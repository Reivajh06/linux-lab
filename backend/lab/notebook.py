"""Notebook: Markdown study notes. Shipped pages come from notebook/*.md; learners can edit them or add their own."""
import hashlib
import json
import re
from pathlib import Path

import yaml

from .db import now, uid

FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
SUMMARY = "id,slug,title,folder,icon,ord,tags,edited,created_at,updated_at"


def parse_page(text: str, slug: str) -> dict:
    """Split YAML frontmatter (title, folder, order, icon, tags) from the Markdown body."""
    text = text.replace("\r\n", "\n")
    meta, body = {}, text
    match = FRONTMATTER.match(text)
    if match:
        meta = yaml.safe_load(match.group(1)) or {}
        if not isinstance(meta, dict):
            raise ValueError(f"{slug}: frontmatter must be a mapping")
        body = text[match.end():]
    tags = meta.get("tags") or []
    return {"slug": slug, "title": str(meta.get("title") or slug)[:200], "folder": (str(meta["folder"])[:80] if meta.get("folder") else None),
            "icon": str(meta.get("icon") or "file")[:40], "ord": int(meta.get("order") or 0),
            "tags": json.dumps([str(t)[:40] for t in tags][:20] if isinstance(tags, list) else []), "body": body.strip("\n") + "\n"}


def row(page: dict) -> dict:
    page = dict(page)
    return {**page, "order": page.pop("ord"), "tags": json.loads(page["tags"]), "shipped": page["slug"] is not None, "edited": bool(page["edited"])}


class Notebook:
    def __init__(self, db, directory: Path):
        self.db, self.directory = db, directory

    def seed(self):
        """Install or refresh shipped pages; pages the learner edited are left alone."""
        for path in sorted(self.directory.glob("*.md")) if self.directory.exists() else []:
            page = parse_page(path.read_text(encoding="utf-8"), path.stem)
            digest = hashlib.sha256(json.dumps(page, sort_keys=True).encode()).hexdigest()
            existing = self.db.one("SELECT id,edited,shipped_hash FROM notes WHERE slug=?", (page["slug"],))
            if not existing:
                self.db.execute("INSERT INTO notes(id,slug,title,folder,icon,ord,tags,body,shipped_hash,edited,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,0,?,?)",
                                (uid(), page["slug"], page["title"], page["folder"], page["icon"], page["ord"], page["tags"], page["body"], digest, now(), now()))
            elif not existing["edited"] and existing["shipped_hash"] != digest:
                self.db.execute("UPDATE notes SET title=?,folder=?,icon=?,ord=?,tags=?,body=?,shipped_hash=?,updated_at=? WHERE id=?",
                                (page["title"], page["folder"], page["icon"], page["ord"], page["tags"], page["body"], digest, now(), existing["id"]))

    def list(self, query=""):
        """All pages, or those whose title, tags or text contain every word of the query."""
        where, args = [], []
        for word in query.split()[:8]:
            like = "%" + re.sub(r"([!%_])", r"!\1", word) + "%"
            where.append("(title LIKE ? ESCAPE '!' OR tags LIKE ? ESCAPE '!' OR body LIKE ? ESCAPE '!')")
            args += [like] * 3
        sql = f"SELECT {SUMMARY} FROM notes {'WHERE ' + ' AND '.join(where) if where else ''} ORDER BY COALESCE(folder,''),ord,title COLLATE NOCASE"
        return [row(p) for p in self.db.all(sql, args)]

    def get(self, note_id):
        page = self.db.one(f"SELECT {SUMMARY},body FROM notes WHERE id=?", (note_id,))
        if not page:
            raise KeyError("Page not found")
        return row(page)

    def create(self, title, folder, body):
        note_id = uid()
        order = (self.db.one("SELECT MAX(ord) AS n FROM notes WHERE COALESCE(folder,'')=?", (folder or "",))["n"] or 0) + 1
        self.db.execute("INSERT INTO notes(id,slug,title,folder,icon,ord,tags,body,shipped_hash,edited,created_at,updated_at) VALUES(?,NULL,?,?,'file',?,'[]',?,NULL,1,?,?)",
                        (note_id, title, folder or None, order, body, now(), now()))
        return self.get(note_id)

    def update(self, note_id, title, folder, body):
        self.get(note_id)
        self.db.execute("UPDATE notes SET title=?,folder=?,body=?,edited=1,updated_at=? WHERE id=?", (title, folder or None, body, now(), note_id))
        return self.get(note_id)

    def delete(self, note_id):
        page = self.get(note_id)
        if page["shipped"]:
            raise ValueError("Built-in pages cannot be deleted. Restore the original instead.")
        self.db.execute("DELETE FROM notes WHERE id=?", (note_id,))

    def restore(self, note_id):
        page = self.get(note_id)
        if not page["shipped"]:
            raise ValueError("Only built-in pages have an original to restore")
        self.db.execute("UPDATE notes SET edited=0,shipped_hash=NULL WHERE id=?", (note_id,))
        self.seed()
        return self.get(note_id)
