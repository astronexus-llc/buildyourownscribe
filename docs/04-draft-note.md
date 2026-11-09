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

Here is the note that came back on our test machine, which runs a 35B Qwen model under vLLM. A smaller model gives the same shape with rougher edges, and every run words things a little differently:

```markdown
## Subjective
The patient reports feeling mostly okay since the last visit in July. He notes that his blood pressure has been better. He presents with a dry cough lasting approximately three weeks that worsens at night when lying down. He denies fever, chills, shortness of breath, runny nose, or post-nasal drip. He reports occasional heartburn, occurring once or twice a week. He denies any sick contacts at home. He quit smoking 12 years ago.

The patient confirms adherence to lisinopril 10 mg daily, taken every morning without missed doses. He reports no stomach upset with metformin, which he takes with breakfast and dinner at 500 mg each time. He reports checking blood sugars most mornings, with fasting levels usually between 120 and 140 mg/dL.

## Objective
Physical examination reveals clear lungs with no wheezing or crackles. Heart sounds are regular. No swelling in the ankles. Blood pressure is 128/82 mmHg. The patient has lost 3 pounds since the last visit in July.

## Assessment
1. **Dry cough**: Likely an ACE inhibitor cough secondary to lisinopril. Lungs are clear, and there are no signs of infection.
2. **Hypertension**: Controlled on current regimen.
3. **Diabetes Mellitus**: Fasting glucose levels (120-140 mg/dL) show improvement.

## Plan
1. **Medication Changes**:
   - Discontinue lisinopril.
   - Start losartan 50 mg once daily. The patient was informed that the cough may take a few weeks to fully clear after stopping lisinopril.
   - Continue metformin at the current dose (500 mg with breakfast and dinner).
2. **Diagnostics**:
   - Repeat A1C and basic metabolic panel today.
   - Check potassium and kidney function again in two weeks due to the medication change.
3. **Monitoring**:
   - Continue checking fasting blood sugars a few mornings a week.
   - Return to clinic in three months.
4. **Follow-up Instructions**:
   - Call sooner if the cough does not improve in four weeks, or if the patient develops fever, shortness of breath, or begins producing sputum.
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
| "Do not include the patient's name even if it was spoken; write the patient" | One less piece of PHI in the note body. The first version of this line said only "no patient name", and the model wrote "Mr. Alvarez" anyway, because the transcript did. Naming the exact situation and giving the replacement fixed it. A rule the model can misread is a rule it will break. |

The package keeps templates as plain Markdown in `scribe/templates/`. Open `soap.md`; it is the script's prompt with more structure. You edit it with a text editor, not Python. Lesson 9 is about writing your own.

## The two settings that matter

**`temperature: 0.2`.** Temperature is how much randomness the model adds when picking each word. At 0.8 it is creative; at 0 it is deterministic. A scribe should be boring. 0.1 to 0.3.

**Thinking off.** Newer models (Qwen3, DeepSeek-R1 and others) "think" in a hidden monologue before answering. On our test machine that more than doubled the reply for `qwen3:8b` on the sample visit, from about 290 tokens to about 700, for no gain on a scribe task; the transcript is right there. Worse, the monologue counts against `max_tokens`, so a long think can leave no room for the note. There is no single off switch. vLLM and llama.cpp read `chat_template_kwargs`. Ollama ignores that field on this endpoint and reads `reasoning_effort` instead, so the script sends both. The package sends both as well, strips any `<think>` block that leaks through, and retries with fewer extra fields if a server rejects them.

## Two failures that give no error

**The transcript does not fit.** Every model server reads a limited number of tokens per request, called its context window. A token is about three quarters of a word. Our two and a half minute sample is about 1,250 tokens including the template, so a fifteen minute visit is roughly 6,000.

Some servers refuse a request that is too long, which is the good outcome. Ollama instead drops the *beginning* of the prompt and answers anyway. We tried it: a 9,700 token visit sent to `qwen3:8b` with a 4,096 token window was read as 2,050 tokens. The allergy and the blood thinner mentioned in the first minute were gone. So was the template, which sits at the very start: the reply was a chatty summary with the patient's name in it instead of a SOAP note. Nothing in the response said so.

Ollama picks its default window from your graphics memory: 4,096 tokens on smaller cards, 32,768 on our 32 GB card, more on very large ones. A fifteen minute visit does not fit in 4,096. Check what you have while a model is loaded:

```bash
ollama ps        # the CONTEXT column is the window in tokens
```

If it is too small, set it well above your longest visit. When you start Ollama by hand:

```bash
OLLAMA_CONTEXT_LENGTH=16384 ollama serve
```

On Linux the installer runs Ollama as a service, so set it there instead:

```bash
sudo systemctl edit ollama       # add the two lines below, save
#   [Service]
#   Environment="OLLAMA_CONTEXT_LENGTH=16384"
sudo systemctl restart ollama
```

A bigger window costs memory. On our card `qwen3:8b` took 5.6 GB at 4,096 tokens and 10 GB at 32,768.

**The note does not fit.** `max_tokens` caps the length of the reply. A model that hits the cap stops mid-sentence and the note ends halfway through the plan. The response says so, in a field most code never reads: `"finish_reason": "length"` instead of `"stop"`. The script prints a warning when it sees that.

The package checks for both in `check_draft()` in `scribe/notes.py`. A cut-off note is detected exactly. A dropped transcript is detected roughly, by comparing how much text was sent with how many tokens the server says it read. That catches a server that lost half the visit, not one that lost the first minute. Either warning appears in red above the note in the review app, in the terminal, and in the audit log.

So add one habit to your review: check that the note covers the *start* of the visit.

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
