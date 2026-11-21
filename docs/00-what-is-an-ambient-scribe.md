# Lesson 0 · What an ambient scribe is

*Reading only. Twenty minutes.*

## The problem it solves

A clinician spends a large share of every visit typing. An ambient scribe records the conversation, turns it into text, and drafts the note in the clinic's format. The clinician reads, fixes, and signs. The typing is replaced by editing, which is faster and keeps eyes on the patient.

## The anatomy

Every ambient scribe, homemade or commercial, is the same pipeline:

| Stage | What happens | The open-source part we use |
|---|---|---|
| 1. Capture | Record the visit as audio | Your microphone, `sounddevice`, or the browser's recorder |
| 2. Speech to text | Audio becomes a timestamped transcript | **Whisper** via `faster-whisper` (or Vosk on weak hardware) |
| 3. Drafting | A language model reads the transcript and writes the note | A **local LLM** served by Ollama, llama.cpp, vLLM or LM Studio |
| 4. Review and sign | The clinician edits and attests | A small local web page |
| 5. Storage | Keep what must be kept, delete the rest on schedule | Folders on an encrypted disk plus an audit log |

Vendors add polish, EHR integration, support, and a monthly fee. The model quality underneath is the same open models, or close.

## Why build your own

- **You know where the audio goes.** It stays on a machine you own. No business associate agreement to read, no vendor breach to worry about.
- **You can change the note format in a text file.** The prompt *is* the product. Your specialty's template takes an evening, not a feature request.
- **You learn what the thing is doing**, which is the only way to judge when it is wrong.
- **It costs hardware you may already have.**

And honestly: because it is a satisfying thing to build.

## Why not

- It is not certified software. You are responsible for every note you sign, as you already are.
- Maintenance is yours: updating models, backups, the day the GPU driver breaks. Lesson 10 covers what that looks like.
- Multi-clinician, multi-site, or anything exposed to the internet changes the risk picture entirely. That is where you get a professional; see the boundaries below.

## Safety and legal footing, plainly

!!! warning "Not legal advice"
    These are the questions to ask, not the answers. Rules differ by country, state, and employer. Your clinic's compliance officer or a health lawyer gives the answers.

**Consent to record.** Some jurisdictions require every party to consent to a recording; others require one. Get consent from the patient every time regardless. Say it out loud, note it, and offer to turn it off. A sign in the room is not consent.

**Protected health information (PHI).** The audio, the transcript, and the note are all PHI. On a single machine you control, with full-disk encryption, a screen lock, and a deletion schedule, you are in roughly the same position as a laptop with a Word document on it. The moment any of it travels to a server you do not own, you need a contract (in the US, a BAA) with whoever runs that server. This course's code refuses to do that by default. [All open source, no cloud](open-source.md) shows how to check that for yourself, and [Cloud models and PHI](cloud-phi.md) covers the services that will sign such a contract.

**The draft is not a note.** The model will occasionally invent a finding, miss a negative, or mishear a drug name. Lesson 8 shows you real examples from our own sample. Review is not a formality.

**Retention.** Decide before the first real visit: when is audio deleted, how long are unsigned drafts kept, where do signed notes go. Write it down. The defaults here are: audio deleted at signing, unsigned sessions purged after seven days, signed notes kept until you move them to your record system.

## Where DIY stops

Do it yourself: a scribe on one machine, used by you, inside your clinic's walls, with consent and encryption.

Get a professional for: anything on a network other than localhost, more than one user, storing signed notes long term, connecting to an EHR, cloud models of any kind (start with [Cloud models and PHI](cloud-phi.md), then ask), or any question that starts with "is it legal to".

## Hardware tiers

| Tier | Example | Transcribe a 15 min visit | Draft a note | Verdict |
|---|---|---|---|---|
| Desktop GPU, 12 GB+ VRAM | RTX 3060 to 5090 | 10 to 40 s with `medium.en` | 5 to 30 s with an 8B model | Ideal |
| Apple Silicon, 16 GB+ | M1 Pro and up | 1 to 2 min with `small.en` | 20 to 60 s | Very good |
| Laptop, CPU only, 16 GB RAM | Any recent x86 | 3 to 6 min with `base.en` | 1 to 3 min with a 4B model | Works, plan a coffee |
| Older laptop, 8 GB | | Use Vosk, near real time | A 1 to 3B model, slow | Dictation yes, ambient barely |

Numbers are rough. The reference page on [choosing models](reference/models.md) has details.

Next: [Lesson 1 · Set up your workbench](01-setup.md).
