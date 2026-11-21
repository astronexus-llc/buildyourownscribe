# Lesson 3 · Transcribe

*One hour.* At the end you have a timestamped transcript and an informed opinion about model size.

## The whole script

```python title="steps/02_transcribe.py"
--8<-- "steps/02_transcribe.py"
```

```bash
python steps/02_transcribe.py samples/visit-01.wav
```

The first run downloads the model to `~/.cache/huggingface`. That download is the only time this step needs the internet; [All open source, no cloud](open-source.md) shows what we measured. Then:

```
[00:00] Good morning, Mr. Alvarez. Come on in and have a seat. How have you been since we last saw you in July?
[00:06] Morning, Doctor.
[00:07] Mostly okay. The blood pressure has been better, I think, but I've had this cough for about three weeks now that just won't quit.
[00:14] Tell me more about the cough. Is it dry, or are you printing anything up?
...
[00:34] Okay, now, the lisinopril we started in July for your blood pressure. Are you still taking it every day?
```

!!! note "The loop near the top, for NVIDIA machines"
    `pip` installs the CUDA math libraries inside the Python environment, where the system does not look for them. The loop loads them by hand before Whisper starts. Without it the script finds your GPU, loads the model, and then stops with `Library libcublas.so.12 is not found` at the first word. On a Mac or a CPU-only machine it does nothing. The package does the same thing in `scribe/transcribe.py`.

## What Whisper is

Whisper is OpenAI's open-weights speech recognition model, trained on 680,000 hours of audio. `faster-whisper` is a reimplementation that runs two to four times faster using the CTranslate2 engine, with the same weights. It is the default speech-to-text in nearly every open scribe project for one reason: it already knows "lisinopril".

It comes in sizes. The `.en` variants are English-only and slightly better at English than the multilingual ones of the same size.

| Model | Download | VRAM | Speed on an RTX-class GPU | Medical vocabulary |
|---|---|---|---|---|
| `tiny.en` | 75 MB | <1 GB | ~100× real time | Poor |
| `base.en` | 140 MB | ~1 GB | ~70× | Fair, good enough for dictation |
| `small.en` | 480 MB | ~2 GB | ~40× | Good. **The default here** |
| `medium.en` | 1.5 GB | ~5 GB | ~15× | Very good |
| `large-v3` | 3 GB | ~10 GB | ~8× | Best, multilingual |

The speed and memory columns are rough guides from published figures, not measurements made for this course. Measure on your own machine; the script prints the time.

Try them:

```bash
python steps/02_transcribe.py samples/visit-01.wav base.en
python steps/02_transcribe.py samples/visit-01.wav medium.en
```

On CPU, `small.en` runs about 1 to 2× real time; `medium.en` is slower than real time. Pick the biggest that finishes a visit in the time you have between patients.

## The three options that matter

```python
vad_filter=True
```
Voice activity detection: skip the silent stretches before transcribing. Faster, and it removes Whisper's best-known failure, hallucinating "Thank you for watching" in silence.

```python
condition_on_previous_text=False
```
By default Whisper feeds each segment the text before it, for consistency. On long audio this sometimes locks it into repeating one sentence for minutes. Turning it off costs a little consistency and buys robustness.

```python
beam_size=5
```
How many candidate transcriptions it keeps while decoding. 5 is the standard accuracy setting. 1 is faster and a bit worse.

## Vosk: the low-power alternative

Before Whisper, open-source speech recognition meant Kaldi, and Vosk is Kaldi made easy. Its small English model is 40 MB, runs on a Raspberry Pi, and transcribes in real time on any CPU. The package supports it:

```bash
uv pip install -e ".[vosk]"
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip -d models/
SCRIBE_STT_BACKEND=vosk scribe transcribe samples/visit-01.wav
```

Here is what it produced on the same sample, alongside Whisper `small.en`:

| What was said | Vosk small | Whisper small.en |
|---|---|---|
| the lisinopril we started in July | the **listener probably** started in july | the lisinopril we started in July |
| switch you to losartan | switch you to **loss or two** | switch you to losartan |
| an ACE inhibitor cough | in **ac ie** inhibitor call | an ACE inhibitor cough |
| no wheezing, no crackles | know wheezing **new** crackles | no wheezing, no crackles |

Vosk is fine for dictating "patient seen, doing well" and wrong about every drug. It has no punctuation or capitalisation either. Use it when the hardware forces you to, and know what you are trading.

## The transcript format

The package wraps results in a `Transcript` of `Segment(start, end, text)` and saves it as JSON. `as_lines()` renders the `[mm:ss] text` form you saw. Timestamps go to the language model in the next lesson on purpose: they let the note say "stated at 01:26" if you ask, and they let a reviewer jump to the audio.

```bash
scribe transcribe samples/visit-01.wav --json transcript.json
```

## Try

- Transcribe your recording from Lesson 2 with `base.en` and `medium.en`. Count the word errors.
- Mumble a drug name. Then say it clearly. Whisper's confidence is in the model; yours is in the diction.
- Look at `[00:14]` above: "printing anything up" for "bringing anything up". Whisper is not magic. Lesson 8 is about catching this.

Next: [Lesson 4 · Draft the note](04-draft-note.md).
