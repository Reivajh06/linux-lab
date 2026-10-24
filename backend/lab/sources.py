"""Local PDF/text extraction and page-based lexical retrieval."""
import asyncio
import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import io
import tarfile
import shutil
from pathlib import Path
from html.parser import HTMLParser

import pdfplumber
from pypdf import PdfReader

from .db import now, uid


def decode_text(data):
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue


class PlainHTML(HTMLParser):
    blocks = {"p", "div", "section", "article", "header", "footer", "blockquote",
              "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "pre", "code", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden, self.verbatim = [], 0, 0

    def paragraph_break(self):
        if not self.parts or not self.parts[-1].endswith("\n\n"):
            self.parts.append("\n\n")

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self.hidden += 1
        if self.hidden:
            return
        if tag in self.blocks:
            self.paragraph_break()
        elif tag == "br":
            self.parts.append("\n")
        if tag in ("pre", "code"):
            self.verbatim += 1

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag in ("pre", "code"):
            self.verbatim = max(0, self.verbatim - 1)
        if tag in self.blocks:
            self.paragraph_break()

    def handle_data(self, data):
        if not self.hidden:
            if not self.verbatim and not data.strip() and (not self.parts or self.parts[-1].endswith("\n")):
                return
            self.parts.append(data if self.verbatim else re.sub(r"\s+", " ", data))


def source_text(data, filename):
    text = decode_text(data).replace("\r\n", "\n").replace("\r", "\n")
    # Some practice sheets have an HTML extension but contain only plain text.
    if Path(filename).suffix.lower() in (".htm", ".html") and re.search(r"</?[a-zA-Z][^>]*>", text):
        parser = PlainHTML()
        parser.feed(text)
        parser.close()
        text = "".join(parser.parts)
    return text.strip("\n")


def text_pages(text, size=3000):
    """Pack paragraphs into pages; split oversized paragraphs at lines/words."""
    pages, current = [], ""
    for paragraph in re.split(r"\n[ \t]*\n+", text):
        if not paragraph.strip():
            continue
        if current and len(current) + len(paragraph) + 2 > size:
            pages.append(current)
            current = ""
        while len(paragraph) > size:
            boundary = paragraph.rfind("\n", 0, size + 1)
            if boundary <= 0:
                boundary = paragraph.rfind(" ", 0, size + 1)
            if boundary <= 0:
                boundary = size
            pages.append(paragraph[:boundary])
            # Drop only the chosen separator, preserving code indentation.
            paragraph = paragraph[boundary + (paragraph[boundary] in "\n "):]
        if paragraph:
            current = current + "\n\n" + paragraph if current else paragraph
    if current:
        pages.append(current)
    return pages


class SourceService:
    def __init__(self, db):
        self.db = db
        self.tasks: dict[str, asyncio.Task] = {}
        self.cancelled: dict[str, threading.Event] = {}

    def path(self, source_id, filename=None):
        if filename is None:
            row = self.db.one("SELECT filename FROM sources WHERE id=?", (source_id,))
            filename = row["filename"] if row else "source.pdf"
        suffix = ".pdf" if Path(filename).suffix.lower() == ".pdf" else ".txt"
        return self.db.directory / "sources" / f"{source_id}{suffix}"

    async def add(self, filename, data):
        if len(data) > 25 * 1024 * 1024:
            raise ValueError("Source exceeds the 25 MB limit")
        filename = Path(filename.replace("\\", "/")).name
        extension = Path(filename).suffix.lower()
        if extension not in (".pdf", ".txt", ".md", ".htm", ".html"):
            raise ValueError("Upload a PDF, TXT, MD, HTM, or HTML document")
        if extension == ".pdf" and not data.startswith(b"%PDF-"):
            raise ValueError("Upload a valid PDF document")
        digest = hashlib.sha256(data).hexdigest()
        existing = self.db.one("SELECT id FROM sources WHERE hash=?", (digest,))
        if existing:
            raise ValueError("This document is already in the Sources library")
        source_id = uid()
        self.path(source_id, filename).write_bytes(data)
        self.db.execute("INSERT INTO sources(id,hash,title,filename,state,created_at) VALUES(?,?,?,?,?,?)", (source_id, digest, Path(filename).stem, filename, "indexing", now()))
        self.start(source_id)
        return self.db.one("SELECT * FROM sources WHERE id=?", (source_id,))

    def start(self, source_id):
        if source_id in self.tasks and not self.tasks[source_id].done():
            raise ValueError("This source is already being indexed")
        event = threading.Event()
        self.cancelled[source_id] = event
        self.db.execute("UPDATE sources SET state='indexing',indexed_pages=0,ocr_pages=0,error=NULL,warnings='[]' WHERE id=?", (source_id,))
        self.tasks[source_id] = asyncio.create_task(self._run(source_id, event))

    async def _run(self, source_id, event):
        try:
            await asyncio.to_thread(self.index, source_id, event)
        except Exception as exc:
            self.db.execute("UPDATE sources SET state='error',error=? WHERE id=?", (str(exc)[:2000], source_id))

    def ocr(self, path, page):
        if not shutil.which("pdftoppm") or not shutil.which("tesseract"):
            return self.ocr_docker(path, page)
        with tempfile.TemporaryDirectory(prefix="linux-lab-ocr-") as tmp:
            prefix = str(Path(tmp) / "page")
            try:
                subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile", "-r", "150", "-scale-to", "2400", "-png", str(path), prefix], check=True, capture_output=True, timeout=90)
                result = subprocess.run(["tesseract", prefix + ".png", "stdout", "-l", os.getenv("OCR_LANGUAGES", "eng+spa")], check=True, capture_output=True, text=True, encoding="utf-8", timeout=90)
                return result.stdout.strip()
            except FileNotFoundError as exc:
                raise ValueError("OCR requires Poppler and Tesseract. Use the Docker app image, which includes both.") from exc
            except subprocess.CalledProcessError as exc:
                error = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr
                raise ValueError(f"OCR failed: {(error or str(exc))[:500]}") from exc

    def ocr_docker(self, path, page):
        """Windows fallback: copy into a disposable OCR container, no host mounts."""
        import docker
        client, container = None, None
        languages = os.getenv("OCR_LANGUAGES", "eng+spa")
        if not re.fullmatch(r"[a-z_+]+", languages):
            raise ValueError("Invalid OCR_LANGUAGES configuration")
        try:
            client = docker.from_env(timeout=200)
            command = f"pdftoppm -f {int(page)} -l {int(page)} -singlefile -r 150 -scale-to 2400 -png /tmp/source.pdf /tmp/page && tesseract /tmp/page.png stdout -l {languages}"
            container = client.containers.create(os.getenv("LAB_IMAGE", "linux-lab-environment:local"), command=["bash", "-lc", command], entrypoint=[], user="learner", network_disabled=True, mem_limit="1g", pids_limit=64, cap_drop=["ALL"], security_opt=["no-new-privileges:true"], labels={"linux-lab.ocr": "true"})
            payload = path.read_bytes()
            archive = io.BytesIO()
            with tarfile.open(fileobj=archive, mode="w") as tar:
                entry = tarfile.TarInfo("source.pdf")
                entry.size, entry.mode = len(payload), 0o444
                tar.addfile(entry, io.BytesIO(payload))
            container.put_archive("/tmp", archive.getvalue())
            container.start()
            status = container.wait(timeout=180)
            if status["StatusCode"] != 0:
                raise ValueError(container.logs(stdout=False).decode(errors="replace")[-1000:])
            return container.logs(stderr=False).decode(errors="replace").strip()
        except Exception as exc:
            raise ValueError(f"Local OCR needs the lab Docker image. Start Docker Desktop, build the image in the app, then retry indexing. Details: {exc}") from exc
        finally:
            if container:
                container.remove(force=True)
            if client:
                client.close()

    def index(self, source_id, event):
        path = self.path(source_id)
        if path.suffix != ".pdf":
            return self.index_text(source_id, path, event)
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError("Password-protected PDFs are not supported. Upload an unlocked copy.")
        count = len(reader.pages)
        if not 1 <= count <= 500:
            raise ValueError("PDF must contain between 1 and 500 pages")
        with self.db.connect() as con:
            con.execute("DELETE FROM pages WHERE source_id=?", (source_id,))
            con.execute("DELETE FROM chunks WHERE source_id=?", (source_id,))
            con.execute("UPDATE sources SET pages=? WHERE id=?", (count, source_id))
        warnings, ocr_count, useful = [], 0, 0
        with pdfplumber.open(path) as pdf:
            for number, page in enumerate(pdf.pages, 1):
                if event.is_set():
                    return
                text = (page.extract_text() or "").strip()
                used_ocr = len(text) < 40
                if used_ocr:
                    try:
                        text = self.ocr(path, number)
                        ocr_count += 1
                    except Exception as exc:
                        warnings.append(f"Page {number}: {exc}")
                if not text:
                    warnings.append(f"Page {number}: no readable text found")
                else:
                    useful += 1
                text = text[:200000]
                words = text.split()
                with self.db.connect() as con:
                    con.execute("INSERT INTO pages VALUES(?,?,?,?)", (source_id, number, text, int(used_ocr)))
                    for start in range(0, len(words), 280):
                        chunk = " ".join(words[start:start + 350])
                        con.execute("INSERT INTO chunks(source_id,page,content) VALUES(?,?,?)", (source_id, number, chunk))
                    con.execute("UPDATE sources SET indexed_pages=?,ocr_pages=?,warnings=? WHERE id=?", (number, ocr_count, json.dumps(warnings), source_id))
                page.close()
        if event.is_set():
            return
        if not useful:
            raise ValueError("No readable text could be extracted. Check OCR dependencies and document quality.")
        self.db.execute("UPDATE sources SET state='ready' WHERE id=?", (source_id,))

    def index_text(self, source_id, path, event):
        row = self.db.one("SELECT filename FROM sources WHERE id=?", (source_id,))
        pages = text_pages(source_text(path.read_bytes(), row["filename"]))
        if not pages:
            raise ValueError("No readable text could be extracted from this document")
        with self.db.connect() as con:
            con.execute("DELETE FROM pages WHERE source_id=?", (source_id,))
            con.execute("DELETE FROM chunks WHERE source_id=?", (source_id,))
            con.execute("UPDATE sources SET pages=? WHERE id=?", (len(pages), source_id))
        for number, text in enumerate(pages, 1):
            if event.is_set():
                return
            words = text.split()
            with self.db.connect() as con:
                con.execute("INSERT INTO pages VALUES(?,?,?,0)", (source_id, number, text))
                for start in range(0, len(words), 280):
                    con.execute("INSERT INTO chunks(source_id,page,content) VALUES(?,?,?)", (source_id, number, " ".join(words[start:start + 350])))
                con.execute("UPDATE sources SET indexed_pages=? WHERE id=?", (number, source_id))
        if not event.is_set():
            self.db.execute("UPDATE sources SET state='ready' WHERE id=?", (source_id,))

    async def remove(self, source_id):
        path = self.path(source_id)
        if source_id in self.cancelled:
            self.cancelled[source_id].set()
        task = self.tasks.get(source_id)
        if task and not task.done():
            await task
        with self.db.connect() as con:
            con.execute("DELETE FROM chunks WHERE source_id=?", (source_id,))
            con.execute("DELETE FROM pages WHERE source_id=?", (source_id,))
            con.execute("DELETE FROM sources WHERE id=?", (source_id,))
        path.unlink(missing_ok=True)

    def selected_sources(self, source_ids=None):
        # None means the entire ready library; [] explicitly disables source grounding.
        if source_ids is None:
            return [s['id'] for s in self.db.all("SELECT id FROM sources WHERE state='ready' ORDER BY created_at,id")]
        if not source_ids:
            return []
        marks = ",".join("?" for _ in source_ids)
        sources = self.db.all(f"SELECT id,state FROM sources WHERE id IN ({marks})", source_ids)
        if len(sources) != len(set(source_ids)) or any(s["state"] != "ready" for s in sources):
            raise ValueError("Select sources that have finished indexing")
        return list(dict.fromkeys(source_ids))

    def retrieve(self, query, source_ids=None, limit=8, max_bytes=12000, offset=0):
        source_ids = self.selected_sources(source_ids)
        if not source_ids or limit < 1 or max_bytes < 256:
            return []
        marks = ",".join("?" for _ in source_ids)
        sources = self.db.all(f"SELECT id,hash,title FROM sources WHERE id IN ({marks}) ORDER BY created_at,id", source_ids)
        tokens = list(dict.fromkeys(re.findall(r"[^\W_]{3,}", query.lower())))[:32]
        # Build FTS expressions ourselves: never interpret user query syntax.
        expression = " OR ".join('"' + t + '"' for t in tokens)
        rows = []
        if expression:
            ranked = self.db.all(f"SELECT source_id,page,content FROM chunks WHERE chunks MATCH ? AND source_id IN ({marks}) ORDER BY bm25(chunks) LIMIT ?", [expression, *source_ids, limit * 8])
            # Prefer different documents before taking more passages from the same PDF.
            seen, extra = set(), []
            for row in ranked:
                if row['source_id'] in seen:
                    extra.append(row)
                else:
                    rows.append(row)
                    seen.add(row['source_id'])
            rows.extend(extra)
        # Even a request like 'make exercises from this' should get source context.
        if not rows:
            # Rotate generic requests across documents between exercise batches.
            shift = offset % len(sources)
            for source in (sources[shift:] + sources[:shift])[:limit]:
                rows.extend(self.db.all("SELECT source_id,page,content FROM chunks WHERE source_id=? ORDER BY page,rowid LIMIT 1", (source["id"],)))
        lookup = {s["id"]: s for s in sources}
        excerpts = []
        for row in rows[:limit]:
            item = {**row, 'document_hash': lookup[row['source_id']]['hash'], 'title': lookup[row['source_id']]['title']}
            # Share a fixed byte budget across passages, including citation metadata.
            remaining = max_bytes - len(json.dumps(excerpts, ensure_ascii=False).encode()) - 2
            item['content'] = ''
            allowance = min(2400, remaining // max(1, min(limit, len(rows)) - len(excerpts)))
            overhead = len(json.dumps(item, ensure_ascii=False).encode()) + 2
            if allowance <= overhead + 40:
                break
            item['content'] = row['content'].encode()[:allowance - overhead].decode('utf-8', errors='ignore')
            # JSON escaping may expand source text (e.g. quotes and backslashes).
            while item['content'] and len(json.dumps(excerpts + [item], ensure_ascii=False).encode()) > max_bytes:
                item['content'] = item['content'][:-40]
            if item['content']:
                excerpts.append(item)
        return excerpts

    def resolve(self, references):
        resolved = []
        for ref in references:
            source = self.db.one("SELECT id,state FROM sources WHERE hash=?", (ref.document_hash,))
            resolved.append({**ref.model_dump(), "available": bool(source), "source_id": source["id"] if source else None})
        return resolved
