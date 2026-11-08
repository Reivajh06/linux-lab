import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid4().hex


class Database:
    def __init__(self, directory: str | Path | None = None):
        self.directory = Path(directory or os.getenv("LAB_DATA_DIR", "data"))
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / "sources").mkdir(exist_ok=True)
        with self.connect() as con:
            con.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS courses (
                    key TEXT PRIMARY KEY, course_id TEXT NOT NULL, version TEXT NOT NULL,
                    yaml TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(course_id, version));
                CREATE TABLE IF NOT EXISTS environments (
                    id TEXT PRIMARY KEY, course_key TEXT, container_id TEXT,
                    state TEXT NOT NULL DEFAULT 'new', setup_done INTEGER DEFAULT 0,
                    error TEXT, created_at TEXT NOT NULL, name TEXT NOT NULL DEFAULT '',
                    cpus REAL NOT NULL DEFAULT 2, memory_mb INTEGER NOT NULL DEFAULT 2048,
                    pids INTEGER NOT NULL DEFAULT 1024, is_default INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS results (
                    environment_id TEXT NOT NULL, exercise_id TEXT NOT NULL,
                    result TEXT NOT NULL, checked_at TEXT NOT NULL,
                    PRIMARY KEY(environment_id, exercise_id));
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, hash TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
                    filename TEXT NOT NULL, state TEXT NOT NULL, pages INTEGER DEFAULT 0,
                    indexed_pages INTEGER DEFAULT 0, ocr_pages INTEGER DEFAULT 0,
                    error TEXT, warnings TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS pages (
                    source_id TEXT NOT NULL, page INTEGER NOT NULL, content TEXT NOT NULL,
                    ocr INTEGER NOT NULL, PRIMARY KEY(source_id, page));
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
                    source_id UNINDEXED, page UNINDEXED, content, tokenize='unicode61 remove_diacritics 2');
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, draft TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL,
                    role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, chat_id TEXT NOT NULL, state TEXT NOT NULL,
                    progress TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY, slug TEXT UNIQUE, title TEXT NOT NULL, folder TEXT,
                    icon TEXT NOT NULL DEFAULT 'file', ord INTEGER NOT NULL DEFAULT 0, tags TEXT NOT NULL DEFAULT '[]',
                    body TEXT NOT NULL, shipped_hash TEXT, edited INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                UPDATE jobs SET state='error', error='Application restarted; retry your request'
                    WHERE state IN ('queued', 'running');
                UPDATE sources SET state='interrupted', error='Indexing interrupted; choose Retry'
                    WHERE state='indexing';
            """)
            environment_sql = con.execute("SELECT sql FROM sqlite_master WHERE name='environments'").fetchone()[0]
            if "course_key TEXT UNIQUE" in environment_sql:
                con.executescript("""
                    ALTER TABLE environments RENAME TO environments_old;
                    CREATE TABLE environments (
                        id TEXT PRIMARY KEY, course_key TEXT, container_id TEXT,
                        state TEXT NOT NULL DEFAULT 'new', setup_done INTEGER DEFAULT 0,
                        error TEXT, created_at TEXT NOT NULL, name TEXT NOT NULL DEFAULT '',
                        cpus REAL NOT NULL DEFAULT 2, memory_mb INTEGER NOT NULL DEFAULT 2048,
                        pids INTEGER NOT NULL DEFAULT 1024, is_default INTEGER NOT NULL DEFAULT 0);
                    INSERT INTO environments(id,course_key,container_id,state,setup_done,error,created_at,is_default)
                        SELECT id,course_key,container_id,state,setup_done,error,created_at,1 FROM environments_old;
                    DROP TABLE environments_old;
                """)
            con.execute("UPDATE environments SET name=CASE WHEN course_key IS NULL THEN 'Free Practice' ELSE 'Course environment' END WHERE name=''")
            if "folder" not in {r[1] for r in con.execute("PRAGMA table_info(courses)")}:
                # NULL follows the collection's own `folder`; '' means the learner moved it out of any folder.
                con.execute("ALTER TABLE courses ADD COLUMN folder TEXT")
            con.execute("CREATE UNIQUE INDEX IF NOT EXISTS environment_defaults ON environments(COALESCE(course_key,'free')) WHERE is_default=1")

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.directory / "lab.sqlite3", timeout=20)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def all(self, sql, args=()):
        with self.connect() as con:
            return [dict(r) for r in con.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        rows = self.all(sql, args)
        return rows[0] if rows else None

    def execute(self, sql, args=()):
        with self.connect() as con:
            return con.execute(sql, args).lastrowid

    def message(self, chat_id, role, content):
        self.execute("INSERT INTO messages(chat_id,role,content,created_at) VALUES(?,?,?,?)", (chat_id, role, content, now()))

    def course(self, key):
        from .schema import parse_course
        row = self.one("SELECT * FROM courses WHERE key=?", (key,))
        if not row:
            raise KeyError("Course not found")
        return parse_course(row["yaml"])

    def results(self, environment_id):
        return {r["exercise_id"]: json.loads(r["result"]) for r in self.all("SELECT * FROM results WHERE environment_id=?", (environment_id,))}
