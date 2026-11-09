# Build Your Scribe

**Build your own medical ambient scribe, one lesson at a time. Local-first: no audio or text leaves your machine.**

An ambient scribe listens to a clinic visit and drafts the note so the clinician reviews instead of types. Commercial ones are a subscription wrapped around four open parts. This repo is those four parts, small enough to read in an afternoon, with a course that walks you through building each one:

```
record  ->  transcribe (Whisper)  ->  draft (local LLM)  ->  review & sign  ->  store & delete on schedule
```

**The course:** https://frasod.github.io/buildyourscribe/ (or `mkdocs serve` in this repo)

## Quick start

```bash
git clone https://github.com/frasod/buildyourscribe
cd buildyourscribe
uv venv && source .venv/bin/activate          # or: python3 -m venv .venv
uv pip install -e ".[cuda]"                   # drop [cuda] on a machine without an NVIDIA GPU

ollama serve &  ollama pull qwen3:8b          # any OpenAI-compatible local server works
scribe doctor                                 # checks mic, GPU, speech model, LLM
scribe run samples/visit-01.wav               # synthetic visit -> transcript -> SOAP note, ~5 s on a GPU
scribe serve                                  # review app at http://127.0.0.1:8765
```

## What is in here

| Path | What |
|---|---|
| `scribe/` | The scribe. `audio.py` record/load, `transcribe.py` Whisper or Vosk, `notes.py` LLM client + templates, `storage.py` sessions/audit/retention, `pipeline.py` chain, `cli.py`, `server.py` + `static/` review app |
| `scribe/templates/` | Note prompts as plain Markdown: `soap`, `progress`, `after-visit-summary`, `transcript-cleanup`. Add your own in `scribe_data/templates/` |
| `steps/` | Standalone scripts for lessons 2 to 5, each short enough to read whole |
| `samples/` | A synthetic two-voice visit recording and its script. No real PHI |
| `docs/` | The course (MkDocs Material) |
| `tests/` | Run with `pytest`; no models or GPU needed |

## Ground rules baked in

- Defaults to a local LLM. Refuses to send transcripts to a non-private address unless you set `SCRIBE_ALLOW_REMOTE_LLM=1`.
- The output is a **draft** until a licensed human edits and signs it. The app says so on every screen.
- Audio is deleted when the note is signed. Unsigned sessions are purged after 7 days (`scribe purge`).
- Every event is appended to `scribe_data/audit.log`.
- Prompts forbid inventing findings and require "Not discussed." for empty sections.

This is a teaching project and a working tool, not a certified medical device. Lesson 0 and the hardening lesson cover consent, PHI, and where to stop and get professional help.

## Configuration

All via `SCRIBE_*` environment variables; see `docs/reference/configuration.md`. The two you will touch first:

```bash
export SCRIBE_WHISPER_MODEL=medium.en                 # tiny.en base.en small.en medium.en large-v3
export SCRIBE_LLM_BASE_URL=http://localhost:11434/v1  # Ollama; vLLM, llama.cpp, LM Studio all work
```

## License

MIT. The synthetic sample is CC0.
