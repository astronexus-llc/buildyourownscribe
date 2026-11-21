# All open source, no cloud

*Fifteen minutes to read, ten to check.* At the end you know what every part of the scribe is, what licence it carries, when it touches the internet, and how to prove to yourself that a visit never leaves the machine.

The scribe in this course needs no cloud model, no account, and no subscription. Every part that hears, transcribes, drafts, or stores a visit runs on the computer in front of you. After setup you can unplug the network and it still works.

## The whole stack

| Job | What does it | Licence |
|---|---|---|
| Record from the microphone | `sounddevice` on PortAudio | MIT |
| Read audio files | PyAV, which bundles FFmpeg | BSD for PyAV; FFmpeg and its codecs are LGPL and GPL |
| Skip silence | Silero VAD model inside faster-whisper, run by `onnxruntime` | MIT |
| Speech to text | `faster-whisper` on CTranslate2, with OpenAI's Whisper weights | MIT, all three |
| Speech to text, low power | Vosk with a Kaldi model | Apache 2.0 |
| Draft the note | Qwen3 weights | Apache 2.0 |
| Serve the model | Ollama, llama.cpp, or vLLM | MIT, MIT, Apache 2.0 |
| Talk to the model | `httpx` | BSD |
| Review app | FastAPI and Uvicorn, plus one HTML page in this repo | MIT, BSD |
| Store sessions and the audit log | Plain files, Python standard library | PSF |
| This course site | MkDocs with the Material theme | BSD, MIT |
| The scribe itself | About 1,200 lines of Python in `scribe/` | MIT |

Do not take the table on trust. Ask your own installation:

```bash
python - <<'PY'
from importlib.metadata import metadata
for name in ("faster-whisper", "ctranslate2", "onnxruntime", "fastapi", "uvicorn", "httpx", "sounddevice", "av"):
    m = metadata(name)
    print(f"{name:16} {m['Version']:9} {m.get('License-Expression') or m.get('License')}")
PY
ollama show qwen3:8b        # prints the model's licence at the bottom
```

## What is not open source

Three things in or near this stack are free to use but are not open source. You should know which.

**NVIDIA's driver and CUDA libraries.** The `cuda` extra installs `nvidia-cublas-cu12` and `nvidia-cudnn-cu12`. Their licence is NVIDIA's own and the source is closed. They run on your machine. To avoid them, install without the extra (`uv pip install -e .`) and run on the CPU. Everything then is open source, and slower. On a Mac the equivalent closed part is macOS itself.

**LM Studio.** It serves models well and the scribe works with it, but the application is closed source. For an all-open setup use Ollama or llama.cpp.

**Some model weights.** "Open weights" means you can download the model and run it yourself. It does not always mean an open source licence. Qwen3 is Apache 2.0, which is why this course uses it. Meta's Llama models and Google's Gemma models come under their own licences with conditions on use. They run locally just the same, so privacy is not affected, but read the licence before you build a service on one.

!!! warning "A model named `cloud` is not local"
    Ollama can also run models on Ollama's own servers. Their tags end in `cloud`, for example `kimi-k2.6:cloud`. You still talk to `localhost`, so the scribe's locality guard cannot tell the difference, and the transcript leaves your machine. Never use one for a visit. `ollama list` shows what you have. Ollama 0.40 also has a setting named `OLLAMA_NO_CLOUD` to switch the feature off; we did not test it.

## The three times the scribe uses the internet

All three happen during setup, before any patient is in the room.

1. **Installing the Python packages** from PyPI.
2. **Downloading the Whisper model** from huggingface.co, once. `small.en` is about 460 MB.
3. **Downloading the language model** from Ollama's library, once. `qwen3:8b` is about 5 GB.

After that the scribe needs nothing from outside.

## What we found when we watched the wire

We did not assume. On our test machine (Linux, 21 November 2026) we recorded every network connection the scribe attempted while transcribing the sample visit on the CPU. Two libraries called out on their own.

**`onnxruntime` reports usage to Microsoft.** Version 1.31 opened two connections to `mobile.events.data.microsoft.com` on every run. The traffic is encrypted, so we could not read it. It is the library's usage reporting and has nothing to do with transcription. A scribe should not make the call at all. Setting `ORT_DISABLE_TELEMETRY=1` stopped it, and `scribe/transcribe.py` now sets that before the library loads. So does the Lesson 3 script.

**`faster-whisper` checks huggingface.co on every start.** Even with the model already on disk, it asked whether a newer copy existed: five connections per run. The scribe now looks on disk first and goes to the network only for the first download. The Lesson 3 script is kept short and does not do this, so run it with `HF_HUB_OFFLINE=1` once the model is downloaded.

After both fixes, on the same machine:

| What we ran | Outside connections |
|---|---|
| `scribe transcribe`, Whisper | 0 |
| `scribe transcribe`, Vosk | 0 |
| `scribe transcribe` in a sandbox with no network at all | Worked |

The drafting step makes one connection, to the model server address you set. By default that is `127.0.0.1`, your own machine.

!!! note "What we did not measure"
    The model server is a separate program. We did not record what Ollama, llama.cpp, or vLLM do on their own, such as checking for updates. We also measured on the CPU, so NVIDIA's libraries were not loaded. The test below covers them too, because it takes the network away from the whole machine. Library versions change, so repeat the check after an update.

## Prove it yourself

**The simple test.** Finish Lesson 1. Turn off Wi-Fi and unplug the cable. Then:

```bash
scribe run samples/visit-01.wav
```

If a note comes out, nothing in the path needs the internet.

**The stricter test, on Linux.** List every connection the scribe attempts:

```bash
strace -f -qq -e trace=connect -o connections.log scribe run samples/visit-01.wav
grep AF_INET connections.log | grep -v '127\.0\.0\.1'
```

No output means no connection to anywhere but your own machine. `strace` is in every Linux distribution's package list. On a Mac, Little Snitch or LuLu show the same thing in a window.

## A machine that never goes online

For a computer that stays disconnected for good, do the three downloads on another machine and carry them over.

- **Whisper.** Copy the model folder and point the scribe at it. `SCRIBE_WHISPER_MODEL` accepts a folder as well as a name:

    ```bash
    export SCRIBE_WHISPER_MODEL=/models/faster-whisper-small.en
    ```

    The folder is the one holding `model.bin`, under `~/.cache/huggingface/hub/models--Systran--faster-whisper-small.en/snapshots/`. We tested this with the network removed.

- **Vosk.** Already a folder you download and unpack into `models/`.
- **The language model.** llama.cpp is the easiest here: one GGUF file on a USB stick, then `llama-server -m model.gguf`.
- **The Python packages.** `pip download` on the connected machine and `pip install --no-index --find-links` on the other. We did not test this step.

## If the hardware is not enough

A small model on a laptop CPU is slow, and a clinic may not want a GPU in every room. There are two honest ways out.

- **One model server on your own network.** A single machine with a GPU can serve every room. The scribe's guard allows private addresses, so `SCRIBE_LLM_BASE_URL=http://192.168.1.20:11434/v1` is accepted once that server is set to listen on the network. No outside company is involved. This is still a network, so read Lesson 7 first.
- **A cloud model under a contract.** Possible, and it has rules. See [Cloud models and PHI](cloud-phi.md).
