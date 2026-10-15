"""Local, page-preserving PDF extraction and lexical retrieval."""
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

import pdfplumber
from pypdf import PdfReader

from .db import now, uid


class SourceService:
    def __init__(self, db):
        self.db = db
        self.tasks: dict[str, asyncio.Task] = {}
        self.cancelled: dict[str, threading.Event] = {}

    def path(self, source_id):
        return self.db.directory / "sources" / f"{source_id}.pdf"

    async def add(self, filename, data):
        if len(data) > 25 * 1024 * 1024:
            raise ValueError("PDF exceeds the 25 MB limit")
        if not data.startswith(b"%PDF-"):
            raise ValueError("Upload a valid PDF document")
        digest = hashlib.sha256(data).hexdigest()
        existing = self.db.one("SELECT id FROM sources WHERE hash=?", (digest,))
        if existing:
            raise ValueError("This PDF is already in the Sources library")
        source_id = uid()
        filename = Path(filename.replace("\\", "/")).name
        self.path(source_id).write_bytes(data)
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

    async def remove(self, source_id):
        if source_id in self.cancelled:
            self.cancelled[source_id].set()
        task = self.tasks.get(source_id)
        if task and not task.done():
            await task
        with self.db.connect() as con:
            con.execute("DELETE FROM chunks WHERE source_id=?", (source_id,))
            con.execute("DELETE FROM pages WHERE source_id=?", (source_id,))
            con.execute("DELETE FROM sources WHERE id=?", (source_id,))
        self.path(source_id).unlink(missing_ok=True)

    def retrieve(self, query, source_ids, limit=8):
        if not source_ids:
            return []
        marks = ",".join("?" for _ in source_ids)
        sources = self.db.all(f"SELECT id,hash,title,state FROM sources WHERE id IN ({marks})", source_ids)
        if len(sources) != len(set(source_ids)) or any(s["state"] != "ready" for s in sources):
            raise ValueError("Select sources that have finished indexing")
        tokens = list(dict.fromkeys(re.findall(r"[^\W_]{3,}", query.lower())))[:32]
        # Build FTS expressions ourselves: never interpret user query syntax.
        expression = " OR ".join('"' + t + '"' for t in tokens)
        rows = []
        if expression:
            rows = self.db.all(f"SELECT source_id,page,content FROM chunks WHERE chunks MATCH ? AND source_id IN ({marks}) ORDER BY bm25(chunks) LIMIT ?", [expression, *source_ids, limit])
        # Even a request like 'make exercises from this' should get source context.
        if not rows:
            for source in sources:
                rows.extend(self.db.all("SELECT source_id,page,content FROM chunks WHERE source_id=? ORDER BY page,rowid LIMIT ?", (source["id"], max(1, limit // len(sources)))))
        lookup = {s["id"]: s for s in sources}
        return [{**r, "document_hash": lookup[r["source_id"]]["hash"], "title": lookup[r["source_id"]]["title"]} for r in rows[:limit]]

    def resolve(self, references):
        resolved = []
        for ref in references:
            source = self.db.one("SELECT id,state FROM sources WHERE hash=?", (ref.document_hash,))
            resolved.append({**ref.model_dump(), "available": bool(source), "source_id": source["id"] if source else None})
        return resolved
