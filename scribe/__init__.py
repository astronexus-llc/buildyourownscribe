"""buildyourscribe: a small, local-first medical ambient scribe you build yourself.

The pipeline is four steps, each its own module:

    audio      -> record or load a visit as 16 kHz mono audio
    transcribe -> turn audio into a timestamped transcript (Whisper or Vosk)
    notes      -> ask a local language model to draft a note from the transcript
    storage    -> keep sessions on disk, log what happened, delete on schedule

``pipeline`` chains them. ``cli`` and ``server`` are the two front doors.
"""

__version__ = "0.1.0"
