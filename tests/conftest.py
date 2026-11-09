import json

import httpx
import pytest

from scribe.config import LLMConfig, StorageConfig
from scribe.notes import LLMClient
from scribe.storage import Store
from scribe.transcribe import Segment, Transcript


@pytest.fixture
def transcript() -> Transcript:
    return Transcript(
        segments=[Segment(0.0, 3.2, "Good morning, how have you been?"),
                  Segment(3.5, 9.0, "I've had a dry cough for three weeks."),
                  Segment(70.0, 75.0, "Blood pressure today is one twenty-eight over eighty-two.")],
        engine="test", model="fake", audio_seconds=80.0, elapsed_seconds=0.1)


class FakeLLM:
    """Records requests and plays an OpenAI-shaped reply."""

    def __init__(self, reply="## Subjective\nCough.\n", reject_extras=False, finish_reason="stop", prompt_tokens=50):
        self.reply, self.reject_extras, self.requests = reply, reject_extras, []
        self.finish_reason, self.prompt_tokens = finish_reason, prompt_tokens

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "fake-model"}]})
        body = json.loads(request.content)
        self.requests.append(body)
        if self.reject_extras and "chat_template_kwargs" in body:
            return httpx.Response(400, json={"error": "unknown field"})
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": self.reply}, "finish_reason": self.finish_reason}],
            "usage": {"prompt_tokens": self.prompt_tokens, "completion_tokens": 10}})

    def client(self, **cfg) -> LLMClient:
        http = httpx.Client(transport=httpx.MockTransport(self.handler))
        return LLMClient(LLMConfig(base_url="http://localhost:11434/v1", **cfg), http=http)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def store(tmp_path) -> Store:
    return Store(StorageConfig(data_dir=tmp_path / "data", retention_days=7, delete_audio_on_sign=True))
