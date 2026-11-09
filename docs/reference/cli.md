# Command line

```
scribe doctor                     check microphone, GPU, speech model, LLM server, data dir
scribe mics                       list input devices with their index
scribe record OUT.wav [--seconds N]
                                  record from the microphone until Enter (or N seconds)
scribe transcribe AUDIO [--json FILE]
                                  print a timestamped transcript; optionally save JSON
scribe note TRANSCRIPT [--template NAME] [--instructions TEXT]
                                  draft a note from a .json transcript or a .txt file
scribe run AUDIO [--template NAME] [--label TEXT] [--instructions TEXT]
                                  ingest + transcribe + draft, saved as a session
scribe sessions                   list sessions, newest first
scribe show ID                    print meta, transcript and note for one session
scribe purge                      delete unsigned sessions older than the retention period
scribe serve                      start the review app on SCRIBE_HOST:SCRIBE_PORT
```

Exit code is 0 on success, 1 on a reported error (printed as `error: ...`), 130 on Ctrl-C.

`scribe doctor` exits 1 if the LLM server is unreachable, so it works as a health check in scripts.

## Common sequences

Transcribe now, draft later with two templates:

```bash
scribe run samples/visit-01.wav --label "room 2"          # does both; or:
scribe transcribe room2.wav --json room2.json
scribe note room2.json --template soap > room2-soap.md
scribe note room2.json --template after-visit-summary > room2-avs.md
```

Nightly cleanup, only needed if you never start the review app (which purges on its own):

```bash
0 2 * * * cd /path/to/buildyourscribe && .venv/bin/scribe purge >> scribe_data/purge.log 2>&1
```
