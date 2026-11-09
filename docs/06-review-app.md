# Lesson 6 · The review app

*One hour.* At the end you record from a browser, watch the transcript and draft appear, edit, and sign.

```bash
scribe serve
```

Open <http://127.0.0.1:8765>. Three columns: sessions, transcript, note.

1. Type a label. Click **Record**, talk, click **Stop**. The browser uploads the recording and transcription starts.
2. Pick a template and click **Draft**.
3. Edit the note in place. **Save edits** whenever you like.
4. **Sign**. The badge turns from amber DRAFT to green SIGNED, the note locks, and the audio is deleted.

Or click **Upload** and pick `samples/visit-01.wav` to skip the recording.

## Why a web page

A browser already has a microphone recorder (`MediaRecorder`), a text editor, a clipboard, and runs on every operating system. The server is under 200 lines of FastAPI in `scribe/server.py`; the page is one HTML file, one CSS file, and one JavaScript file in `scribe/static/`. No build step, no framework, nothing to compile.

## The API

Every button on the page is one of these calls. You can drive them with `curl`, which is how the tests work.

| Method | Path | What |
|---|---|---|
| GET | `/api/health` | STT and LLM status for the header |
| GET | `/api/templates` | Names for the dropdown |
| GET, POST | `/api/sessions` | List; create by uploading audio |
| GET | `/api/sessions/{id}` | Meta, transcript, note |
| POST | `/api/sessions/{id}/transcribe` | Run speech to text |
| POST | `/api/sessions/{id}/draft` | Run the LLM with `{template, instructions}` |
| PUT | `/api/sessions/{id}/note` | Save the clinician's edits |
| POST | `/api/sessions/{id}/sign` | Lock the note, delete audio |
| DELETE | `/api/sessions/{id}` | Remove a session entirely |

The transcribe and draft handlers use `run_in_threadpool` so a two-minute CPU transcription does not freeze the page for other requests. It is still one job at a time per model; a clinic with four rooms would queue. That is a scaling problem you do not have yet.

## Design decisions you should keep

**Bound to 127.0.0.1.** The server listens only on the loopback address. Another computer on the clinic network cannot reach it. Changing `SCRIBE_HOST` to `0.0.0.0` is a one-word change and a different risk category; Lesson 7 explains what has to come with it.

**It only answers to its own name.** Listening on the loopback address keeps other computers out. It does not keep out other *websites* open in the same browser, which can ask your browser to call `127.0.0.1` for them. So the server checks two things on every request: that it was addressed to `localhost` or `127.0.0.1` rather than some other name pointed at this machine, and that any request which changes something came from its own page. Both checks are the `local_only` function near the top of `create_app()`.

**Signed means locked, on the server.** The page greys out the buttons after signing, but a greyed-out button is a courtesy, not a lock. `storage.py` refuses to change a signed session whoever asks, and the API answers `409`. A session with no note cannot be signed at all.

**Session IDs are checked.** Every ID is matched against the exact pattern the scribe generates before it is used to build a folder path. Without that check, a request to delete session `..` would delete the whole data folder. It did, in the first version of this code.

**No login.** There is one user: whoever is sitting at this machine, which is already behind the operating system's login and screen lock. Adding users means adding authentication, sessions, and an audit trail of who did what, which is where "get a professional" starts.

**The badge.** Every unsigned note shows an amber `DRAFT · not signed` badge next to it. The text box says the same in its placeholder. The sign button asks for confirmation with the words "you are attesting that you reviewed and edited it". Small things; they are the whole safety model.

**Signing deletes audio.** On by default (`SCRIBE_DELETE_AUDIO_ON_SIGN`). Once the human has signed, the recording has done its job and is a liability.

**Warnings sit above the note.** If the draft was cut off or the model server did not read the whole transcript, a red box says so before the reviewer reads a word. [Lesson 4](04-draft-note.md#two-failures-that-give-no-error) explains both.

## The browser recorder

`app.js` asks for the microphone with echo cancellation and noise suppression on, records WebM/Opus, and uploads the blob. The server's `ingest()` decodes whatever arrives and saves 16 kHz WAV. Chrome, Firefox, Safari and Edge all work. Browsers only allow microphone access on `localhost` or HTTPS, which is another reason the loopback default is convenient.

## Try

- Open the browser's developer tools (F12), Network tab, and click Draft. Watch the single POST and its JSON. That is the whole integration.
- Change the amber colour in `style.css`. Reload. The static files are served straight from disk.
- Sign a note, then try to change it from the terminal: `curl -X PUT -H 'Content-Type: application/json' -d '{"text":"x"}' http://127.0.0.1:8765/api/sessions/<id>/note`. Read the answer.
- Add a **Copy transcript** button: one line of HTML, three of JavaScript, modelled on the existing **Copy**.

Next: [Lesson 7 · Harden it](07-harden.md).
