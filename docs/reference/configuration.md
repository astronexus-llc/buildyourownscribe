# Configuration

Everything is an environment variable prefixed `SCRIBE_`, read once at start by `scribe/config.py`. Put them in your shell profile or a file you `source` before `scribe serve`.

## Speech to text

| Variable | Default | Notes |
|---|---|---|
| `SCRIBE_STT_BACKEND` | `whisper` | `whisper` or `vosk` |
| `SCRIBE_WHISPER_MODEL` | `small.en` | `tiny.en` `base.en` `small.en` `medium.en` `large-v3`, or a path to a CTranslate2 model folder |
| `SCRIBE_STT_DEVICE` | `auto` | `auto` picks `cuda` if available, else `cpu` |
| `SCRIBE_STT_COMPUTE` | `auto` | `float16` on GPU, `int8` on CPU. `int8_float16` saves VRAM |
| `SCRIBE_STT_LANGUAGE` | `en` | Empty string for auto-detect (multilingual models only) |
| `SCRIBE_STT_BEAM` | `5` | Beam size; 1 is faster and slightly worse |
| `SCRIBE_VOSK_MODEL` | `models/vosk-model-small-en-us-0.15` | Folder of an extracted Vosk model |

## Language model

| Variable | Default | Notes |
|---|---|---|
| `SCRIBE_LLM_BASE_URL` | `http://localhost:11434/v1` | Ollama. vLLM is usually `:8000/v1`, llama.cpp `:8080/v1`, LM Studio `:1234/v1` |
| `SCRIBE_LLM_MODEL` | empty | Empty uses the first model the server lists |
| `SCRIBE_LLM_API_KEY` | `not-needed` | Local servers ignore it |
| `SCRIBE_LLM_TEMPERATURE` | `0.2` | Keep low |
| `SCRIBE_LLM_MAX_TOKENS` | `2048` | Enough for most notes. A note that hits the cap is flagged as cut off |
| `SCRIBE_LLM_TIMEOUT` | `300` | Seconds. CPU inference can be slow |
| `SCRIBE_LLM_THINKING` | `off` | `on` lets reasoning models think; slower, rarely better for this task |
| `SCRIBE_ALLOW_REMOTE_LLM` | unset | Set to `1` to permit a non-private address. Read Lesson 7 first |

## Storage

| Variable | Default | Notes |
|---|---|---|
| `SCRIBE_DATA_DIR` | `scribe_data` | Relative to the working directory |
| `SCRIBE_RETENTION_DAYS` | `7` | Unsigned sessions older than this are removed when the review app starts, hourly while it runs, and by `scribe purge` |
| `SCRIBE_DELETE_AUDIO_ON_SIGN` | `1` | Set `0` to keep audio after signing |

## Audio and server

| Variable | Default | Notes |
|---|---|---|
| `SCRIBE_MIC` | system default | Device index or name from `scribe mics` |
| `SCRIBE_HOST` | `127.0.0.1` | Do not change without reading Lesson 7 |
| `SCRIBE_PORT` | `8765` | |
| `SCRIBE_ALLOWED_HOSTS` | empty | Extra names the review app answers to, comma separated. It always answers to `localhost`, `127.0.0.1` and `SCRIBE_HOST`. Only needed off localhost; Lesson 7 |

## Example profile

```bash
# ~/.config/scribe.env  ->  source ~/.config/scribe.env
export SCRIBE_WHISPER_MODEL=medium.en
export SCRIBE_LLM_BASE_URL=http://localhost:11434/v1
export SCRIBE_LLM_MODEL=qwen3:8b
export SCRIBE_DATA_DIR=$HOME/scribe_data
export SCRIBE_MIC="USB PnP Audio Device"
```
