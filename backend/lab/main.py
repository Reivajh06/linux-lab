import asyncio
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import httpx
import yaml
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from websockets.asyncio.client import connect

from .db import Database, now, uid
from .build import ImageBuilder
from .evaluation import evaluate
from .generation import Generator
from .runtime import LabError, Runtime
from .schema import Course, course_yaml, parse_course
from .sources import SourceService
from .workspace import WorkspaceService

ROOT = Path(os.getenv("LAB_RESOURCE_DIR", str(Path(__file__).resolve().parents[2])))


class YAMLInput(BaseModel):
    yaml: str = Field(max_length=2_000_000)


class CourseUpdate(BaseModel):
    folder: str = Field(max_length=80)  # empty string removes the collection from its folder


class EnvironmentInput(BaseModel):
    course_key: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    cpus: float | None = Field(default=None, ge=0.5, le=32)
    memory_mb: int | None = Field(default=None, ge=512, le=65536)
    pids: int | None = Field(default=None, ge=64, le=4096)


class EnvironmentUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    cpus: float = Field(ge=0.5, le=32)
    memory_mb: int = Field(ge=512, le=65536)
    pids: int = Field(ge=64, le=4096)


class EvaluationInput(BaseModel):
    exercise_id: str | None = None


class GenerationInput(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    model: str = Field(min_length=1, max_length=200)
    source_ids: list[str] | None = Field(default=None, max_length=500)
    count: int = Field(default=5, ge=1, le=30)


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class AssistantInput(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    exercise_id: str | None = Field(default=None, max_length=200)
    messages: list[AssistantMessage] = Field(min_length=1, max_length=60)


class PreferencesInput(BaseModel):
    palette: Literal["tux", "ubuntu", "terminal", "debian", "mint", "fedora", "arch", "kali", "opensuse", "pop", "manjaro"] | None = None
    accent: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")
    model: str | None = Field(default=None, min_length=1, max_length=200)


class WindowInput(BaseModel):
    window: str = Field(pattern=r"^0x[0-9a-fA-F]{1,16}$")


class AppInput(BaseModel):
    app: Literal["terminal", "editor", "browser"]


def create_app(db=None, runtime=None):
    db = db or Database()
    runtime = runtime or Runtime(db)
    sources = SourceService(db)
    generator = Generator(db, sources)
    builder = ImageBuilder(ROOT)
    workspace = WorkspaceService(runtime, ROOT / "docker" / "lab")
    token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app):
        for starter in sorted((ROOT / "courses").glob("*.yaml")):
            course = parse_course(starter.read_text(encoding="utf-8"))
            # Refresh shipped collections in place so content fixes (and folders) reach existing libraries.
            db.execute("INSERT INTO courses(key,course_id,version,yaml,created_at) VALUES(?,?,?,?,?) ON CONFLICT(course_id,version) DO UPDATE SET yaml=excluded.yaml", (uid(), course.id, course.version, course_yaml(course), now()))
        yield
        if builder.task and not builder.task.done():
            builder.task.cancel()
            await builder.task
        for task in generator.tasks.values():
            task.cancel()
        if generator.tasks:
            await asyncio.gather(*generator.tasks.values(), return_exceptions=True)
        for event in sources.cancelled.values():
            event.set()
        if sources.tasks:
            await asyncio.gather(*sources.tasks.values(), return_exceptions=True)

    app = FastAPI(title="Linux Lab", version="1.1.0", lifespan=lifespan)
    app.state.db, app.state.runtime, app.state.sources, app.state.generator = db, runtime, sources, generator
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])

    def valid_origin(origin):
        try:
            return urlparse(origin).hostname in ("localhost", "127.0.0.1", "::1")
        except ValueError:
            return False

    @app.middleware("http")
    async def local_guard(request, call_next):
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
        if length > 27 * 1024 * 1024:
            return JSONResponse({"detail": "Request exceeds upload limit"}, status_code=413)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if not hmac.compare_digest(request.headers.get("x-lab-token", ""), token):
                return JSONResponse({"detail": "Reload the page to refresh the local session"}, status_code=403)
            origin = request.headers.get("origin")
            if origin and not valid_origin(origin):
                return JSONResponse({"detail": "Only local browser origins are allowed"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": str(exc).strip("'")}, status_code=404)

    @app.exception_handler(LabError)
    async def lab_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=503)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        if isinstance(exc, ValidationError):
            detail = [{"path": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
        else:
            detail = str(exc)
        return JSONResponse({"detail": detail}, status_code=422)

    @app.exception_handler(yaml.YAMLError)
    async def invalid_yaml(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.get("/api/config")
    async def config():
        return {"token": token, "docker": await asyncio.to_thread(runtime.health), "ollama_url": generator.base_url, "ocr_languages": os.getenv("OCR_LANGUAGES", "eng+spa"), "desktop": os.getenv("LAB_HOST_RUNTIME") == "1"}

    @app.get("/api/desktop/ready")
    async def desktop_ready():
        return {"nonce": os.getenv("LAB_DESKTOP_NONCE", "web")}

    @app.get("/api/runtime/build")
    async def build_status():
        return builder.status()

    @app.post("/api/runtime/build")
    async def build_image():
        if os.getenv("LAB_HOST_RUNTIME") != "1":
            raise HTTPException(400, "For Docker Compose installations, run docker compose build lab-image on the host.")
        builder.start()
        return builder.status()

    @app.get("/api/courses/schema")
    async def schema():
        return Course.model_json_schema()

    def saved_preferences():
        return {"palette": "tux", "accent": None, "model": "gemma3:12b-it-qat",
                **{r["key"]: json.loads(r["value"]) for r in db.all("SELECT * FROM preferences")}}

    @app.get("/api/preferences")
    async def preferences():
        return saved_preferences()

    @app.patch("/api/preferences")
    async def save_preferences(body: PreferencesInput):
        for key, value in body.model_dump(exclude_unset=True).items():
            if value is None and key != "accent":
                continue
            db.execute("INSERT OR REPLACE INTO preferences VALUES(?,?)", (key, json.dumps(value)))
        return saved_preferences()

    @app.get("/api/courses")
    async def courses():
        output = []
        for row in db.all("SELECT * FROM courses ORDER BY created_at DESC"):
            course = parse_course(row["yaml"])
            env = db.one("SELECT * FROM environments WHERE course_key=? AND is_default=1", (row["key"],))
            results = db.results(env["id"]) if env else {}
            folder = course.folder if row["folder"] is None else row["folder"]
            output.append({"key": row["key"], "id": course.id, "version": course.version, "title": course.title, "folder": folder or None,
                           "description": course.description, "exercise_count": len(course.exercises),
                           "points": sum(t.points for e in course.exercises for t in e.tasks),
                           "earned": sum(r["earned"] for r in results.values()),
                           "completed": sum(r["earned"] == r["available"] for r in results.values()),
                           "environment": env, "created_at": row["created_at"]})
        return output

    @app.post("/api/courses/validate")
    async def validate(body: YAMLInput):
        course = parse_course(body.yaml)
        return {"course": course.model_dump(), "yaml": course_yaml(course)}

    @app.post("/api/courses/import", status_code=201)
    async def import_course(body: YAMLInput):
        course = parse_course(body.yaml)
        key = uid()
        try:
            db.execute("INSERT INTO courses(key,course_id,version,yaml,created_at) VALUES(?,?,?,?,?)", (key, course.id, course.version, course_yaml(course), now()))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "This course ID and version already exist. Change version before importing a revision.") from exc
        return {"key": key, "title": course.title}

    @app.get("/api/courses/{key}")
    async def course_detail(key: str):
        course = db.course(key)
        env = runtime.environment(key)
        data = course.model_dump()
        for exercise, original in zip(data["exercises"], course.exercises):
            exercise["sources"] = sources.resolve(original.sources)
        return {"key": key, "course": data, "environment": await asyncio.to_thread(runtime.refresh, env["id"]), "results": db.results(env["id"])}

    @app.patch("/api/courses/{key}")
    async def move_course(key: str, body: CourseUpdate):
        db.course(key)
        db.execute("UPDATE courses SET folder=? WHERE key=?", (body.folder.strip(), key))
        return {"key": key, "folder": body.folder.strip() or None}

    @app.get("/api/courses/{key}/export")
    async def export(key: str):
        course = db.course(key)
        return Response(course_yaml(course), media_type="application/yaml", headers={"Content-Disposition": f'attachment; filename="{course.id}-{course.version}.yaml"'})

    @app.post("/api/environments")
    async def get_environment(body: EnvironmentInput):
        if body.course_key:
            db.course(body.course_key)
        if body.name is not None:
            if not body.name.strip():
                raise ValueError("Environment name cannot be blank")
            env = runtime.create(body.name, body.course_key, body.cpus, body.memory_mb, body.pids)
        else:
            env = runtime.environment(body.course_key)
        return await asyncio.to_thread(runtime.refresh, env["id"])

    @app.get("/api/environments")
    async def list_environments():
        rows = db.all("SELECT * FROM environments ORDER BY created_at DESC")
        return await asyncio.gather(*(asyncio.to_thread(runtime.refresh, row["id"]) for row in rows))

    @app.get("/api/environments/{environment_id}")
    async def environment(environment_id: str):
        return await asyncio.to_thread(runtime.refresh, environment_id)

    @app.patch("/api/environments/{environment_id}")
    async def update_environment(environment_id: str, body: EnvironmentUpdate):
        if not body.name.strip():
            raise ValueError("Environment name cannot be blank")
        return await runtime.update(environment_id, body.name, body.cpus, body.memory_mb, body.pids)

    @app.delete("/api/environments/{environment_id}")
    async def delete_environment(environment_id: str):
        await runtime.delete(environment_id)
        return {"deleted": True}

    @app.get("/api/environments/{environment_id}/workspace")
    async def environment_workspace(environment_id: str):
        env = await asyncio.to_thread(runtime.refresh, environment_id)
        if not env["course_key"]:
            return {"course": None, "environment": env, "results": {}}
        course = db.course(env["course_key"])
        data = course.model_dump()
        for exercise, original in zip(data["exercises"], course.exercises):
            exercise["sources"] = sources.resolve(original.sources)
        return {"key": env["course_key"], "course": data, "environment": env, "results": db.results(environment_id)}

    @app.post("/api/environments/{environment_id}/start")
    async def start(environment_id: str):
        return await runtime.start(environment_id)

    @app.post("/api/environments/{environment_id}/stop")
    async def stop(environment_id: str):
        return await runtime.stop(environment_id)

    @app.post("/api/environments/{environment_id}/recreate")
    async def recreate(environment_id: str):
        return await runtime.recreate(environment_id)

    @app.post("/api/environments/{environment_id}/evaluate")
    async def grade(environment_id: str, body: EvaluationInput):
        return await evaluate(runtime, db, environment_id, body.exercise_id)

    @app.post("/api/environments/{environment_id}/workspace/prepare")
    async def prepare_workspace(environment_id: str):
        return await workspace.prepare(environment_id)

    @app.get("/api/environments/{environment_id}/workspace/windows")
    async def workspace_windows(environment_id: str):
        return await asyncio.to_thread(workspace.command, environment_id, "list")

    @app.post("/api/environments/{environment_id}/workspace/activate")
    async def activate_window(environment_id: str, body: WindowInput):
        return await asyncio.to_thread(workspace.command, environment_id, "activate", body.window)

    @app.post("/api/environments/{environment_id}/workspace/close")
    async def close_window(environment_id: str, body: WindowInput):
        return await asyncio.to_thread(workspace.command, environment_id, "close", body.window)

    @app.post("/api/environments/{environment_id}/workspace/launch")
    async def launch_app(environment_id: str, body: AppInput):
        return await asyncio.to_thread(workspace.command, environment_id, body.app)

    @app.websocket("/api/environments/{environment_id}/desktop")
    async def desktop(ws: WebSocket, environment_id: str):
        origin = ws.headers.get("origin", "")
        if not valid_origin(origin) or not hmac.compare_digest(ws.query_params.get("token", ""), token):
            await ws.close(code=1008)
            return
        tasks = []
        try:
            remote_url = await asyncio.to_thread(runtime.desktop_url, environment_id)
            await ws.accept(subprotocol="binary" if "binary" in ws.scope.get("subprotocols", []) else None)
            async with connect(remote_url, open_timeout=10, max_size=8 * 1024 * 1024, compression=None) as remote:
                async def incoming():
                    while True:
                        event = await ws.receive()
                        if event["type"] == "websocket.disconnect":
                            return
                        await remote.send(event.get("bytes") if event.get("bytes") is not None else event.get("text", ""))

                async def outgoing():
                    async for message in remote:
                        if isinstance(message, bytes):
                            await ws.send_bytes(message)
                        else:
                            await ws.send_text(message)

                tasks = [asyncio.create_task(incoming()), asyncio.create_task(outgoing())]
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            try:
                await ws.close(code=1011, reason="Desktop unavailable; check environment status and reconnect")
            except RuntimeError:
                pass
        finally:
            for task in tasks:
                task.cancel()

    @app.get("/api/sources")
    async def list_sources():
        return [{**s, "warnings": json.loads(s["warnings"])} for s in db.all("SELECT * FROM sources ORDER BY created_at DESC")]

    @app.post("/api/sources", status_code=201)
    async def upload_source(file: UploadFile = File(...)):
        data = await file.read(25 * 1024 * 1024 + 1)
        return await sources.add(file.filename or "source.pdf", data)

    def source_row(source_id):
        row = db.one("SELECT * FROM sources WHERE id=?", (source_id,))
        if not row:
            raise KeyError("Source not found")
        return row

    @app.get("/api/sources/{source_id}/pdf")
    async def source_pdf(source_id: str):
        row = source_row(source_id)
        if sources.path(source_id).suffix != ".pdf":
            from .sources import source_text
            return Response(source_text(sources.path(source_id).read_bytes(), row["filename"]), media_type="text/plain")
        return FileResponse(sources.path(source_id), media_type="application/pdf", filename=row["filename"], content_disposition_type="inline")

    @app.post("/api/sources/{source_id}/retry")
    async def retry_source(source_id: str):
        source_row(source_id)
        sources.start(source_id)
        return {"state": "indexing"}

    @app.delete("/api/sources/{source_id}")
    async def delete_source(source_id: str):
        source_row(source_id)
        await sources.remove(source_id)
        return {"deleted": True}

    @app.get("/api/sources/{source_id}/pages/{page}")
    async def source_page(source_id: str, page: int):
        source_row(source_id)
        row = db.one("SELECT * FROM pages WHERE source_id=? AND page=?", (source_id, page))
        if not row:
            raise KeyError("Page not indexed")
        return row

    @app.get("/api/ollama/models")
    async def models():
        try:
            return {"available": True, "models": await generator.models()}
        except (httpx.HTTPError, ValueError) as exc:
            return {"available": False, "models": [], "message": f"Cannot connect to local Ollama: {exc}"}

    @app.get("/api/chats")
    async def chats():
        return db.all("SELECT id,title,created_at,updated_at FROM chats ORDER BY updated_at DESC")

    @app.post("/api/chats", status_code=201)
    async def create_chat():
        return {"id": generator.create_chat()}

    @app.get("/api/chats/{chat_id}")
    async def chat(chat_id: str):
        row = db.one("SELECT * FROM chats WHERE id=?", (chat_id,))
        if not row:
            raise KeyError("Chat not found")
        return {**row, "messages": db.all("SELECT * FROM messages WHERE chat_id=? ORDER BY id", (chat_id,)), "job": db.one("SELECT * FROM jobs WHERE chat_id=? ORDER BY created_at DESC LIMIT 1", (chat_id,))}

    @app.delete("/api/chats/{chat_id}")
    async def delete_chat(chat_id: str):
        if not db.one("SELECT id FROM chats WHERE id=?", (chat_id,)):
            raise KeyError("Chat not found")
        for job in db.all("SELECT id FROM jobs WHERE chat_id=? AND state IN ('queued','running')", (chat_id,)):
            await generator.cancel(job["id"])
        with db.connect() as con:
            for table, column in (("messages", "chat_id"), ("jobs", "chat_id"), ("chats", "id")):
                con.execute(f"DELETE FROM {table} WHERE {column}=?", (chat_id,))
        return {"deleted": True}

    @app.post("/api/environments/{environment_id}/assistant")
    async def assistant(environment_id: str, body: AssistantInput):
        # A temporary helper chat: the browser holds the conversation and nothing is stored.
        if body.messages[-1].role != "user":
            raise ValueError("The last message must be the learner's question")
        environment = runtime.get(environment_id)
        course = db.course(environment["course_key"]) if environment["course_key"] else None
        exercise = next((e for e in course.exercises if e.id == body.exercise_id), None) if course else None
        try:
            chunks = await generator.assist(body.model, generator.environment_context(environment, course, exercise),
                                            [m.model_dump() for m in body.messages])
        except httpx.HTTPError as exc:
            raise ValueError(generator.describe_error(exc)) from exc

        async def reply():
            try:
                async for text in chunks:
                    yield text
            except Exception as exc:
                yield f"\n\n**Error:** {generator.describe_error(exc)}"
        return StreamingResponse(reply(), media_type="text/plain; charset=utf-8", headers={"Cache-Control": "no-store"})

    @app.put("/api/chats/{chat_id}/draft")
    async def save_draft(chat_id: str, body: YAMLInput):
        if not db.one("SELECT id FROM chats WHERE id=?", (chat_id,)):
            raise KeyError("Chat not found")
        if db.one("SELECT id FROM jobs WHERE chat_id=? AND state IN ('queued','running')", (chat_id,)):
            raise HTTPException(409, "Wait for generation to finish before editing this draft")
        db.execute("UPDATE chats SET draft=?,updated_at=? WHERE id=?", (body.yaml, now(), chat_id))
        return {"saved": True}

    @app.post("/api/chats/{chat_id}/generate", status_code=202)
    async def generate(chat_id: str, body: GenerationInput):
        return {"job_id": generator.start(chat_id, body.prompt, body.model, body.source_ids, body.count)}

    @app.post("/api/jobs/{job_id}/cancel")
    async def cancel(job_id: str):
        if not db.one("SELECT id FROM jobs WHERE id=?", (job_id,)):
            raise KeyError("Job not found")
        await generator.cancel(job_id)
        return db.one("SELECT * FROM jobs WHERE id=?", (job_id,))

    @app.get("/api/docs/exercise-format")
    async def format_doc():
        return Response((ROOT / "EXERCISE_FORMAT.md").read_text(encoding="utf-8"), media_type="text/markdown")

    dist = Path(os.getenv("LAB_FRONTEND_DIR", str(ROOT / "frontend" / "dist")))
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}")
    async def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found")
        if (dist / "index.html").exists():
            return FileResponse(dist / "index.html")
        return JSONResponse({"message": "Linux Lab API is running. Build the frontend or use its Vite dev server.", "docs": "/docs"})

    return app


app = create_app()
