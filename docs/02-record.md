# Lesson 2 · Record a visit

*Thirty minutes.* At the end you have a WAV file of your own voice and understand why it is 16 kHz mono.

## The whole script

`steps/01_record.py` is the entire lesson. It is 35 lines; read it first.

```python title="steps/01_record.py"
--8<-- "steps/01_record.py"
```

Run it:

```bash
python steps/01_record.py myvisit.wav
```

Talk for twenty seconds. Role-play both sides if you like. Press Enter.

## What the lines mean

**`RATE = 16000`.** Speech models are trained on 16,000 samples per second. CD audio is 44,100. Higher does not help the model and triples the file size. One channel (mono) for the same reason: the model does not use stereo.

**The queue.** The sound card delivers audio in small blocks on its own thread, dozens of times a second. If you write to disk inside that callback and the disk hiccups, you drop audio. So the callback only drops the block in a queue, and the main loop writes. This pattern, "capture thread hands off to worker", shows up again in every real-time system.

**`PCM_16`.** Sixteen-bit integers, the plain uncompressed WAV format. A 15-minute visit is about 29 MB. Fine on disk, and it means the transcriber never has to decode anything.

## Microphones matter more than code

The single biggest quality lever in this whole pipeline is the microphone and where it sits. In order of impact:

1. **Distance.** A USB conference mic on the desk between you and the patient beats a laptop mic by a wide margin. Under a metre to each speaker is the goal.
2. **Room.** Hard floors and bare walls echo. A rug and a curtain are real improvements.
3. **Gain.** Too quiet is recoverable; clipped is not. The browser recorder in Lesson 6 turns on automatic gain control; this script does not.

List what the system sees:

```bash
scribe mics
```

Pick one by index or name:

```bash
SCRIBE_MIC=1 scribe record myvisit.wav
```

## The package version

`scribe record` in `scribe/audio.py` is the same loop with a device option, a time limit option, and a `load()` helper that turns any audio file (WAV, MP3, the browser's WebM) into the float array the transcriber wants. It uses faster-whisper's bundled decoder, so you do not need `ffmpeg` installed.

```bash
scribe record myvisit.wav --seconds 30
```

## Try

- Record the same sentence from across the room and up close. Transcribe both in the next lesson. The difference is your argument for buying a mic.
- Open the WAV in Audacity or any editor and look at the waveform. Flat tops are clipping.

!!! note "Safety"
    You have just created PHI if anyone real was recorded. Even in practice, treat test recordings as if they were: keep them in the project folder, which `scribe purge` cleans, not in Downloads.

Next: [Lesson 3 · Transcribe](03-transcribe.md).
