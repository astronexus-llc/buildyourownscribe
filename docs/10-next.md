# Lesson 10 · Where to go next

You have a scribe. Here is what people build next, roughly in order of value for effort, and where each one crosses into professional territory.

## Worth doing

**A bigger Whisper.** If you have the VRAM, `medium.en` or `large-v3` is the cheapest accuracy you will ever buy. One environment variable.

**Whisper's word hints.** Pass your specialty's vocabulary as `initial_prompt` in `WhisperTranscriber.transcribe()`. Measurable improvement on drug and procedure names.

**Speaker labels.** Knowing who said what matters for "patient denies" versus "clinician asked". [pyannote.audio](https://github.com/pyannote/pyannote-audio) does speaker diarisation locally; it needs a Hugging Face account to download the model and a GPU to be pleasant. Merge its speaker turns with Whisper's segments by timestamp. Alternatively the `transcript-cleanup` template guesses speakers from context, which is surprisingly good for two-person visits and free.

**Live transcript.** Show words appearing while the visit happens. Chunk the audio every few seconds and transcribe each chunk; the old Vosk code this project grew out of did exactly that. Nice to see, not necessary for the note; the batch transcript after the visit is more accurate.

**A proper test harness.** Turn your Lesson 8 tally into a script: for each test recording, run the pipeline and check that specific strings (the dose, the follow-up interval) appear in the note. Run it before every change.

**Export.** A `scribe export <id>` that writes the signed note as a text file to wherever your records live. Ten lines.

## Worth knowing about

**Streaming the LLM.** Showing the note appearing word by word feels faster. It is the `stream: true` flag and reading server-sent events. Cosmetic.

**Structured output.** Asking the model for JSON (`{"subjective": ..., "plan": [...]}`) lets you render sections separately and validate that none are missing. Most local servers support a JSON mode. Trade: slightly stiffer prose.

**Fine-tuning Whisper on your audio.** Possible, documented, and usually not worth it: a bigger model plus word hints gets you most of the way without a training pipeline to maintain.

**Smaller hardware.** A Mac mini or a mini-PC with a 12 GB GPU in the consultation room, running everything, is a real and quiet deployment.

## Where to get a professional

Each of these is a reasonable next step and each is beyond this course:

- **Multiple users or a shared server.** Authentication, authorisation, HTTPS, central audit.
- **Connecting to your EHR.** FHIR, HL7, or a vendor API, plus the contract that allows it.
- **Any cloud component.** Even "just for the drafting". BAA, data processing agreement, and a risk assessment. [Cloud models and PHI](cloud-phi.md) tells you which vendors offer the contract, so you arrive at that conversation prepared.
- **Long-term storage of signed notes.** Retention law, backup verification, access controls.
- **A formal risk assessment** before use in a regulated setting, which may be required by your employer regardless of how local the system is.

## Keeping it alive

A working scribe needs about an hour a month:

- Update the scribe and its dependencies; run `pytest`.
- Update the operating system and the GPU driver.
- Pull the latest model if you want it; re-run the test set afterwards.
- Check that old drafts are being purged (`grep purged scribe_data/audit.log`).
- Restore one note from backup to prove the backup works.

When something breaks, the [troubleshooting reference](reference/troubleshooting.md) covers the usual suspects, and `scribe doctor` is always the first command.

## Contribute

The course and code are MIT licensed at [github.com/frasod/buildyourownscribe](https://github.com/frasod/buildyourownscribe). The most useful contributions are a template for a specialty not covered, a synthetic test visit with a tricky feature, or a correction where the text is wrong. Open an issue or a pull request.
