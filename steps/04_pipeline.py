"""Lesson 5 - the three pieces, chained, using the scribe package.

    python steps/04_pipeline.py samples/visit-01.wav [template]

This is what `scribe run` does. Read scribe/pipeline.py next; it is about 70 lines.
"""
import sys

from scribe.pipeline import Pipeline

audio = sys.argv[1]
template = sys.argv[2] if len(sys.argv) > 2 else "soap"

pipe = Pipeline()                              # reads SCRIBE_* environment variables
meta = pipe.ingest(audio, label="lesson 5")    # 1. session folder + audio.wav
transcript = pipe.transcribe(meta.id)          # 2. transcript.json
draft = pipe.draft(meta.id, template)          # 3. note.md

print(transcript.as_lines())
print("\n" + "=" * 60 + "\n")
print(draft.text)
print(f"\nsession {meta.id}: {transcript.elapsed_seconds}s to transcribe, {draft.elapsed_seconds}s to draft",
      file=sys.stderr)
