"""Step 3: transcript to draft note.

Talks to any OpenAI-compatible chat endpoint: Ollama, llama.cpp server, vLLM,
LM Studio, or a hosted provider if you have a BAA and set the override. The
prompt templates live in ``scribe/templates/*.md`` as plain text so you can
edit them without touching Python.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
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
    warnings: list[str] = field(default_factory=list)


# English prose runs about four characters per token. If the server reports a
# prompt far smaller than that, it did not read all of what we sent.
_CHARS_PER_TOKEN_ALARM = 6


def check_draft(messages: list[dict], usage: dict, finish_reason: str) -> list[str]:
    """Things the reviewer must know that the note itself will not tell them."""
    warnings = []
    if finish_reason == "length":
        warnings.append("The note was cut off at the output limit and is incomplete. "
                        "Raise SCRIBE_LLM_MAX_TOKENS and draft again.")
    sent_chars = sum(len(m["content"]) for m in messages)
    prompt_tokens = usage.get("prompt_tokens", 0)
    if prompt_tokens and sent_chars / prompt_tokens > _CHARS_PER_TOKEN_ALARM:
        warnings.append("The model server read only part of the transcript (its context window is too small), "
                        "so part of the visit is missing from this note. Raise the server's context length "
                        "and draft again.")
    return warnings


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

    def _thinking_off_ladder(self) -> list[dict]:
        """Extra request fields to try, most complete first, ending with none.

        Reasoning models (Qwen3 etc.) think before answering by default. That burns time
        and reply tokens and adds nothing to a scribe draft. There is no single switch:
        vLLM and llama.cpp read `chat_template_kwargs`, Ollama's OpenAI endpoint reads only
        `reasoning_effort` (it ignores `think` there; tested on Ollama 0.40 with qwen3:8b), and
        Ollama's native API reads `think`. A server that rejects a field it does not know
        gets the next, shorter set.
        """
        if self.cfg.thinking != "off":
            return [{}]
        template = {"chat_template_kwargs": {"enable_thinking": False}, "think": False}
        return [{**template, "reasoning_effort": "none"}, template, {}]

    def chat(self, messages: list[dict]) -> tuple[str, dict, str]:
        """Returns (text, usage, finish_reason)."""
        body = {"model": self.resolve_model(), "messages": messages,
                "temperature": self.cfg.temperature, "max_tokens": self.cfg.max_tokens, "stream": False}
        url = f"{self.cfg.base_url}/chat/completions"
        r = None
        for extras in self._thinking_off_ladder():
            r = self.http.post(url, json={**body, **extras}, headers=self.headers)
            if r.status_code not in (400, 422) or not extras:
                break
        r.raise_for_status()
        data = r.json()
        choice = data["choices"][0]
        content = choice["message"]["content"] or ""
        return _THINK_RE.sub("", content).strip(), data.get("usage", {}) or {}, choice.get("finish_reason") or ""

    def draft(self, transcript: Transcript | str, template: str = "soap", extra_instructions: str = "",
              template_dir_override: Path | None = None) -> Draft:
        lines = transcript.as_lines() if isinstance(transcript, Transcript) else transcript
        messages = build_messages(load_template(template, template_dir_override), lines, extra_instructions)
        t = time.time()
        text, usage, finish_reason = self.chat(messages)
        return Draft(text=text, template=template, model=self.resolve_model(), elapsed_seconds=round(time.time() - t, 2),
                     prompt_tokens=usage.get("prompt_tokens", 0), completion_tokens=usage.get("completion_tokens", 0),
                     warnings=check_draft(messages, usage, finish_reason))
