"""Lesson 3 - turn an audio file into a timestamped transcript.

    python steps/02_transcribe.py samples/visit-01.wav [model]

model defaults to small.en. Try base.en if slow, medium.en for better medical vocabulary.
"""
import sys
import time

from faster_whisper import WhisperModel

audio = sys.argv[1]
model_name = sys.argv[2] if len(sys.argv) > 2 else "small.en"

# Use the GPU if there is one, otherwise CPU with 8-bit weights (slower, same words).
try:
    import ctranslate2
    device, compute = ("cuda", "float16") if ctranslate2.get_cuda_device_count() else ("cpu", "int8")
except Exception:
    device, compute = "cpu", "int8"

t0 = time.time()
model = WhisperModel(model_name, device=device, compute_type=compute)
print(f"loaded {model_name} on {device} in {time.time() - t0:.1f}s", file=sys.stderr)

t0 = time.time()
segments, info = model.transcribe(
    audio,
    language="en",
    beam_size=5,
    vad_filter=True,                   # skip silence: faster and fewer hallucinated words in gaps
    condition_on_previous_text=False,  # avoids the "repeats the same sentence forever" failure
)
for s in segments:                      # segments is a generator; work happens as you iterate
    m, sec = divmod(int(s.start), 60)
    print(f"[{m:02d}:{sec:02d}] {s.text.strip()}")
print(f"done in {time.time() - t0:.1f}s", file=sys.stderr)
