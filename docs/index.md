# Build Your Scribe

**Build your own medical ambient scribe, one lesson at a time. Nothing leaves your machine.**

An ambient scribe listens to a clinic visit and drafts the note, so the clinician reviews instead of types. The commercial products are a subscription wrapped around four parts you can run yourself:

```
 record a visit  ->  transcribe it  ->  draft the note  ->  review, sign, store
   (microphone)        (Whisper)        (local LLM)         (a web page)
```

This course builds each part in turn. By lesson 6 you have a working scribe with a review screen. Lessons 7 and 8 make it safe and teach you to check its work. Lessons 9 and 10 make it yours.

<div class="grid cards" markdown>

- **Who it is for**

    Clinicians, clinic staff, and students who can open a terminal and copy a command. No programming background required. If you have one, you will read the code faster; it is about 1,200 lines of Python in total.

- **What you need**

    One computer you control. An NVIDIA GPU or a recent Mac makes it fast; a plain laptop works, slower. A microphone. About 10 GB of disk for models. No internet after setup.

- **What you get**

    A command line tool (`scribe`), a local review web app, four note templates, a synthetic test visit, and the understanding to change any of it.

- **What it is not**

    Not a certified medical device, not legal advice, not a replacement for your judgment. The output is a draft until a licensed human signs it. [Lesson 0](00-what-is-an-ambient-scribe.md) covers the boundaries.

</div>

## The thirty-second version

```bash
git clone https://github.com/frasod/buildyourscribe && cd buildyourscribe
uv venv && source .venv/bin/activate && uv pip install -e ".[cuda]"
ollama pull qwen3:8b                      # or any local OpenAI-compatible server
scribe run samples/visit-01.wav           # synthetic visit -> transcript -> SOAP note
```

On a desktop GPU that takes about five seconds end to end. Then `scribe serve` opens the review app.

## Ground rules, from the first line of code

1. **Local by default.** The scribe refuses to send a transcript to any address that is not on your machine or private network unless you override it on purpose.
2. **Drafts are drafts.** Every screen says so until a human signs.
3. **Delete on schedule.** Audio goes when the note is signed. Unsigned work is purged after seven days.
4. **Write down what happened.** Every step appends to an audit log.
5. **Never invent.** The prompts forbid adding findings and require "Not discussed." where the transcript is silent.

Start with [Lesson 0](00-what-is-an-ambient-scribe.md) if you are new to this, or jump to [Lesson 1](01-setup.md) to start installing.
