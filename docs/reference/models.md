# Choosing models

Two models, two decisions. Both are "the biggest that fits comfortably".

!!! info "What this course was actually tested on"
    One machine with an RTX 5090. Whisper `small.en` through faster-whisper for speech. Two language model setups:

    - A 35B Qwen model (`Qwen3.6-35B-A3B`, 4-bit) served by vLLM. Every transcript and note quoted in the lessons came from this one. The Vosk comparison in Lesson 3 was run on the same machine. On 27 November 2026 we ran the whole pipeline again with `scribe run` and the review app: the 153-second sample visit went from audio to draft note in about 5 seconds, signing deleted the audio, and the only network connection made was to the local model. Recording from a live microphone was not part of that run.
    - The route we recommend for most readers: Ollama 0.40 with `qwen3:8b`, at its defaults. The lesson scripts, `scribe doctor`, `scribe run` and both draft warnings were run against it. The first note took 45 seconds while the model loaded. After that the sample visit took under 2 seconds and about 290 tokens. The model used 10 GB of graphics memory at Ollama's default window for that card.

    The other language models in the table below were not run. Their memory and quality notes, and the Whisper speed figures, are rough guides from published numbers, not our measurements. Nothing was run on a CPU-only or Mac setup.

## Speech to text (Whisper via faster-whisper)

| Model | Size | GPU VRAM (float16) | CPU RAM (int8) | Speed, RTX-class GPU | Speed, 8-core CPU | Accuracy |
|---|---|---|---|---|---|---|
| `tiny.en` | 75 MB | 0.5 GB | 0.5 GB | 100× real time | 10× | Dictation only |
| `base.en` | 140 MB | 1 GB | 0.7 GB | 70× | 5× | Dictation, simple visits |
| `small.en` | 480 MB | 2 GB | 1.2 GB | 40× | 1.5× | **Default.** Good medical vocab |
| `medium.en` | 1.5 GB | 5 GB | 3 GB | 15× | 0.5× | Very good |
| `large-v3` | 3 GB | 10 GB | 6 GB | 8× | 0.2× | Best; multilingual |
| `distil-large-v3` | 1.5 GB | 5 GB | 3 GB | 20× | 0.7× | Near large-v3 quality, English only |

"Speed" is how many seconds of audio are processed per second. 40× means a 15-minute visit in about 22 seconds. CPU figures are rough and depend heavily on the chip.

Rules of thumb:

- Desktop GPU with 8 GB or more: `medium.en`. 12 GB or more: `large-v3` if you want the last few percent.
- Apple Silicon: `small.en` on CPU is comfortable; `medium.en` if you can wait a minute per visit.
- CPU-only laptop: `base.en` or `small.en`. If a visit takes longer to transcribe than it took to happen, step down.
- Non-English or mixed language: a non-`.en` model (`small`, `medium`, `large-v3`) with `SCRIBE_STT_LANGUAGE` set or empty.

### Vosk

Vosk models are Kaldi models: tiny, CPU only, real time on anything, no punctuation. `vosk-model-small-en-us-0.15` (40 MB) for weak hardware; `vosk-model-en-us-0.22` (1.8 GB) is better but still well behind Whisper `small.en` on drug names. See the comparison in Lesson 3.

## Language model

The scribe does not care which model, only that a server speaks the OpenAI chat API. What matters is faithfulness to the transcript, and that tracks size and recency.

| Class | Examples (Ollama names) | Needs | Faithfulness on drafting |
|---|---|---|---|
| 3 to 4B | `qwen3:4b`, `llama3.2:3b`, `gemma3:4b` | 4 GB VRAM or CPU with 8 GB RAM | Usable. Watch for invented normals and dropped list items |
| 7 to 9B | `qwen3:8b`, `llama3.1:8b`, `gemma3:12b` | 8 GB VRAM or 16 GB RAM on CPU (slow) | **Recommended start.** Reliably follows the rules block |
| 14 to 32B | `qwen3:14b`, `qwen3:32b`, `gemma3:27b` | 12 to 24 GB VRAM | Noticeably better at long lists and negations |
| Mixture of experts, 30B+ | `qwen3:30b-a3b` | 20 GB+ VRAM, fast once loaded | Large-model quality at small-model speed; the closest Ollama equivalent to what this course was tested with |

Quantisation: Ollama's defaults (Q4_K_M) are fine. Below 4-bit, faithfulness degrades fast.

Reasoning models work, and that includes `qwen3`, which thinks by default. Leave `SCRIBE_LLM_THINKING=off` (the default) or the model spends more than half its reply on a monologue you never see.

### Servers

| Server | Base URL | Notes |
|---|---|---|
| Ollama | `http://localhost:11434/v1` | Easiest. `ollama pull`, done |
| llama.cpp `llama-server` | `http://localhost:8080/v1` | Fastest on CPU and Mac; you manage GGUF files |
| vLLM | `http://localhost:8000/v1` | Fastest on NVIDIA for concurrent use; heavier install |
| LM Studio | `http://localhost:1234/v1` | GUI, good for browsing models. Closed source, unlike the other three |

All four accept the same request the scribe sends. Change the URL and nothing else.

Licences differ between models. Qwen3 is Apache 2.0; Llama and Gemma carry their own terms. [All open source, no cloud](../open-source.md) has the full list. Avoid any Ollama tag ending in `cloud`: those run on Ollama's servers, not yours.

## Re-test after any change

Model choice is an experiment. Run your Lesson 8 test set after every change and keep the tally.
