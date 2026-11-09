"""Step 1: get audio.

Two jobs only: record from a microphone to a WAV file, and load any audio file
as 16 kHz mono float32 (the shape every speech model wants).
"""

from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path

import numpy as np
import soundfile as sf

from .config import AudioConfig

SAMPLE_RATE = 16000


def list_microphones() -> list[str]:
    import sounddevice as sd

    lines = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            lines.append(f"{i:>3}  {d['name']}  ({d['max_input_channels']} in)")
    return lines


def record(out_path: Path, cfg: AudioConfig | None = None, stop_event: threading.Event | None = None,
           max_seconds: float | None = None) -> Path:
    """Record from the default (or configured) microphone until Enter is pressed.

    Writes 16-bit PCM WAV at 16 kHz mono. Returns the path written.
    """
    import sounddevice as sd

    cfg = cfg or AudioConfig()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    q: queue.Queue[np.ndarray] = queue.Queue()
    stop_event = stop_event or threading.Event()

    def on_audio(indata, frames, time_info, status):
        if status:
            print(f"[audio] {status}", file=sys.stderr)
        q.put(indata.copy())

    if max_seconds is None:
        threading.Thread(target=lambda: (input(), stop_event.set()), daemon=True).start()
        print("Recording... press Enter to stop.")

    frames_written = 0
    device = cfg.device
    if device is not None and str(device).isdigit():
        device = int(device)
    with sf.SoundFile(str(out_path), mode="w", samplerate=cfg.sample_rate, channels=cfg.channels, subtype="PCM_16") as f:
        with sd.InputStream(samplerate=cfg.sample_rate, channels=cfg.channels, dtype="int16",
                            device=device, callback=on_audio):
            while not stop_event.is_set():
                try:
                    block = q.get(timeout=0.2)
                except queue.Empty:
                    continue
                f.write(block)
                frames_written += len(block)
                if max_seconds is not None and frames_written >= max_seconds * cfg.sample_rate:
                    break
    print(f"Saved {frames_written / cfg.sample_rate:.1f}s to {out_path}")
    return out_path


def load(path: Path) -> np.ndarray:
    """Load any audio file (wav, webm, ogg, mp3, m4a...) as 16 kHz mono float32.

    Uses faster-whisper's decoder, which wraps FFmpeg via PyAV, so no system
    ffmpeg install is needed.
    """
    from faster_whisper.audio import decode_audio

    return decode_audio(str(path), sampling_rate=SAMPLE_RATE)


def save_wav(audio: np.ndarray, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, SAMPLE_RATE, subtype="PCM_16")
    return path


def duration_seconds(path: Path) -> float:
    with sf.SoundFile(str(path)) as f:
        return len(f) / f.samplerate
