import pytest

from scribe.config import LLMConfig, is_local_url
from scribe.notes import LLMClient, build_messages, list_templates, load_template
from tests.conftest import FakeLLM


def test_builtin_templates_present():
    names = list_templates()
    assert {"soap", "progress", "after-visit-summary", "transcript-cleanup"} <= set(names)
    for n in names:
        text = load_template(n)
        assert "transcript" in text.lower()


def test_user_templates_override(tmp_path):
    (tmp_path / "soap.md").write_text("my custom soap prompt about the transcript")
    (tmp_path / "derm.md").write_text("derm template for the transcript")
    names = list_templates(tmp_path)
    assert names["soap"] == tmp_path / "soap.md"
    assert "derm" in names


def test_build_messages_includes_extra_instructions(transcript):
    msgs = build_messages("SYSTEM", transcript.as_lines(), "Use British spelling.")
    assert msgs[0]["role"] == "system" and "British spelling" in msgs[0]["content"]
    assert "[01:10] Blood pressure" in msgs[1]["content"]


def test_draft_strips_thinking_and_records_usage(transcript):
    fake = FakeLLM(reply="<think>hmm</think>\n## Subjective\nCough.")
    d = fake.client().draft(transcript, template="soap")
    assert d.text.startswith("## Subjective")
    assert d.model == "fake-model" and d.completion_tokens == 10
    assert fake.requests[0]["chat_template_kwargs"] == {"enable_thinking": False}


def test_retries_without_extras_on_400(transcript):
    fake = FakeLLM(reject_extras=True)
    d = fake.client().draft(transcript)
    assert d.text.startswith("## Subjective")
    assert len(fake.requests) == 3
    assert not {"chat_template_kwargs", "think", "reasoning_effort"} & set(fake.requests[-1])


def test_thinking_off_sends_every_known_switch(transcript):
    fake = FakeLLM()
    fake.client().draft(transcript)
    sent = fake.requests[0]
    assert sent["reasoning_effort"] == "none"            # Ollama's OpenAI endpoint
    assert sent["chat_template_kwargs"] == {"enable_thinking": False}   # vLLM, llama.cpp
    assert len(fake.requests) == 1


def test_server_that_rejects_only_reasoning_effort_keeps_the_other_switch(transcript):
    fake = FakeLLM(reject_extras="reasoning_effort")
    fake.client().draft(transcript)
    assert len(fake.requests) == 2
    assert "reasoning_effort" not in fake.requests[1] and "chat_template_kwargs" in fake.requests[1]


def test_thinking_on_sends_no_extras(transcript):
    fake = FakeLLM()
    fake.client(thinking="on").draft(transcript)
    assert "chat_template_kwargs" not in fake.requests[0] and "reasoning_effort" not in fake.requests[0]


def test_explicit_model_is_used(transcript):
    fake = FakeLLM()
    fake.client(model="my-model").draft(transcript)
    assert fake.requests[0]["model"] == "my-model"


@pytest.mark.parametrize("url,local", [
    ("http://localhost:11434/v1", True), ("http://127.0.0.1:8000/v1", True), ("http://10.0.0.5:8000/v1", True),
    ("http://192.168.1.20:11434/v1", True), ("http://172.20.0.1/v1", True), ("http://spark.lan:8002/v1", True),
    ("https://api.openai.com/v1", False), ("http://8.8.8.8/v1", False), ("http://172.32.0.1/v1", False),
])
def test_is_local_url(url, local):
    assert is_local_url(url) is local


def test_remote_llm_refused_by_default():
    with pytest.raises(RuntimeError, match="BAA"):
        LLMClient(LLMConfig(base_url="https://api.example.com/v1"))
    LLMClient(LLMConfig(base_url="https://api.example.com/v1", allow_remote=True))  # does not raise


def test_clean_draft_has_no_warnings(transcript):
    assert FakeLLM(prompt_tokens=400).client().draft(transcript).warnings == []


def test_cut_off_note_is_flagged(transcript):
    d = FakeLLM(finish_reason="length", prompt_tokens=400).client().draft(transcript)
    assert len(d.warnings) == 1 and "cut off" in d.warnings[0]


def test_truncated_transcript_is_flagged(transcript):
    # The prompt is well over a thousand characters; a server that says it read
    # 50 tokens of it dropped most of the visit.
    d = FakeLLM(prompt_tokens=50).client().draft(transcript)
    assert len(d.warnings) == 1 and "context window" in d.warnings[0]
