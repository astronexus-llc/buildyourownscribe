"""Server tests with a fake transcriber and fake LLM, so no models are needed."""
import numpy as np
from fastapi.testclient import TestClient

from scribe.audio import save_wav
from scribe.config import Settings, StorageConfig
from scribe.pipeline import Pipeline
from scribe.server import create_app
from scribe.storage import Store
from scribe.transcribe import Segment, Transcriber, Transcript
from tests.conftest import FakeLLM


class FakeTranscriber(Transcriber):
    def transcribe(self, audio):
        return Transcript(segments=[Segment(0, 2, "fake words")], engine="fake", model="fake",
                          audio_seconds=len(audio) / 16000, elapsed_seconds=0.0)


def make_client(tmp_path):
    store = Store(StorageConfig(data_dir=tmp_path / "data"))
    pipe = Pipeline(Settings(), transcriber=FakeTranscriber(), llm=FakeLLM().client(), store=store)
    return TestClient(create_app(Settings(), pipeline=pipe)), store


def test_full_flow(tmp_path):
    client, store = make_client(tmp_path)
    wav = save_wav(np.zeros(16000, dtype=np.float32), tmp_path / "in.wav")

    assert client.get("/").status_code == 200
    assert "soap" in client.get("/api/templates").json()
    h = client.get("/api/health").json()
    assert h["llm"]["ok"]

    with wav.open("rb") as f:
        r = client.post("/api/sessions", files={"file": ("in.wav", f, "audio/wav")}, data={"label": "t"})
    sid = r.json()["id"]
    assert store.path(sid, "audio.wav").exists()

    assert client.post(f"/api/sessions/{sid}/transcribe").json()["transcript"] == "[00:00] fake words"
    r = client.post(f"/api/sessions/{sid}/draft", json={"template": "soap"})
    assert r.json()["note"].startswith("## Subjective")

    assert client.put(f"/api/sessions/{sid}/note", json={"text": "edited"}).json()["ok"]
    r = client.post(f"/api/sessions/{sid}/sign", json={"signer": "Dr"})
    assert r.json()["status"] == "signed"
    s = client.get(f"/api/sessions/{sid}").json()
    assert s["note"] == "edited" and s["meta"]["status"] == "signed"
    assert not store.path(sid, "audio.wav").exists()

    assert client.get("/api/sessions/nope").status_code == 404
    assert client.delete(f"/api/sessions/{sid}").json()["ok"]
    assert client.get("/api/sessions").json() == []


def test_draft_before_transcribe_is_400(tmp_path):
    client, store = make_client(tmp_path)
    sid = store.new_session().id
    assert client.post(f"/api/sessions/{sid}/draft", json={}).status_code == 400
