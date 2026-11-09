# Lesson 8 · Evaluate it

*Two hours.* At the end you have caught the scribe being wrong, built a test set, and have a habit.

## Three real errors from our own sample

The synthetic visit in `samples/` was transcribed with Whisper `small.en` and drafted with the 35B Qwen model on our test machine. Both did well. Both also did this:

**1. The speech-to-text error that changed a meaning.** The clinician said: *"or if you develop fever, shortness of breath, or you start coughing up anything, call us sooner."* Whisper wrote:

```
[02:14] If the cough is not improving in four weeks, or if you develop fever, shortness of breath,
[02:20] Before you start coughing up anything, call us sooner.
```

"or you" became "Before you". A reader of the raw transcript might conclude the patient was told to call before coughing anything up. The language model, with the whole context, wrote *"call sooner if fever, shortness of breath, or hemoptysis develops"* in one run and *"or begins producing sputum"* in another. Both recover the meaning. Both are also the model's words, not the clinician's, who said "coughing up anything". It got it right this time.

**2. The paraphrase that added a claim.** For the after-visit summary the clinician said *"repeat your A1C and a basic metabolic panel today."* The model wrote *"We checked your blood sugar, A1C, and kidney function today."* A basic metabolic panel does include glucose and creatinine, so a clinician would accept it. But the model stated a fact about what a panel contains that was not in the transcript. On a different test it will fill a gap with something false in exactly the same tone.

**3. The small word swap.** *"Is it dry, or are you bringing anything up?"* became *"printing anything up"*. Harmless here because the patient answered "it's dry". Not harmless if the question had been about blood.

None of these would be caught by someone skimming a tidy-looking note. All of them are caught by reading the note against the transcript. That is the whole method.

## The method: claim by claim

For each sentence in the draft, ask three questions:

1. **Was it said?** Find it in the transcript. If you cannot, it is invented. Delete it.
2. **Was it said *that way*?** Dose, frequency, laterality, negation, who said it. "Denies chest pain" when the clinician asked and the patient said "a little" is an inversion.
3. **Is anything missing?** Read the transcript once more looking for things the note skipped. Models drop the second half of long lists. Check the first minutes of the visit in particular: a model server with too small a context window loses those first ([Lesson 4](04-draft-note.md#two-failures-that-give-no-error)).

The `transcript-cleanup` template helps with step 1: it produces a speaker-labelled, filler-free transcript that is faster to scan than the timestamped raw one.

```bash
scribe note scribe_data/sessions/<id>/transcript.json --template transcript-cleanup
```

## Build a test set

A test set is five to ten recordings you know the truth of. Role-play them with a colleague or a family member reading a script; no real patients. Cover:

- a follow-up with a medication change (dose and frequency to get right)
- a visit with a negative exam (does the note say "not discussed" or invent normals?)
- a visit with a long list, such as eight medications (does it keep all eight?)
- a visit with a drug name that sounds like another (the lisinopril problem)
- a visit where the patient contradicts themselves
- a visit in your specialty's vocabulary
- one visit as long as your longest real one, with a distinctive fact in the first minute (does the note still have it?)

Save each with its script in a folder. Run them all:

```bash
for f in testset/*.wav; do scribe run "$f" --label "test $(basename $f)"; done
```

Read each note against its script with the three questions. Keep a tally. Then re-run the set whenever anything changes: a bigger Whisper model, a different LLM, a template edit, a model update. Your tally tells you whether the change helped.

## Make your own synthetic visit

The sample was made with [Piper](https://github.com/OHF-Voice/piper1-gpl), a small offline text-to-speech engine, using two voices for the two speakers. Write a script with `CLINICIAN:` and `PATIENT:` lines, then:

```bash
uv pip install piper-tts soundfile
python -m piper.download_voices en_US-lessac-medium en_US-ryan-medium
```

```python
import numpy as np, soundfile as sf
from piper import PiperVoice
voices = {"CLINICIAN": PiperVoice.load("en_US-lessac-medium.onnx"),
          "PATIENT": PiperVoice.load("en_US-ryan-medium.onnx")}
out, sr = [], None
for line in open("script.txt"):
    if ":" not in line: continue
    who, text = line.split(":", 1)
    for chunk in voices[who.strip()].synthesize(text.strip()):
        sr = chunk.sample_rate
        out.append(np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16))
    out.append(np.zeros(int(sr * 0.7), dtype=np.int16))   # a pause between turns
sf.write("visit.wav", np.concatenate(out), sr)
```

Synthetic speech is cleaner than a real room, so it tests the drafting more than the listening. Record the same script yourself for the harder version.

## What good looks like

A reasonable target on clean audio, to be checked against your own test set rather than taken from us: zero invented findings, fewer than one meaningful omission per visit, and a handful of wording fixes. If you see invented findings, first suspect the template (is "use only information in the transcript" still there?), then the model size, then the audio quality.

## Try

- Feed the scribe thirty seconds of silence, or a recording of the radio. What does the note say? It should be mostly "Not discussed." If it is a confident SOAP note, your template has a hole.
- Give the same transcript to two different models and diff the notes.

Next: [Lesson 9 · Templates for your specialty](09-templates.md).
