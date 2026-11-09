"""Step 4: chain the pieces. Audio file in, transcript + draft note out, saved to a session."""

from __future__ import annotations

from pathlib import Path

from .audio import load, save_wav
from .config import Settings
from .notes import LLMClient
from .storage import SessionMeta, Store
from .transcribe import Transcriber, make_transcriber


class Pipeline:
    """Holds the loaded models so repeated runs do not reload them."""

    def __init__(self, settings: Settings | None = None, transcriber: Transcriber | None = None,
                 llm: LLMClient | None = None, store: Store | None = None):
        self.settings = settings or Settings()
        self._transcriber = transcriber
        self._llm = llm
        self.store = store or Store(self.settings.storage)

    @property
    def transcriber(self) -> Transcriber:
        if self._transcriber is None:
            self._transcriber = make_transcriber(self.settings.stt)
        return self._transcriber

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient(self.settings.llm)
        return self._llm

    def ingest(self, audio_path: Path, label: str = "") -> SessionMeta:
        """Create a session and store the audio as 16 kHz mono WAV."""
        meta = self.store.new_session(label)
        audio = load(audio_path)
        save_wav(audio, self.store.path(meta.id, "audio.wav"))
        self.store.audit(meta.id, "audio_saved", seconds=round(len(audio) / 16000, 1), source=Path(audio_path).name)
        return meta

    def transcribe(self, sid: str):
        self.store.require_unsigned(sid)
        audio = self.store.path(sid, "audio.wav")
        if not audio.exists():
            raise FileNotFoundError(f"Session {sid} has no audio to transcribe")
        t = self.transcriber.transcribe_file(audio)
        self.store.save_transcript(sid, t)
        return t

    def draft(self, sid: str, template: str = "soap", extra_instructions: str = ""):
        self.store.require_unsigned(sid)
        t = self.store.transcript(sid)
        if t is None:
            raise RuntimeError("Transcribe before drafting")
        d = self.llm.draft(t, template=template, extra_instructions=extra_instructions,
                           template_dir_override=self.store.root / "templates")
        self.store.save_note(sid, d.text, template=template, model=d.model, warnings=d.warnings)
        return d

    def run(self, audio_path: Path, template: str = "soap", label: str = "", extra_instructions: str = "") -> str:
        """The whole thing. Returns the session id."""
        meta = self.ingest(audio_path, label)
        self.transcribe(meta.id)
        self.draft(meta.id, template, extra_instructions)
        return meta.id
