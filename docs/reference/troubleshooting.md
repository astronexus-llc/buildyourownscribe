# Troubleshooting

`scribe doctor` first. Then find your symptom.

## Install

**`No module named 'scribe'`.** The virtual environment is not active. `source .venv/bin/activate`, and check the prompt shows `(.venv)`.

**`OSError: PortAudio library not found`.** Linux needs the system library: `sudo apt install libportaudio2`. Mac: `brew install portaudio`.

**`av.open() got an unexpected keyword argument 'metadata_errors'`.** A PyAV newer than faster-whisper expects. `uv pip install "av<16"`. The project pins this; you will only see it if you installed faster-whisper by hand.

## GPU

**`Library libcublas.so.12 is not found` or `libcudnn` errors.** The CUDA math libraries are missing. `uv pip install -e ".[cuda]"` installs them through pip; the scribe and `steps/02_transcribe.py` load them at start, no `LD_LIBRARY_PATH` needed. Your own script needs the same few lines; copy them from the lesson script. If you still see it, `nvidia-smi` must work first; if it does not, it is a driver issue.

**`CUDA out of memory`.** Smaller Whisper model, or `SCRIBE_STT_COMPUTE=int8_float16`, or close whatever else is using the GPU (`nvidia-smi` shows it). If the LLM server shares the GPU, it may have taken all the memory; Ollama frees it after a few minutes idle, vLLM never does.

**`gpu (cuda) no` but you have an NVIDIA card.** Driver too old for the CUDA 12 libraries. Update the driver. Meanwhile CPU works.

## Speech to text

**The transcript repeats one sentence over and over.** Whisper's known failure on long audio. The package sets `condition_on_previous_text=False` which mostly prevents it. If you still see it, the audio probably has a long stretch of noise; `vad_filter=True` should skip it, so check the recording.

**"Thank you for watching" or "Subtitles by..." in the transcript.** Hallucination in silence. Same fix: VAD is on by default; check the audio is not mostly silence or music.

**Everything is one segment with no timestamps.** Vosk without word timings; the package sets `SetWords(True)`. If you are using your own Vosk code, add it.

**Drug names consistently wrong.** Bigger model. Then a better microphone. Then `initial_prompt` with your vocabulary (Lessons 9 and 10).

**Slow on CPU.** Expected. `base.en`, or buy a GPU, or accept it and transcribe while you see the next patient.

## Language model

**`NOT REACHABLE` in doctor.** `curl http://localhost:11434/v1/models`. If connection refused: `ollama serve`. If it returns `{"data":[]}`: `ollama pull qwen3:8b`. If it is on another port or machine: `SCRIBE_LLM_BASE_URL`.

**`LLM endpoint ... is not on this machine or a private network`.** The locality guard. Intended. Lesson 7 explains; `SCRIBE_ALLOW_REMOTE_LLM=1` overrides if you have the paperwork, which [Cloud models and PHI](../cloud-phi.md) describes.

**The note starts with "Here is the SOAP note..." or ends with a disclaimer.** Weak model or a template missing the "no preamble" rule. Check the template, then try a bigger model.

**The note takes minutes.** A reasoning model thinking: `SCRIBE_LLM_THINKING` should be `off`. Or CPU inference with a big model: try `qwen3:4b`. Or the server is loading the model into memory on first request, which is normal once.

**A red warning says the note was cut off.** The model hit `SCRIBE_LLM_MAX_TOKENS` before it finished. Raise it and draft again.

**A red warning says the server read only part of the transcript, or the note ignores the start of the visit, or the note comes back as a chatty summary instead of your template.** The model server's context window is smaller than the visit, and it dropped the start of the request. On Ollama, `ollama ps` shows the window under CONTEXT. Raise it with `OLLAMA_CONTEXT_LENGTH=16384` (or more), restart Ollama, and draft again. Lesson 4 shows where to set it.

**`<think>` text in the note.** The package strips it; if you see it, you are running an old copy or your own client. The regex is in `notes.py`.

**Empty note or `400 Bad Request`.** The server rejected the request. Run with `SCRIBE_LLM_THINKING=on` to drop the extra fields; if that fixes it, the server does not accept unknown parameters and the automatic retry should have caught it, so please open an issue with the server name and version.

## Review app

**Record button does nothing.** The browser refused microphone access. It only grants it on `localhost`/`127.0.0.1` or HTTPS. Check the address bar, then the padlock or site settings for a blocked microphone permission.

**Upload works, Record produces a session with 0 seconds.** The browser recorded a format the decoder could not read. Rare. Check the server terminal for the error; `ffmpeg -i` on a saved blob tells you what it is.

**`This scribe only answers on its own address`.** You opened the page under a name the scribe does not know, such as the machine's hostname. Use `http://127.0.0.1:8765`. Off localhost, see `SCRIBE_ALLOWED_HOSTS` and Lesson 7.

**`is signed and can no longer be changed`.** Intended. A signed note is locked. If it is wrong, the correction belongs in your record system as an addendum, not in a silently altered note.

**Another computer cannot open the page.** Correct. `SCRIBE_HOST` is `127.0.0.1` on purpose; Lesson 7.

## Storage

**`scribe purge` deleted something I wanted.** It only removes *unsigned* sessions older than `SCRIBE_RETENTION_DAYS`. Sign what you want to keep, or raise the number. The audit log records what was purged and when.

**Audio file is gone.** Signed notes delete their audio by default. `SCRIBE_DELETE_AUDIO_ON_SIGN=0` to keep it, and decide how you will delete it later instead.
