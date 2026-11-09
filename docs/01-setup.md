# Lesson 1 · Set up your workbench

*Forty-five minutes, most of it downloads.*

At the end you can run `scribe doctor` and see every line say OK.

## 1. Python and uv

You need Python 3.10 or newer. Check:

```bash
python3 --version
```

Install [uv](https://docs.astral.sh/uv/), a fast Python package manager. It also installs Python for you if yours is too old.

=== "Linux / macOS"
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"
    Use WSL2 (Ubuntu) and follow the Linux steps. Native Windows works for the Python parts but GPU setup is harder; WSL2 is the path of least pain.

## 2. Get the code

```bash
git clone https://github.com/frasod/buildyourscribe
cd buildyourscribe
uv venv
source .venv/bin/activate
```

Everything from here on assumes you are inside this folder with the environment activated. Your prompt shows `(.venv)` when it is.

## 3. Install the scribe

=== "NVIDIA GPU"
    ```bash
    uv pip install -e ".[cuda]"
    ```
    The `cuda` extra installs the CUDA math libraries through pip, so you do not need the CUDA toolkit. You do need a recent NVIDIA driver (`nvidia-smi` should work).

=== "Mac or CPU only"
    ```bash
    uv pip install -e .
    ```

=== "Also want Vosk"
    ```bash
    uv pip install -e ".[vosk]"
    ```
    Then download a model from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) into `models/`. Vosk is covered as the low-power alternative in Lesson 3.

`-e` means editable: when you change a file in `scribe/`, the command picks it up immediately. You will be changing files.

## 4. A local language model server

The scribe talks to any server that speaks the OpenAI chat API. The easiest is Ollama.

```bash
curl -fsSL https://ollama.com/install.sh | sh     # Linux; Mac: download from ollama.com
ollama serve &                                    # usually starts itself as a service
ollama pull qwen3:8b                              # about 5 GB
```

Other servers that work unchanged, if you already have one: llama.cpp `llama-server`, vLLM, LM Studio. Point the scribe at them with `SCRIBE_LLM_BASE_URL`; see [configuration](reference/configuration.md).

!!! tip "Which model"
    An 8B-parameter model at 4-bit quantization (`qwen3:8b`, `llama3.1:8b`) is the sweet spot for drafting on a 12 GB GPU or 16 GB Mac. On CPU, start with `qwen3:4b`. Bigger is better for faithfulness; the [models reference](reference/models.md) compares them.

## 5. Check everything

```bash
scribe doctor
```

You should see something like:

```
buildyourscribe 0.1.0
python          3.12.3
microphones     2 found
                  1  USB PnP Audio Device  (1 in)
                  5  default  (128 in)
gpu (cuda)      yes
stt             whisper model=small.en
llm             ok  http://localhost:11434/v1 (qwen3:8b)
data dir        /home/you/buildyourscribe/scribe_data  retention=7d  delete_audio_on_sign=True
```

Each line that is wrong points at the fix:

- **microphones 0 found**: plug one in, or on Linux install PortAudio (`sudo apt install libportaudio2`).
- **gpu (cuda) no** on a machine with an NVIDIA card: run `nvidia-smi`. If that fails, it is a driver problem, not a scribe problem. CPU still works meanwhile.
- **llm NOT REACHABLE**: the server is not running or is on a different port. `curl http://localhost:11434/v1/models` should return JSON.

## 6. Run the whole thing once

Before building it piece by piece, see the finished result on the synthetic sample visit:

```bash
scribe run samples/visit-01.wav --label "first run"
```

The first run downloads the Whisper model (about 500 MB for `small.en`). Then you get a timestamped transcript and a SOAP note printed to the terminal, and a session folder in `scribe_data/sessions/`.

Read the note. Compare it to `samples/visit-01.script.txt`. That gap, between what was said and what was written, is what the rest of the course is about.

Next: [Lesson 2 · Record a visit](02-record.md).
