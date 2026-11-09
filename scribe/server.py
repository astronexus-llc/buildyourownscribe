"""Step 6: the review app. A single page, served locally, where the clinician
records (or uploads), transcribes, drafts, edits, and signs.

Bound to 127.0.0.1 by default. Putting this on a network is a hardening topic,
not a flag flip.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import Settings
from .notes import list_templates
from .pipeline import Pipeline

STATIC = Path(__file__).parent / "static"


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
    app = FastAPI(title="buildyourscribe review", version="0.1")

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
        try:
            meta = pipe.store.meta(sid)
        except (KeyError, FileNotFoundError):
            raise HTTPException(404, "no such session")
        t = pipe.store.transcript(sid)
        return {"meta": meta.__dict__, "transcript": t.as_lines() if t else None,
                "segments": t.to_dict()["segments"] if t else None, "note": pipe.store.note(sid)}

    @app.post("/api/sessions/{sid}/transcribe")
    async def transcribe(sid: str):
        t = await run_in_threadpool(pipe.transcribe, sid)
        return {"transcript": t.as_lines(), "engine": t.engine, "elapsed": t.elapsed_seconds}

    @app.post("/api/sessions/{sid}/draft")
    async def draft(sid: str, body: DraftBody):
        try:
            d = await run_in_threadpool(pipe.draft, sid, body.template, body.instructions)
        except RuntimeError as e:
            raise HTTPException(400, str(e))
        return {"note": d.text, "model": d.model, "elapsed": d.elapsed_seconds}

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


app = create_app() if __name__ == "scribe.server_autoload" else None  # pragma: no cover
