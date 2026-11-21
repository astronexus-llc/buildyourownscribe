"""Step 2: audio to transcript.

Two interchangeable engines behind one ``Transcriber`` interface:

* ``WhisperTranscriber`` (default): faster-whisper, GPU if available. Best
  accuracy on medical vocabulary; pick the biggest model your machine runs.
* ``VoskTranscriber`` (optional): tiny CPU-only Kaldi models, fine for
  dictation on a weak laptop, weaker on drug names.
"""

from __future__ import annotations

import ctypes
import glob
import json
import os
import site
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .config import STTConfig

# onnxruntime, which faster-whisper uses to skip silence, reports usage to Microsoft
# on every run unless told not to (measured on onnxruntime 1.31: two connections to
# mobile.events.data.microsoft.com). A scribe has no business calling anywhere, so
# switch it off before the library loads. Set ORT_DISABLE_TELEMETRY=0 to undo.
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class Transcript:
    segments: list[Segment] = field(default_factory=list)
    engine: str = ""
    model: str = ""
    audio_seconds: float = 0.0
    elapsed_seconds: float = 0.0

    @property
    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments if s.text.strip())

    def as_lines(self) -> str:
        """``[mm:ss] text`` per segment. This is what we hand to the LLM."""
        out = []
        for s in self.segments:
            m, sec = divmod(int(s.start), 60)
            out.append(f"[{m:02d}:{sec:02d}] {s.text.strip()}")
        return "\n".join(out)

    def to_dict(self) -> dict:
        return {"engine": self.engine, "model": self.model, "audio_seconds": self.audio_seconds,
                "elapsed_seconds": self.elapsed_seconds, "segments": [asdict(s) for s in self.segments]}

    @classmethod
    def from_dict(cls, d: dict) -> "Transcript":
        return cls(segments=[Segment(**s) for s in d.get("segments", [])], engine=d.get("engine", ""),
                   model=d.get("model", ""), audio_seconds=d.get("audio_seconds", 0.0),
                   elapsed_seconds=d.get("elapsed_seconds", 0.0))

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "Transcript":
        return cls.from_dict(json.loads(Path(path).read_text()))


# --------------------------------------------------------------------------- CUDA helper

def _preload_cuda_libs() -> None:
    """Make pip-installed CUDA libraries visible to CTranslate2.

    ``pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`` drops the .so files
    inside site-packages, where the dynamic loader does not look. Loading them
    with RTLD_GLOBAL first lets faster-whisper find them without touching
    LD_LIBRARY_PATH. Harmless when the packages are absent.
    """
    if sys.platform != "linux":
        return
    dirs = []
    for sp in set(site.getsitepackages() + [site.getusersitepackages()]):
        dirs += glob.glob(f"{sp}/nvidia/cublas/lib") + glob.glob(f"{sp}/nvidia/cudnn/lib")
    for d in dirs:
        for pattern in ("libcublasLt.so.*", "libcublas.so.*", "libcudnn.so.*"):
            for lib in sorted(glob.glob(f"{d}/{pattern}")):
                try:
                    ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass


def cuda_available() -> bool:
    try:
        _preload_cuda_libs()
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def resolve_whisper_model(name: str) -> str:
    """Return a folder holding the Whisper model, downloading it only if it is not cached.

    Left to itself faster-whisper asks huggingface.co on every start whether the
    model has changed, even when it is already on disk. We look on disk first and
    go to the network only for the one-time download, so a cached scribe starts
    with no outside connection at all.
    """
    if os.path.isdir(name):
        return name
    from faster_whisper.utils import download_model

    try:
        return download_model(name, local_files_only=True)
    except Exception:
        print(f"Whisper model {name!r} is not on this machine yet; downloading it once "
              "from huggingface.co.", file=sys.stderr)
        return download_model(name)


# --------------------------------------------------------------------------- engines

class Transcriber:
    name = "base"

    def transcribe(self, audio: np.ndarray) -> Transcript:  # pragma: no cover - interface
        raise NotImplementedError

    def transcribe_file(self, path: Path) -> Transcript:
        from .audio import load

        return self.transcribe(load(path))


class WhisperTranscriber(Transcriber):
    name = "whisper"

    def __init__(self, cfg: STTConfig | None = None):
        from faster_whisper import WhisperModel

        self.cfg = cfg or STTConfig()
        device = self.cfg.device
        if device == "auto":
            device = "cuda" if cuda_available() else "cpu"
        elif device == "cuda":
            _preload_cuda_libs()
        compute = self.cfg.compute_type
        if compute == "auto":
            compute = "float16" if device == "cuda" else "int8"
        self.device, self.compute = device, compute
        t = time.time()
        self.model = WhisperModel(resolve_whisper_model(self.cfg.whisper_model), device=device,
                                  compute_type=compute)
        self.load_seconds = time.time() - t

    def transcribe(self, audio: np.ndarray) -> Transcript:
        t = time.time()
        segments, _info = self.model.transcribe(
            audio,
            language=self.cfg.language or None,
            beam_size=self.cfg.beam_size,
            vad_filter=True,                       # skip silence; big speed win on real visits
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,      # fewer repetition loops on long audio
        )
        segs = [Segment(round(s.start, 2), round(s.end, 2), s.text.strip()) for s in segments]
        return Transcript(segments=segs, engine=f"faster-whisper/{self.device}/{self.compute}",
                          model=self.cfg.whisper_model, audio_seconds=len(audio) / 16000,
                          elapsed_seconds=round(time.time() - t, 2))


class VoskTranscriber(Transcriber):
    name = "vosk"

    def __init__(self, cfg: STTConfig | None = None):
        import vosk

        self.cfg = cfg or STTConfig()
        path = Path(self.cfg.vosk_model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Vosk model not found at {path}. Download one from https://alphacephei.com/vosk/models "
                "and set SCRIBE_VOSK_MODEL to the extracted folder.")
        vosk.SetLogLevel(-1)
        self.model = vosk.Model(str(path))

    def transcribe(self, audio: np.ndarray) -> Transcript:
        import vosk

        t = time.time()
        rec = vosk.KaldiRecognizer(self.model, 16000)
        rec.SetWords(True)
        pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes()
        segs: list[Segment] = []

        def take(result_json: str) -> None:
            r = json.loads(result_json)
            words = r.get("result") or []
            if r.get("text") and words:
                segs.append(Segment(round(words[0]["start"], 2), round(words[-1]["end"], 2), r["text"]))

        step = 16000 * 2  # one-second chunks of int16
        for i in range(0, len(pcm), step):
            if rec.AcceptWaveform(pcm[i:i + step]):
                take(rec.Result())
        take(rec.FinalResult())
        return Transcript(segments=segs, engine="vosk/cpu", model=Path(self.cfg.vosk_model_path).name,
                          audio_seconds=len(audio) / 16000, elapsed_seconds=round(time.time() - t, 2))


def make_transcriber(cfg: STTConfig | None = None) -> Transcriber:
    cfg = cfg or STTConfig()
    if cfg.backend == "vosk":
        return VoskTranscriber(cfg)
    if cfg.backend == "whisper":
        return WhisperTranscriber(cfg)
    raise ValueError(f"Unknown SCRIBE_STT_BACKEND={cfg.backend!r} (use 'whisper' or 'vosk')")
