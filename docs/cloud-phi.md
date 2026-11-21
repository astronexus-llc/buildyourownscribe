# Cloud models and PHI

*Twenty minutes, then a conversation with whoever handles compliance for you.* At the end you know which cloud model services will sign the contract that US law requires, what each one leaves out, and what it takes to point the scribe at one.

You do not need any of this. The course works end to end on your own machine, and [All open source, no cloud](open-source.md) shows how to check that. This page is for the reader whose hardware is too small for a good model, or who wants a larger model than a clinic can host, and who intends to do it lawfully.

!!! warning "Not legal advice, and it goes out of date"
    Everything below was read from each vendor's own pages on **21 November 2026**. Vendors change these terms several times a year. Follow the links and read the current page before you rely on any line here. This page covers the United States and HIPAA. Other countries have their own rules, and a US contract does not satisfy them.

## The rules

1. **Contract first.** A business associate agreement (BAA) with the vendor must be in place before the first real transcript is sent. Not after a trial.
2. **Only what the contract names.** A BAA covers listed services and listed features. The same company's other products are not covered because one of them is.
3. **A BAA is not compliance.** It makes the vendor responsible for its side. Your risk analysis, access control, consent, and audit trail are still yours. Every vendor below says so in its own words.
4. **Never the chat apps.** Pasting a transcript into a personal ChatGPT, Claude, or Gemini account is a disclosure of PHI to a company you have no contract with. No setting changes that.

## What would leave your machine

Only the drafting step moves. The recording stays on your disk and Whisper still runs locally. What goes to the vendor is the transcript and the note template, and what comes back is the draft. The transcript is PHI in full: names, dates, diagnoses, and everything the patient said.

## Five services that offer a BAA

| Service | How you get the BAA | What to know | Read |
|---|---|---|---|
| **Amazon Bedrock** | Accept it in AWS Artifact, inside the AWS console | Bedrock is on AWS's HIPAA eligible services list (updated 16 November 2026). PHI may go only into services on that list | [Eligible services](https://aws.amazon.com/compliance/hipaa-eligible-services-reference/), [AWS and HIPAA](https://aws.amazon.com/compliance/hipaa-compliance/) |
| **Azure OpenAI in Microsoft Foundry** | Nothing to sign. The BAA is part of Microsoft's Product Terms for every customer that is a covered entity or business associate | It applies only to services Microsoft lists as in scope. See the caution below. Microsoft states that prompts are not used for training and are not available to OpenAI | [Azure and HIPAA](https://learn.microsoft.com/en-us/azure/compliance/offerings/offering-hipaa-us), [Data privacy](https://learn.microsoft.com/en-us/azure/ai-foundry/responsible-ai/openai/data-privacy) |
| **Google Cloud** (Gemini Enterprise Agent Platform, formerly Vertex AI) | Review and accept it in the Google Cloud console | The covered list (updated 11 November 2026) includes "Generative AI on Agent Platform". Google says not to use pre-release features with PHI. Google AI Studio and the Gemini Developer API are not on the list | [Google Cloud and HIPAA](https://docs.cloud.google.com/docs/security/compliance/hipaa) |
| **OpenAI API** | In the API settings: Organization, General, HIPAA compliance support, Enable. Needs an established history of API use; otherwise write to `baa@openai.com` | Chat completions is on the eligible list. Web search with live internet access is not. OpenAI also requires a retention setting it calls Modified Retention. Once enabled it cannot be switched off | [Getting a BAA](https://help.openai.com/en/articles/8660679-how-can-i-get-a-business-associate-agreement-baa-with-openai), [Eligible products](https://help.openai.com/articles/20001069) |
| **Anthropic Claude API** | In the Claude Console, on the Data privacy page, for eligible organisations. Otherwise through Anthropic's sales team | Anthropic calls the setting HIPAA readiness. It applies to the whole organisation and is permanent. Zero data retention is not required. The Batch API, Files API, code execution, and web fetch are not covered | [BAA for commercial customers](https://privacy.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers), [API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) |

!!! warning "Azure: check the scope list yourself"
    Microsoft's public HIPAA page says the BAA covers "in-scope" services and points to a compliance document on its Service Trust Portal for the list. We could not confirm from the public pages that Azure OpenAI is on it. Get that confirmed in writing from Microsoft or from your organisation's Azure administrator before sending PHI.

Two more points that catch people.

**Abuse monitoring can mean a person reads prompts.** Several vendors keep prompts for a period and allow staff to review flagged ones. OpenAI's default is up to 30 days. Azure lets approved customers apply to turn human review off, and says that option ends for models released from 1 November 2026. Ask each vendor what applies under the BAA.

**The same model through another door has a different contract.** Claude on Amazon Bedrock is governed by your AWS agreement, not by Anthropic's. OpenAI models on Azure are governed by Microsoft's. The contract follows the company you pay.

## What is never covered

| Product | Status on the vendor's own pages |
|---|---|
| ChatGPT Business | OpenAI: "We do not offer a BAA for ChatGPT Business." Enterprise and Edu are arranged through sales |
| Claude Free, Pro, and Max | Consumer plans. Outside Anthropic's BAA |
| Google AI Studio, Gemini Developer API | Not on Google's covered list |
| Any vendor's preview or beta feature | Assume not covered unless the vendor says otherwise in writing |

For any personal or free plan from any vendor, assume no BAA exists.

## Which one to choose

- **Your organisation already has AWS, Azure, or Google Cloud with a BAA.** Use that one. The contract, the billing, and the person who administers it already exist.
- **You are starting from nothing.** The OpenAI API and the Anthropic API both let an organisation accept a BAA from a settings page. Those are the shortest routes.
- **You want the least code to change.** The scribe speaks the OpenAI chat format. The OpenAI API and Amazon Bedrock accept that format with a plain key. See the next section for the others.

The model matters less than the paperwork. Any current large model from these vendors drafts a better note than an 8B model on a laptop. Run your Lesson 8 test set on whichever you choose.

## Pointing the scribe at one

The locality guard from [Lesson 7](07-harden.md) refuses any address outside your machine and private network. One variable lifts it. Set it only when the contract is signed.

```bash
export SCRIBE_ALLOW_REMOTE_LLM=1                  # you have the BAA
export SCRIBE_LLM_BASE_URL=https://...            # from the list below
export SCRIBE_LLM_API_KEY=...                     # never commit this
export SCRIBE_LLM_MODEL=...                       # name it; do not rely on the first one listed
export SCRIBE_LLM_THINKING=on                     # send only standard fields
```

`SCRIBE_LLM_THINKING=on` matters here. Left at `off`, the scribe adds the fields that local servers use to switch thinking off, and a cloud API may reject or misread them.

!!! warning "Not tested by us"
    This course was built and tested on local models only. We did not run any of the cloud routes below. The addresses come from each vendor's documentation as read on 21 November 2026. Expect to adjust a line or two of `scribe/notes.py`.

| Service | Base URL | From the vendor's documentation |
|---|---|---|
| OpenAI API | `https://api.openai.com/v1` | `max_tokens`, which the scribe sends, is deprecated in favour of `max_completion_tokens` and is rejected by the o-series reasoning models |
| Amazon Bedrock | `https://bedrock-runtime.REGION.amazonaws.com/openai/v1` | Takes an Amazon Bedrock API key as the key. Does not list models, so `SCRIBE_LLM_MODEL` is required. [Docs](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-chat-completions.html) |
| Azure OpenAI | `https://YOUR-RESOURCE.openai.azure.com/openai/v1` | The model name is your deployment name. Microsoft's examples send the key in an `api-key` header, and the scribe sends `Authorization: Bearer`, so the header may need changing. [Docs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/api-version-lifecycle) |
| Google Cloud | `https://aiplatform.googleapis.com/v1/projects/PROJECT/locations/LOCATION/endpoints/openapi` | Model names look like `google/gemini-...`. The key is a Google access token that expires after an hour, so it needs refreshing. [Docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/openai) |
| Anthropic Claude API | Not a drop-in | Anthropic's API is the Messages API, a different request format. The scribe does not speak it as written, and the BAA covers only listed Messages API features |

## Before you switch it on

- [ ] The BAA is executed and you have a copy.
- [ ] Whoever is responsible for compliance has agreed, and the risk analysis names the vendor.
- [ ] You know the vendor's retention period for prompts and whether staff can review them.
- [ ] The API key lives outside the repository and outside any file you might share.
- [ ] Your consent wording still fits. Some clinics tell patients when an outside service processes the visit.
- [ ] You re-ran the Lesson 8 test set on the new model and kept the tally.
- [ ] You can go back. Unset the four variables and the scribe is local again.

The review step does not change. A cloud model's draft is still a draft until a licensed human signs it.
