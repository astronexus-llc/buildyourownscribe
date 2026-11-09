# Lesson 7 · Harden it

*Two hours, and a decision or two.* At the end your scribe is as safe as a careful solo clinician's laptop can be, and you know exactly where that stops.

The scribe already does several things by default. This lesson explains each, shows where it lives, and covers what the code cannot do for you.

## What the code already does

### 1. Refuses to send PHI off the machine

`config.py`, `LLMConfig.check_locality()`. Before the first request, the LLM address is checked against localhost and the private ranges (10.x, 192.168.x, 172.16-31.x, `.local`, `.lan`). Anything else raises an error naming the business associate agreement you would need. The override is `SCRIBE_ALLOW_REMOTE_LLM=1`, which you set knowingly or not at all.

!!! danger "Cloud models"
    A hosted model (OpenAI, Anthropic, a cloud Ollama) can be excellent and may be entirely appropriate **with a signed BAA and your compliance officer's approval**. Without those two things, sending a transcript to one is a reportable breach in most of the world. The flag exists for people who have the paperwork.

### 2. Listens only on this machine

`SCRIBE_HOST` defaults to `127.0.0.1`. The review page cannot be reached from any other computer.

It also refuses requests that reach it under any name other than `localhost` or `127.0.0.1`, and refuses changes requested by another website. That closes the route where a hostile page in your own browser talks to the scribe on your behalf. `server.py`, `local_only()`.

### 3. Deletes on schedule

- Audio is removed the moment a note is signed (`SCRIBE_DELETE_AUDIO_ON_SIGN=1`).
- Unsigned sessions older than `SCRIBE_RETENTION_DAYS` (7) are removed every time the review app starts, and every hour while it runs. Nothing to remember.

If you only ever use the command line and never start the review app, nothing runs the purge for you. Then schedule it:

```bash
# crontab -e
0 2 * * * cd /home/you/buildyourscribe && .venv/bin/scribe purge >> scribe_data/purge.log 2>&1
```

Signed notes are never auto-deleted. Moving them into your record system and then out of `scribe_data` is your workflow decision; `storage.py` has `delete_session()` for the script that does it.

### 4. Writes everything down

`scribe_data/audit.log` gets one line per event: created, audio saved, transcribed (with engine), drafted (with template and model), edited, signed, audio deleted, purged. Append only, plain JSON, one line each:

```json
{"t": "2026-11-09T12:44:36+00:00", "session": "20261109-074433-26dac5", "event": "signed", "signer": "Dr Test"}
{"t": "2026-11-09T12:44:36+00:00", "session": "20261109-074433-26dac5", "event": "audio_deleted", "file": "audio.wav"}
```

If anyone ever asks "what happened to the recording of that visit", this is the answer.

### 5. Locks what is signed

A signed session cannot be edited, re-drafted, re-transcribed, or signed again, from the page or from anywhere else. The check is in `storage.py`, the lowest layer, so no new feature can forget it. A session with no note cannot be signed.

### 6. Tells the reviewer when the draft is incomplete

A note cut off at the output limit, or drafted by a server that did not read the whole transcript, carries a red warning. See [Lesson 4](04-draft-note.md#two-failures-that-give-no-error).

### 7. Prompts that refuse to invent

Every built-in template forbids adding findings, requires "Not discussed." for empty sections, and asks for `[unclear]` markers. Keep those lines when you write your own.

## What the code cannot do for you

### Encrypt the disk

The scribe stores plain files. Encrypting them inside the application would mean managing keys inside the application, which is a worse idea than it sounds. The right layer is the operating system:

- **Linux:** LUKS full-disk encryption at install time, or an encrypted home directory.
- **macOS:** FileVault. It is on by default on recent machines; check System Settings.
- **Windows/WSL2:** BitLocker on the Windows volume covers the WSL disk.

With full-disk encryption and a screen lock, a stolen laptop is an inconvenience rather than a breach notification.

### Lock the screen

Set the screen to lock after two to five minutes. The review page shows a transcript. An unlocked screen in an open room is the most likely way this data leaks.

### Get consent

Say "I'd like to use a recording tool so I can pay attention instead of typing; the recording is deleted once I finish the note. Is that all right?" at the start of every visit. Note the answer. Make "no" cost nothing. Check your jurisdiction's recording consent law, and your employer's policy, before the first real visit.

### Back up, and test the restore

Signed notes in `scribe_data/sessions/` are the only thing worth backing up; models re-download and audio is deliberately transient.

```bash
rsync -a --include='*/' --include='meta.json' --include='note.md' --exclude='*' \
      scribe_data/sessions/ /media/encrypted-usb/scribe-backup/
```

A backup you have not restored from is a hope. Try it once.

### Keep the machine patched

The scribe's own dependencies: `uv pip install -e ".[cuda]" --upgrade` every month or two, then `pytest`. The operating system: however you already do it. The local model: `ollama pull qwen3:8b` fetches the latest; re-run the Lesson 8 check afterwards, because a model update can change behaviour.

## If you are tempted to put it on the network

So a colleague in the next room can use it too. Here is what that honestly requires, each a project of its own:

0. Telling the scribe its new name with `SCRIBE_ALLOWED_HOSTS`, or it will refuse every request. That is the easy part.
1. HTTPS with a real certificate (browsers will not give microphone access over plain HTTP to a non-localhost address).
2. Authentication, so the audit log can say who signed.
3. Authorisation, so one clinician cannot read another's drafts.
4. A firewall rule so only clinic machines reach it.
5. A conversation with whoever is responsible for compliance at your clinic.

None of it is exotic. All of it is where this course says [get a professional](00-what-is-an-ambient-scribe.md#where-diy-stops), and means it.

## The checklist

Before the first real patient, every line true:

- [ ] Full-disk encryption on, screen lock under five minutes
- [ ] `scribe doctor` shows the LLM at a localhost or private address
- [ ] `SCRIBE_ALLOW_REMOTE_LLM` is not set anywhere (`env | grep SCRIBE`)
- [ ] The model server's context window is larger than your longest visit, and you have drafted one long recording to prove it
- [ ] You have seen the purge work: the audit log has a `purged` line, or you start the review app daily
- [ ] You know where signed notes go after this folder, and have moved one
- [ ] A backup exists and you have restored a note from it
- [ ] You have a consent sentence and have said it out loud
- [ ] You have read the recording-consent rule for your jurisdiction
- [ ] You have done Lesson 8 on at least three role-played visits

Next: [Lesson 8 · Evaluate it](08-evaluate.md).
