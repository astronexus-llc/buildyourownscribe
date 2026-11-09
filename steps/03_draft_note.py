"""Lesson 4 - ask a local language model to draft a SOAP note from a transcript.

    python steps/03_draft_note.py transcript.txt

Works with any OpenAI-compatible server. Defaults to Ollama on this machine.
    export LLM_BASE_URL=http://localhost:11434/v1   LLM_MODEL=qwen3:8b
"""
import os
import re
import sys

import httpx

BASE = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
MODEL = os.environ.get("LLM_MODEL", "")      # empty: use whatever the server lists first

SYSTEM = """You are a medical scribe drafting a note for a licensed clinician to review and sign.
Write a SOAP note from the transcript below.
Rules: use only information in the transcript. Never add vitals, exam findings, labs, medications or
doses that were not said. If a section has nothing, write "Not discussed." Mark doubtful words [unclear].
No preamble, no disclaimers, no patient name.
Format: ## Subjective  ## Objective  ## Assessment  ## Plan"""

transcript = open(sys.argv[1]).read()
headers = {"Authorization": "Bearer not-needed"}

if not MODEL:
    MODEL = httpx.get(f"{BASE}/models", headers=headers).json()["data"][0]["id"]

body = {
    "model": MODEL,
    "messages": [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": "Transcript of the visit:\n\n" + transcript}],
    "temperature": 0.2,                 # low: we want faithful, not creative
    "max_tokens": 2048,
    "chat_template_kwargs": {"enable_thinking": False},   # reasoning models: skip the thinking monologue
    "think": False,                                         # same switch, Ollama's spelling
}
r = httpx.post(f"{BASE}/chat/completions", json=body, headers=headers, timeout=300)
r.raise_for_status()
text = r.json()["choices"][0]["message"]["content"]
text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S)   # belt and braces
print(f"[{MODEL}]", file=sys.stderr)
print(text.strip())
