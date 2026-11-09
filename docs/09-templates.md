# Lesson 9 · Templates for your specialty

*One evening.* At the end the scribe writes notes the way your clinic writes them.

## Where templates live

Built-in templates are Markdown files in `scribe/templates/`. Yours go in `scribe_data/templates/` and appear in the dropdown and in `scribe note --template <name>` automatically. A file with the same name as a built-in replaces it.

```bash
mkdir -p scribe_data/templates
cp scribe/templates/soap.md scribe_data/templates/derm-followup.md
```

Edit, save, draft. No restart needed.

## Anatomy of a template

```markdown
# Title                                 <- ignored by the model, for you

Who the model is and who reads the output.      <- register
What it is given (a timestamped transcript).

Rules:                                           <- the guardrails; keep these
- only what is in the transcript
- "Not discussed." for empty sections
- [unclear] for doubtful words
- no preamble, no disclaimers, no patient name

Format exactly:                                  <- your clinic's note shape
## Heading one
What belongs under it, in one or two lines.
## Heading two
...
```

The rules block is the part you should not weaken. The format block is yours.

## Tips that come from experience

**Describe each section in one sentence.** "Objective: only what the clinician stated as examined or measured" beats a bare heading. The model is good at following a description and bad at guessing your conventions.

**Say what to do with things that do not fit.** "Anything that is not clearly history or plan goes under Subjective" prevents the model inventing a fifth heading.

**Give an example for formatting, not for content.** If you want `Medications: name dose route frequency`, show one made-up line in that shape. Do not paste a real note as an example: the model will borrow its content.

**Specialty vocabulary helps the transcript too.** Whisper accepts an `initial_prompt` with words to expect. The package does not expose it yet; adding it to `WhisperTranscriber.transcribe()` is a one-line change and a good exercise. A list of your twenty most common drug names there measurably improves recognition.

**Keep the per-draft instructions box for the exceptions.** "Patient is here for pre-op clearance, use that heading" belongs in the box, not in the template.

**Short beats long.** A 400-word template is not more precise than a 150-word one; it is more likely to be partly ignored.

## Three starting points

The built-ins cover a general visit (`soap`), a short follow-up (`progress`), and a plain-language patient handout (`after-visit-summary`). Common adaptations:

=== "Mental health"
    Sections: Presenting concern · Mental status (only as stated) · Risk (only as asked and answered; write "Not assessed." if not) · Formulation · Plan. Add a rule: "Report risk questions and answers verbatim; never summarise them."

=== "Physiotherapy"
    Sections: Subjective (pain, function, goals) · Objective measures stated · Treatment given today · Home programme · Next visit. Add: "Record ranges and counts exactly as spoken."

=== "Paediatrics"
    Sections: History from (who is reporting) · Feeding, sleep, development as discussed · Exam as stated · Growth as stated · Assessment · Plan and anticipatory guidance given. Add: "Note who answered each question when the parent and child differ."

## Test every change

Edit the template, re-run your Lesson 8 test set, read the notes against the scripts. A template change that improves formatting can quietly worsen faithfulness. Your tally is the referee.

Next: [Lesson 10 · Where to go next](10-next.md).
