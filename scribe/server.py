"""Step 6: the review app. A single page, served locally, where the clinician
records (or uploads), transcribes, drafts, edits, and signs.

Bound to 127.0.0.1 by default. Putting this on a network is a hardening topic,
not a flag flip.

Three guards live here because a local web server is still a web server:

* it only answers requests addressed to this machine by name (a hostile web
  page cannot reach it by pointing its own domain at 127.0.0.1);
* it refuses writes that come from another website open in the same browser;
* a signed session is locked on the server, not just greyed out on the page.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import Settings
from .notes import list_templates
from .pipeline import Pipeline
from .storage import SessionLocked

STATIC = Path(__file__).parent / "static"
PURGE_EVERY_SECONDS = 3600


def _hostname(header: str) -> str:
    """'127.0.0.1:8765' -> '127.0.0.1', '[::1]:8765' -> '::1'."""
    return (urlparse("//" + header).hostname or "").lower()


class NoteBody(BaseModel):
    text: str


class DraftBody(BaseModel):
    template: str = "soap"
    instructions: str = ""


class SignBody(BaseModel):
    signer: str = ""


def create_app(settings: Settings | None = None, pipeline: Pipeline | None = None) -> FastAPI:
    settings = settings or Settings()
    pipe = pipeline or Pipeline(settings)
    allowed = {"localhost", "127.0.0.1", "::1", settings.host.lower(), *(h.lower() for h in settings.allowed_hosts)}

    async def purge_once() -> None:
        try:
            removed = await run_in_threadpool(pipe.store.purge)
            if removed:
                print(f"purged {len(removed)} unsigned session(s) past retention", file=sys.stderr)
        except Exception as e:  # noqa: BLE001 - never let housekeeping take the app down
            print(f"purge failed: {e}", file=sys.stderr)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Retention is a promise, so the app keeps it without anyone remembering to:
        # once before the first page is served, then every hour while it runs.
        await purge_once()

        async def purge_loop():
            while True:
                await asyncio.sleep(PURGE_EVERY_SECONDS)
                await purge_once()

        task = asyncio.create_task(purge_loop())
        yield
        task.cancel()

    app = FastAPI(title="buildyourscribe review", version="0.1", lifespan=lifespan)

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if _hostname(request.headers.get("host", "")) not in allowed:
            return JSONResponse({"detail": "This scribe only answers on its own address."}, status_code=400)
        origin = request.headers.get("origin")
        if origin and request.method not in ("GET", "HEAD", "OPTIONS"):
            if (urlparse(origin).hostname or "").lower() not in allowed:
                return JSONResponse({"detail": "Request came from another website."}, status_code=403)
        return await call_next(request)

    @app.exception_handler(KeyError)
    @app.exception_handler(FileNotFoundError)
    async def not_found(request: Request, exc: Exception):
        detail = exc.args[0] if isinstance(exc, KeyError) and exc.args else str(exc)
        return JSONResponse({"detail": str(detail)}, status_code=404)

    @app.exception_handler(SessionLocked)
    async def locked(request: Request, exc: SessionLocked):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(httpx.HTTPError)
    async def llm_down(request: Request, exc: httpx.HTTPError):
        return JSONResponse({"detail": f"The model server did not answer properly: {exc}"}, status_code=502)

    @app.exception_handler(RuntimeError)
    async def bad_request(request: Request, exc: RuntimeError):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/health")
    def health():
        try:
            llm_ok, llm_info = pipe.llm.health()
        except RuntimeError as e:
            llm_ok, llm_info = False, str(e)
        return {"stt": {"backend": settings.stt.backend, "model": settings.stt.whisper_model},
                "llm": {"ok": llm_ok, "info": llm_info},
                "storage": {"retention_days": settings.storage.retention_days,
                            "delete_audio_on_sign": settings.storage.delete_audio_on_sign}}

    @app.get("/api/templates")
    def templates():
        return sorted(list_templates(pipe.store.root / "templates"))

    @app.get("/api/sessions")
    def sessions():
        return [m.__dict__ for m in pipe.store.list_sessions()]

    @app.post("/api/sessions")
    async def upload(file: UploadFile = File(...), label: str = Form("")):
        suffix = Path(file.filename or "audio.webm").suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)
        try:
            meta = await run_in_threadpool(pipe.ingest, tmp_path, label)
        finally:
            tmp_path.unlink(missing_ok=True)
        return meta.__dict__

    @app.get("/api/sessions/{sid}")
    def session(sid: str):
        meta = pipe.store.meta(sid)
        t = pipe.store.transcript(sid)
        return {"meta": meta.__dict__, "transcript": t.as_lines() if t else None,
                "segments": t.to_dict()["segments"] if t else None, "note": pipe.store.note(sid)}

    @app.post("/api/sessions/{sid}/transcribe")
    async def transcribe(sid: str):
        t = await run_in_threadpool(pipe.transcribe, sid)
        return {"transcript": t.as_lines(), "engine": t.engine, "elapsed": t.elapsed_seconds}

    @app.post("/api/sessions/{sid}/draft")
    async def draft(sid: str, body: DraftBody):
        d = await run_in_threadpool(pipe.draft, sid, body.template, body.instructions)
        return {"note": d.text, "model": d.model, "elapsed": d.elapsed_seconds, "warnings": d.warnings}

    @app.put("/api/sessions/{sid}/note")
    def save_note(sid: str, body: NoteBody):
        pipe.store.save_note(sid, body.text, edited=True)
        return {"ok": True}

    @app.post("/api/sessions/{sid}/sign")
    def sign(sid: str, body: SignBody):
        meta = pipe.store.sign(sid, body.signer)
        return meta.__dict__

    @app.delete("/api/sessions/{sid}")
    def delete(sid: str):
        pipe.store.delete_session(sid)
        return {"ok": True}

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app

