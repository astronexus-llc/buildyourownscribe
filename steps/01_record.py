"""Lesson 2 - record a visit to a WAV file. No scribe package needed.

    python steps/01_record.py visit.wav

Speak, then press Enter to stop. Produces 16 kHz mono 16-bit PCM, which is
what every speech model wants.
"""
import queue
import sys
import threading

import sounddevice as sd
import soundfile as sf

RATE = 16000                      # samples per second. Speech models were trained on this rate.
out = sys.argv[1] if len(sys.argv) > 1 else "visit.wav"

q: "queue.Queue" = queue.Queue()  # the audio callback runs on a separate thread; hand blocks over safely
stop = threading.Event()


def on_audio(indata, frames, time_info, status):
    if status:
        print(status, file=sys.stderr)
    q.put(indata.copy())


threading.Thread(target=lambda: (input(), stop.set()), daemon=True).start()
print("Recording. Press Enter to stop.")

with sf.SoundFile(out, mode="w", samplerate=RATE, channels=1, subtype="PCM_16") as f:
    with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", callback=on_audio):
        while not stop.is_set():
            try:
                f.write(q.get(timeout=0.2))
            except queue.Empty:
                pass

print(f"Saved {out}")
