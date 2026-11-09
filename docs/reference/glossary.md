# Glossary

**Ambient scribe.** Software that records a clinical visit and drafts the documentation from the conversation, as opposed to dictation, where the clinician speaks the note.

**ASR / STT.** Automatic speech recognition, speech to text. Whisper and Vosk are ASR engines.

**BAA.** Business associate agreement. In the US, the contract required before a vendor may handle PHI on a covered entity's behalf. The scribe's locality guard exists because of this.

**Beam size.** How many candidate transcriptions Whisper keeps while decoding. More is more accurate and slower.

**CTranslate2.** The inference engine faster-whisper runs on. Handles the GPU and quantisation.

**Diarisation.** Working out who spoke when. Whisper does not do it; pyannote does.

**Hallucination.** The model producing fluent text with no basis in the input. In transcription: words in silence. In drafting: findings not in the transcript.

**LLM.** Large language model. The part that reads the transcript and writes the note.

**Local-first.** Designed so everything runs on the machine in front of you and nothing requires a network.

**OpenAI-compatible API.** The HTTP request format OpenAI introduced and nearly every model server now accepts. Why one client talks to Ollama, vLLM, llama.cpp and LM Studio.

**PHI / PII.** Protected health information; personally identifiable information. Audio, transcript and note are all PHI.

**Quantisation.** Storing model weights in fewer bits (4-bit, 8-bit) to use less memory and run faster at a small cost in quality.

**Reasoning / thinking model.** A model trained to write out a hidden chain of thought before answering. Good for puzzles, slow and unnecessary for drafting from a transcript.

**Retention.** How long each kind of data is kept before deletion. Decided before the first visit, enforced by `scribe purge`.

**Segment.** One chunk of a transcript with a start time, end time and text.

**Session.** One visit's folder: audio, transcript, note, metadata.

**SOAP.** Subjective, Objective, Assessment, Plan. The most common clinical note structure.

**System prompt / template.** The instructions sent to the language model before the transcript. In this project, a Markdown file.

**Temperature.** The randomness setting on a language model. Low is repeatable and literal; high is varied. A scribe wants low.

**VAD.** Voice activity detection. Finding the parts of audio that contain speech so the rest can be skipped.

**VRAM.** Memory on the graphics card. The limit on which models fit.

**Whisper.** OpenAI's open-weights speech recognition model family. The default ASR in this course.
