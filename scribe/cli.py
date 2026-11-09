"""Command line front door. ``scribe --help`` lists everything.

    scribe doctor                      check microphone, GPU, model, LLM server
    scribe mics                        list input devices
    scribe record out.wav              record until Enter
    scribe transcribe visit.wav        print a timestamped transcript
    scribe note transcript.json        draft a note from a saved transcript
    scribe run visit.wav               audio -> transcript -> note, saved as a session
    scribe sessions                    list sessions
    scribe show <id>                   print a session's transcript and note
    scribe purge                       apply the retention policy
    scribe serve                       start the review web app
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import Settings


def cmd_doctor(args, s: Settings) -> int:
    from .audio import list_microphones
    from .notes import LLMClient
    from .transcribe import cuda_available

    print(f"buildyourscribe {__version__}")
    print(f"python          {sys.version.split()[0]}")
    mics = list_microphones()
    print(f"microphones     {len(mics)} found" + ("" if mics else "  <- none; plug one in"))
    for m in mics[:8]:
        print(f"                {m}")
    gpu = cuda_available()
    print(f"gpu (cuda)      {'yes' if gpu else 'no, whisper will run on CPU (slower, still fine)'}")
    print(f"stt             {s.stt.backend} model={s.stt.whisper_model if s.stt.backend == 'whisper' else s.stt.vosk_model_path}")
    try:
        ok, info = LLMClient(s.llm).health()
    except RuntimeError as e:
        ok, info = False, str(e)
    print(f"llm             {'ok ' if ok else 'NOT REACHABLE '} {info}")
    if not ok:
        print("                start a local server first, e.g. `ollama serve` then `ollama pull qwen3:8b`")
    print(f"data dir        {s.storage.data_dir.resolve()}  retention={s.storage.retention_days}d  "
          f"delete_audio_on_sign={s.storage.delete_audio_on_sign}")
    return 0 if ok else 1


def cmd_mics(args, s: Settings) -> int:
    from .audio import list_microphones

    print("\n".join(list_microphones()) or "No input devices found.")
    return 0


def cmd_record(args, s: Settings) -> int:
    from .audio import record

    record(Path(args.out), s.audio, max_seconds=args.seconds)
    return 0


def cmd_transcribe(args, s: Settings) -> int:
    from .transcribe import make_transcriber

    tr = make_transcriber(s.stt)
    t = tr.transcribe_file(Path(args.audio))
    if args.json:
        t.save(Path(args.json))
        print(f"wrote {args.json}", file=sys.stderr)
    print(t.as_lines())
    print(f"\n[{t.engine} {t.model}: {t.audio_seconds:.0f}s of audio in {t.elapsed_seconds}s]", file=sys.stderr)
    return 0


def cmd_note(args, s: Settings) -> int:
    from .notes import LLMClient
    from .transcribe import Transcript

    p = Path(args.transcript)
    text = Transcript.load(p) if p.suffix == ".json" else p.read_text()
    d = LLMClient(s.llm).draft(text, template=args.template, extra_instructions=args.instructions or "")
    print(d.text)
    print(f"\n[{d.model}: {d.completion_tokens} tokens in {d.elapsed_seconds}s]", file=sys.stderr)
    for w in d.warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    return 0


def cmd_run(args, s: Settings) -> int:
    from .pipeline import Pipeline

    p = Pipeline(s)
    sid = p.run(Path(args.audio), template=args.template, label=args.label or "", extra_instructions=args.instructions or "")
    print(f"session {sid}")
    print(p.store.note(sid))
    for w in p.store.meta(sid).warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    return 0


def cmd_sessions(args, s: Settings) -> int:
    from .storage import Store

    for m in Store(s.storage).list_sessions():
        print(f"{m.id}  {m.status:<11} {m.audio_seconds:>5.0f}s  {m.label}")
    return 0


def cmd_show(args, s: Settings) -> int:
    from .storage import Store

    st = Store(s.storage)
    print(json.dumps(st.meta(args.id).__dict__, indent=2))
    t = st.transcript(args.id)
    if t:
        print("\n--- transcript ---\n" + t.as_lines())
    n = st.note(args.id)
    if n:
        print("\n--- note ---\n" + n)
    return 0


def cmd_purge(args, s: Settings) -> int:
    from .storage import Store

    removed = Store(s.storage).purge()
    print(f"purged {len(removed)} unsigned session(s) older than {s.storage.retention_days} days")
    return 0


def cmd_serve(args, s: Settings) -> int:
    import uvicorn

    from .server import create_app

    print(f"Review app on http://{s.host}:{s.port}  (Ctrl-C to stop)")
    if s.host not in ("127.0.0.1", "localhost", "::1"):
        print(f"WARNING: listening on {s.host}, not just this machine. Read Lesson 7 first.", file=sys.stderr)
    uvicorn.run(create_app(s), host=s.host, port=s.port, log_level="warning")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scribe", description="Build-your-own ambient medical scribe.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="check the environment").set_defaults(fn=cmd_doctor)
    sub.add_parser("mics", help="list microphones").set_defaults(fn=cmd_mics)

    r = sub.add_parser("record", help="record from the microphone to a WAV file")
    r.add_argument("out")
    r.add_argument("--seconds", type=float, help="stop automatically after N seconds")
    r.set_defaults(fn=cmd_record)

    t = sub.add_parser("transcribe", help="transcribe an audio file")
    t.add_argument("audio")
    t.add_argument("--json", help="also save the transcript as JSON here")
    t.set_defaults(fn=cmd_transcribe)

    n = sub.add_parser("note", help="draft a note from a transcript (.json or .txt)")
    n.add_argument("transcript")
    n.add_argument("--template", default="soap")
    n.add_argument("--instructions", help="extra instructions appended to the template")
    n.set_defaults(fn=cmd_note)

    ru = sub.add_parser("run", help="audio -> transcript -> note, saved as a session")
    ru.add_argument("audio")
    ru.add_argument("--template", default="soap")
    ru.add_argument("--label")
    ru.add_argument("--instructions")
    ru.set_defaults(fn=cmd_run)

    sub.add_parser("sessions", help="list sessions").set_defaults(fn=cmd_sessions)
    sh = sub.add_parser("show", help="show one session")
    sh.add_argument("id")
    sh.set_defaults(fn=cmd_show)
    sub.add_parser("purge", help="delete unsigned sessions past retention").set_defaults(fn=cmd_purge)
    sub.add_parser("serve", help="start the review web app").set_defaults(fn=cmd_serve)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args, Settings())
    except KeyboardInterrupt:
        return 130
    except (RuntimeError, FileNotFoundError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
