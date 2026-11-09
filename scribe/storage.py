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
import re
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import StorageConfig
from .transcribe import Transcript


_SESSION_ID = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")


class SessionLocked(RuntimeError):
    """Raised when something tries to change a signed session."""


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
    warnings: list[str] = field(default_factory=list)   # e.g. "note was cut off"; shown to the reviewer
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
        if _SESSION_ID.match(session_id) and (self.sessions_dir / session_id / "meta.json").exists():
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

    def dir(self, sid: str) -> Path:
        """The session's folder. The id must look like one we made: this is the
        only thing standing between a request for ``..`` and the data folder."""
        if not _SESSION_ID.match(sid or ""):
            raise KeyError(f"No session {sid}")
        d = self.sessions_dir / sid
        if not d.is_dir():
            raise KeyError(f"No session {sid}")
        return d

    def path(self, sid: str, name: str) -> Path:
        return self.dir(sid) / name

    def meta(self, sid: str) -> SessionMeta:
        known = SessionMeta.__dataclass_fields__
        raw = json.loads(self.path(sid, "meta.json").read_text())
        return SessionMeta(**{k: v for k, v in raw.items() if k in known})

    def require_unsigned(self, sid: str) -> SessionMeta:
        meta = self.meta(sid)
        if meta.status == "signed":
            raise SessionLocked(f"Session {sid} is signed and can no longer be changed")
        return meta

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
        self.require_unsigned(sid)
        t.save(self.path(sid, "transcript.json"))
        self.update(sid, status="transcribed", stt_engine=f"{t.engine} {t.model}", audio_seconds=t.audio_seconds)
        self.audit(sid, "transcribed", engine=t.engine, model=t.model, seconds=t.elapsed_seconds)

    def transcript(self, sid: str) -> Transcript | None:
        p = self.path(sid, "transcript.json")
        return Transcript.load(p) if p.exists() else None

    def save_note(self, sid: str, text: str, template: str = "", model: str = "", edited: bool = False,
                  warnings: list[str] | None = None) -> None:
        self.require_unsigned(sid)
        self.path(sid, "note.md").write_text(text)
        if edited:
            self.audit(sid, "edited", chars=len(text))
        else:
            self.update(sid, status="drafted", template=template, llm_model=model, warnings=list(warnings or []))
            self.audit(sid, "drafted", template=template, model=model, warnings=list(warnings or []))

    def note(self, sid: str) -> str | None:
        p = self.path(sid, "note.md")
        return p.read_text() if p.exists() else None

    def sign(self, sid: str, signer: str = "") -> SessionMeta:
        self.require_unsigned(sid)
        if not (self.note(sid) or "").strip():
            raise RuntimeError("There is no note to sign yet")
        meta = self.update(sid, status="signed", signed_at=_now())
        self.audit(sid, "signed", signer=signer)
        if self.cfg.delete_audio_on_sign:
            self.delete_audio(sid)
        return meta

    def delete_audio(self, sid: str) -> None:
        for p in self.dir(sid).glob("audio.*"):
            p.unlink()
            self.audit(sid, "audio_deleted", file=p.name)

    def delete_session(self, sid: str) -> None:
        shutil.rmtree(self.dir(sid))
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
