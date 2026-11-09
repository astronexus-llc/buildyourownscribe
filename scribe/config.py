"""Configuration, read once from environment variables.

Every setting has a safe default so the scribe runs with no configuration on a
single machine. Override with ``SCRIBE_*`` environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

_PRIVATE_HOSTS = ("localhost", "127.0.0.1", "::1", "0.0.0.0")


def _env(name: str, default: str) -> str:
    return os.environ.get(f"SCRIBE_{name}", default)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(f"SCRIBE_{name}")
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def is_local_url(url: str) -> bool:
    """True if ``url`` points at this machine or a private network.

    Used as a guard: the scribe refuses to send transcripts anywhere else unless
    you explicitly set ``SCRIBE_ALLOW_REMOTE_LLM=1``.
    """
    host = urlparse(url).hostname or ""
    if host in _PRIVATE_HOSTS or host.endswith(".local") or host.endswith(".lan"):
        return True
    parts = host.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        a, b = int(parts[0]), int(parts[1])
        return a == 10 or (a == 192 and b == 168) or (a == 172 and 16 <= b <= 31)
    return False


@dataclass(frozen=True)
class STTConfig:
    backend: str = _env("STT_BACKEND", "whisper")          # "whisper" or "vosk"
    whisper_model: str = _env("WHISPER_MODEL", "small.en")  # tiny.en base.en small.en medium.en large-v3
    device: str = _env("STT_DEVICE", "auto")                 # auto, cuda, cpu
    compute_type: str = _env("STT_COMPUTE", "auto")          # auto, float16, int8, int8_float16
    language: str = _env("STT_LANGUAGE", "en")
    vosk_model_path: str = _env("VOSK_MODEL", "models/vosk-model-small-en-us-0.15")
    beam_size: int = int(_env("STT_BEAM", "5"))


@dataclass(frozen=True)
class LLMConfig:
    base_url: str = _env("LLM_BASE_URL", "http://localhost:11434/v1")  # Ollama default
    model: str = _env("LLM_MODEL", "")                                  # empty = first model the server lists
    api_key: str = _env("LLM_API_KEY", "not-needed")
    temperature: float = float(_env("LLM_TEMPERATURE", "0.2"))
    max_tokens: int = int(_env("LLM_MAX_TOKENS", "2048"))
    timeout_s: float = float(_env("LLM_TIMEOUT", "300"))
    thinking: str = _env("LLM_THINKING", "off")   # off | on  (for reasoning models such as Qwen3)
    allow_remote: bool = _env_bool("ALLOW_REMOTE_LLM", False)

    def check_locality(self) -> None:
        if not self.allow_remote and not is_local_url(self.base_url):
            raise RuntimeError(
                f"LLM endpoint {self.base_url!r} is not on this machine or a private network. "
                "Transcripts contain protected health information. Set SCRIBE_ALLOW_REMOTE_LLM=1 "
                "only if you have a signed BAA with that provider and understand the consequences."
            )


@dataclass(frozen=True)
class StorageConfig:
    data_dir: Path = Path(_env("DATA_DIR", "scribe_data"))
    retention_days: int = int(_env("RETENTION_DAYS", "7"))        # unsigned sessions older than this are purged
    delete_audio_on_sign: bool = _env_bool("DELETE_AUDIO_ON_SIGN", True)


@dataclass(frozen=True)
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    device: str | None = os.environ.get("SCRIBE_MIC") or None   # sounddevice name or index


@dataclass(frozen=True)
class Settings:
    stt: STTConfig = field(default_factory=STTConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    host: str = _env("HOST", "127.0.0.1")
    port: int = int(_env("PORT", "8765"))


def load() -> Settings:
    return Settings()
