"""Step 3: transcript to draft note.

Talks to any OpenAI-compatible chat endpoint: Ollama, llama.cpp server, vLLM,
LM Studio, or a hosted provider if you have a BAA and set the override. The
prompt templates live in ``scribe/templates/*.md`` as plain text so you can
edit them without touching Python.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import httpx

from .config import LLMConfig
from .transcribe import Transcript

_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


# --------------------------------------------------------------------------- templates

def template_dir() -> Path:
    return Path(str(resources.files("scribe") / "templates"))


def list_templates(extra_dir: Path | None = None) -> dict[str, Path]:
    """Built-in templates, overridden by any ``*.md`` in ``extra_dir``."""
    found = {p.stem: p for p in sorted(template_dir().glob("*.md"))}
    if extra_dir and Path(extra_dir).is_dir():
        found.update({p.stem: p for p in sorted(Path(extra_dir).glob("*.md"))})
    return found


def load_template(name: str, extra_dir: Path | None = None) -> str:
    templates = list_templates(extra_dir)
    if name not in templates:
        raise KeyError(f"No template {name!r}. Available: {', '.join(templates)}")
    return templates[name].read_text()


def build_messages(template_text: str, transcript_lines: str, extra_instructions: str = "") -> list[dict]:
    system = template_text.strip()
    if extra_instructions.strip():
        system += "\n\nAdditional instructions from the clinician:\n" + extra_instructions.strip()
    user = "Transcript of the visit:\n\n" + transcript_lines.strip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# --------------------------------------------------------------------------- client

@dataclass
class Draft:
    text: str
    template: str
    model: str
    elapsed_seconds: float
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMClient:
    """Minimal OpenAI-compatible chat client. No SDK, just one POST."""

    def __init__(self, cfg: LLMConfig | None = None, http: httpx.Client | None = None):
        self.cfg = cfg or LLMConfig()
        self.cfg.check_locality()
        self.http = http or httpx.Client(timeout=self.cfg.timeout_s)
        self._model: str | None = self.cfg.model or None

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.cfg.api_key}", "Content-Type": "application/json"}

    def list_models(self) -> list[str]:
        r = self.http.get(f"{self.cfg.base_url}/models", headers=self.headers)
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])]

    def resolve_model(self) -> str:
        if self._model:
            return self._model
        models = self.list_models()
        if not models:
            raise RuntimeError(f"The server at {self.cfg.base_url} lists no models. Pull one first "
                               "(for Ollama: `ollama pull qwen3:8b`).")
        self._model = models[0]
        return self._model

    def health(self) -> tuple[bool, str]:
        try:
            return True, f"{self.cfg.base_url} ({self.resolve_model()})"
        except Exception as e:  # noqa: BLE001
            return False, f"{self.cfg.base_url}: {e}"

    def chat(self, messages: list[dict]) -> tuple[str, dict]:
        body = {"model": self.resolve_model(), "messages": messages,
                "temperature": self.cfg.temperature, "max_tokens": self.cfg.max_tokens, "stream": False}
        extras = {}
        if self.cfg.thinking == "off":
            # Reasoning models (Qwen3 etc.) think out loud by default; that burns minutes
            # and adds nothing to a scribe draft. vLLM/llama.cpp read chat_template_kwargs;
            # Ollama reads "think". Servers that reject unknown fields get a plain retry.
            extras = {"chat_template_kwargs": {"enable_thinking": False}, "think": False}
        url = f"{self.cfg.base_url}/chat/completions"
        r = self.http.post(url, json={**body, **extras}, headers=self.headers)
        if r.status_code == 400 and extras:
            r = self.http.post(url, json=body, headers=self.headers)
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"] or ""
        return _THINK_RE.sub("", content).strip(), data.get("usage", {}) or {}

    def draft(self, transcript: Transcript | str, template: str = "soap", extra_instructions: str = "",
              template_dir_override: Path | None = None) -> Draft:
        lines = transcript.as_lines() if isinstance(transcript, Transcript) else transcript
        messages = build_messages(load_template(template, template_dir_override), lines, extra_instructions)
        t = time.time()
        text, usage = self.chat(messages)
        return Draft(text=text, template=template, model=self.resolve_model(), elapsed_seconds=round(time.time() - t, 2),
                     prompt_tokens=usage.get("prompt_tokens", 0), completion_tokens=usage.get("completion_tokens", 0))
