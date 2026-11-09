"""Step 5: where things live, and when they die.

One folder per session under ``scribe_data/sessions/<id>/``::

    audio.wav         the recording (deleted when the note is signed, by default)
    transcript.json   timestamped segments
    note.md           the draft, then the clinician's edited version
    meta.json         status, timestamps, template, model

Plus ``scribe_data/audit.log``: one JSON line per event, append-only.
Nothing in here is encrypted; the lesson on hardening covers full-disk
encryption, which is the right layer for that.
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import StorageConfig
from .transcribe import Transcript


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class SessionMeta:
    id: str
    created: str
    status: str = "new"            # new -> transcribed -> drafted -> signed
    label: str = ""                # free text the user types, e.g. "room 3, follow-up"
    template: str = ""
    stt_engine: str = ""
    llm_model: str = ""
    audio_seconds: float = 0.0
    signed_at: str = ""
    events: list[dict] = field(default_factory=list)


class Store:
    def __init__(self, cfg: StorageConfig | None = None):
        self.cfg = cfg or StorageConfig()
        self.root = Path(self.cfg.data_dir)
        self.sessions_dir = self.root / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.root / "audit.log"

    # ---- audit -----------------------------------------------------------
    def audit(self, session_id: str, event: str, **detail) -> None:
        line = {"t": _now(), "session": session_id, "event": event, **detail}
        with self.audit_path.open("a") as f:
            f.write(json.dumps(line) + "\n")
        meta_path = self.sessions_dir / session_id / "meta.json"
        if meta_path.exists():
            meta = self.meta(session_id)
            meta.events.append(line)
            self._write_meta(meta)

    # ---- sessions --------------------------------------------------------
    def new_session(self, label: str = "") -> SessionMeta:
        sid = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        (self.sessions_dir / sid).mkdir(parents=True)
        meta = SessionMeta(id=sid, created=_now(), label=label)
        self._write_meta(meta)
        self.audit(sid, "created", label=label)
        return meta

    def path(self, sid: str, name: str) -> Path:
        p = self.sessions_dir / sid / name
        if not p.parent.is_dir():
            raise KeyError(f"No session {sid}")
        return p

    def meta(self, sid: str) -> SessionMeta:
        return SessionMeta(**json.loads(self.path(sid, "meta.json").read_text()))

    def _write_meta(self, meta: SessionMeta) -> None:
        (self.sessions_dir / meta.id / "meta.json").write_text(json.dumps(asdict(meta), indent=2))

    def update(self, sid: str, **changes) -> SessionMeta:
        meta = self.meta(sid)
        for k, v in changes.items():
            setattr(meta, k, v)
        self._write_meta(meta)
        return meta

    def list_sessions(self) -> list[SessionMeta]:
        out = []
        for d in sorted(self.sessions_dir.iterdir(), reverse=True):
            if (d / "meta.json").exists():
                out.append(self.meta(d.name))
        return out

    # ---- artifacts -------------------------------------------------------
    def save_transcript(self, sid: str, t: Transcript) -> None:
        t.save(self.path(sid, "transcript.json"))
        self.update(sid, status="transcribed", stt_engine=f"{t.engine} {t.model}", audio_seconds=t.audio_seconds)
        self.audit(sid, "transcribed", engine=t.engine, model=t.model, seconds=t.elapsed_seconds)

    def transcript(self, sid: str) -> Transcript | None:
        p = self.path(sid, "transcript.json")
        return Transcript.load(p) if p.exists() else None

    def save_note(self, sid: str, text: str, template: str = "", model: str = "", edited: bool = False) -> None:
        self.path(sid, "note.md").write_text(text)
        if edited:
            self.audit(sid, "edited", chars=len(text))
        else:
            self.update(sid, status="drafted", template=template, llm_model=model)
            self.audit(sid, "drafted", template=template, model=model)

    def note(self, sid: str) -> str | None:
        p = self.path(sid, "note.md")
        return p.read_text() if p.exists() else None

    def sign(self, sid: str, signer: str = "") -> SessionMeta:
        meta = self.update(sid, status="signed", signed_at=_now())
        self.audit(sid, "signed", signer=signer)
        if self.cfg.delete_audio_on_sign:
            self.delete_audio(sid)
        return meta

    def delete_audio(self, sid: str) -> None:
        for p in (self.sessions_dir / sid).glob("audio.*"):
            p.unlink()
            self.audit(sid, "audio_deleted", file=p.name)

    def delete_session(self, sid: str) -> None:
        shutil.rmtree(self.sessions_dir / sid)
        self.audit(sid, "purged")

    # ---- retention -------------------------------------------------------
    def purge(self, now: datetime | None = None) -> list[str]:
        """Delete unsigned sessions older than ``retention_days``. Signed notes are kept."""
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.cfg.retention_days)
        removed = []
        for meta in self.list_sessions():
            created = datetime.fromisoformat(meta.created)
            if meta.status != "signed" and created < cutoff:
                self.delete_session(meta.id)
                removed.append(meta.id)
        return removed
