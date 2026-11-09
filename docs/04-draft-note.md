# Lesson 4 · Draft the note

*One hour.* At the end a local model turns your transcript into a SOAP note, and you understand the prompt well enough to change it.

## The whole script

```python title="steps/03_draft_note.py"
--8<-- "steps/03_draft_note.py"
```

Save the transcript from Lesson 3 as text, then:

```bash
scribe transcribe samples/visit-01.wav > transcript.txt
python steps/03_draft_note.py transcript.txt
```

With `qwen3:8b` you get something close to:

```markdown
## Subjective
Chief complaint: Persistent dry cough for approximately three weeks.
History of Present Illness: Patient reports a dry cough that worsens at night when lying down.
Denies fever, chills, shortness of breath, runny nose, or post-nasal drip. Reports occasional
heartburn (once or twice weekly). No recent sick contacts. Quit smoking 12 years ago.
Medications and Adherence:
- Lisinopril 10 mg daily: Adherent, no missed doses.
- Metformin 500 mg with breakfast and dinner: Adherent, no stomach upset.
Home Monitoring: Fasting blood sugars typically 120–140 mg/dL.

## Objective
Vitals: Blood pressure 128/82 mmHg. Weight loss of 3 lbs since July.
Physical Exam: Lungs clear, no wheezing, no crackles. Heart regular rhythm. No ankle swelling.

## Assessment
1. ACE inhibitor-induced cough (likely secondary to lisinopril).
2. Hypertension (controlled).
3. Type 2 Diabetes Mellitus (controlled).

## Plan
1. Discontinue lisinopril. Start losartan 50 mg once daily. Continue metformin 500 mg BID.
2. Order A1C and basic metabolic panel today. Potassium and kidney function in two weeks.
3. Return in three months. Call sooner if cough persists past four weeks, or fever,
   shortness of breath, or hemoptysis develops.
```

## What just happened

You sent two messages to a model running on your own machine: a **system message** (the instructions, which we call the template) and a **user message** (the transcript). It replied with text. That is the entire interface. There is no SDK, no account, no magic; one HTTP POST, which is why the same code talks to Ollama, llama.cpp, vLLM, LM Studio, and the hosted providers.

## The template is the product

Read the system prompt in the script again. Every line is there because of a failure it prevents:

| Line | The failure it prevents |
|---|---|
| "for a licensed clinician to review and sign" | Sets the register. Models write differently for a doctor than for a patient. |
| "use only information in the transcript" | Hallucinated findings. The single most important sentence. |
| "Never add vitals, exam findings, labs..." | Models love to write "Vitals: WNL" when nothing was measured. |
| "write Not discussed." | Without an explicit escape hatch, the model fills empty sections with plausible fiction. |
| "Mark doubtful words [unclear]" | Gives the model permission to flag speech-to-text errors rather than smooth them over. |
| "No preamble, no disclaimers" | Otherwise every note begins "Here is the SOAP note based on..." |
| "no patient name" | One less piece of PHI in the note body. |

The package keeps templates as plain Markdown in `scribe/templates/`. Open `soap.md`; it is the script's prompt with more structure. You edit it with a text editor, not Python. Lesson 9 is about writing your own.

## The two settings that matter

**`temperature: 0.2`.** Temperature is how much randomness the model adds when picking each word. At 0.8 it is creative; at 0 it is deterministic. A scribe should be boring. 0.1 to 0.3.

**Thinking off.** Newer models (Qwen3, DeepSeek-R1 and others) "think" in a hidden monologue before answering. That doubles or triples the time for no gain on a scribe task; the transcript is right there. The two extra fields in the request body turn it off for vLLM, llama.cpp (`chat_template_kwargs`) and Ollama (`think`). The package also strips any `<think>` block that leaks through, and retries without the extra fields if a server rejects them.

## The locality guard

`scribe/notes.py` adds one thing the script does not: before the first request, it checks that the server address is localhost or a private network range. If not, it raises an error that mentions the BAA you would need. You can override it with `SCRIBE_ALLOW_REMOTE_LLM=1`. The point is that sending PHI off-machine should require typing something deliberate.

## Try

- Change `temperature` to 1.0 and run three times. Watch the note change between runs. Change it back.
- Delete the "Not discussed." line from the prompt and run on a transcript with no exam. See what the Objective section does.
- Run with a 4B model, then an 8B. The smaller one is more likely to add things.

```bash
scribe note transcript.txt --template progress
scribe note transcript.txt --template after-visit-summary
```

Next: [Lesson 5 · Assemble the pipeline](05-pipeline.md).
