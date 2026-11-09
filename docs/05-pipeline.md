# Lesson 5 · Assemble the pipeline

*Forty-five minutes.* At the end you understand the package well enough to change any part, and you have a session on disk.

## From scripts to a package

The three scripts work. They also have a problem: each loads its model on every run. Whisper `small.en` takes two seconds to load, `medium.en` ten. The language model server keeps its own model warm, but the scribe needs somewhere to keep the transcriber, remember what has been done, and write things down. That somewhere is the `scribe` package.

```
scribe/
├── config.py      every setting, read once from SCRIBE_* environment variables
├── audio.py       record(), load(), save_wav()           <- Lesson 2
├── transcribe.py  WhisperTranscriber, VoskTranscriber     <- Lesson 3
├── notes.py       LLMClient, templates                    <- Lesson 4
├── storage.py     Store: sessions, audit log, purge       <- Lesson 7
├── pipeline.py    Pipeline: chains the above              <- this lesson
├── cli.py         the `scribe` command
└── server.py      the review app                          <- Lesson 6
```

Each module does one thing and can be used alone. `pipeline.py` is the only one that imports all the others.

## The pipeline in fifteen lines

```python title="steps/04_pipeline.py"
--8<-- "steps/04_pipeline.py"
```

```bash
python steps/04_pipeline.py samples/visit-01.wav
```

Now read `scribe/pipeline.py`. Three things to notice:

**Lazy loading.** `Pipeline.transcriber` and `.llm` are properties that create the model on first use. Starting the review app is instant; the first transcription pays the load cost once.

**Sessions.** `ingest()` creates a folder under `scribe_data/sessions/<id>/` and stores the audio as a normalised WAV. Everything after that is keyed by the session id. You can stop after transcribing and draft later, or draft again with a different template.

**Injection.** The constructor accepts a transcriber, an LLM client and a store. That is how the test suite runs the whole server with fake models in a third of a second (`tests/test_server.py`). It is also how you would plug in a different speech engine without touching anything else.

## What is on disk

```
scribe_data/
├── audit.log                       one JSON line per event, append only
├── templates/                      your own templates go here (Lesson 9)
└── sessions/
    └── 20261109-074309-2f4500/
        ├── audio.wav               deleted when the note is signed
        ├── transcript.json         segments with timestamps
        ├── note.md                 the draft, then your edited version
        └── meta.json               status, template, model, event history
```

```bash
scribe sessions
scribe show 20261109-074309-2f4500
tail -5 scribe_data/audit.log
```

Everything is a plain file. You can `grep` it, back it up with `rsync`, and read it in ten years. No database until you need one, and a single clinician never does.

## The command line

`scribe/cli.py` is one function per subcommand, no framework. `scribe run` is `Pipeline.run()` and a print. If you want a `scribe export` that writes the note to a USB stick, it is a ten-line function and a parser entry. The [CLI reference](reference/cli.md) lists what exists.

## Try

- Run `steps/04_pipeline.py` twice in a row and compare the transcription times. They are the same: each `python` process loads Whisper fresh. The review app in the next lesson is a single long-running process, which is why it feels faster after the first visit.
- Add a `SCRIBE_DEFAULT_TEMPLATE` setting. It touches `config.py` (one field) and `cli.py` (two default values). There is no such setting today on purpose: templates are chosen per draft. Deciding whether that is the right call is the exercise.

Next: [Lesson 6 · The review app](06-review-app.md).
