# Cleaned transcript

You are given a raw, timestamped speech-to-text transcript of a two-person clinic visit (a clinician and a patient).
Produce a cleaned transcript that is easier to read.

Rules:
- Keep every piece of medical content exactly as spoken. Do not summarize, reorder, or omit anything substantive.
- Remove filler words (um, uh, you know), false starts, and stutters.
- Fix obvious speech-to-text errors in common words only when the intended word is unambiguous. Leave medical terms as-is unless certain, marking doubts with [unclear].
- Label speakers as "Clinician:" and "Patient:" based on context. If you cannot tell, use "Speaker:".
- Drop the timestamps. Start a new line for each speaker turn.
- Output only the cleaned transcript. No preamble.
