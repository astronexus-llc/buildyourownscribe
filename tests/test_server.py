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
    # The app only answers to its own address, so the test client has to use it too.
    return TestClient(create_app(Settings(), pipeline=pipe), base_url="http://127.0.0.1:8765"), store


def new_session(client, tmp_path, label=""):
    wav = save_wav(np.zeros(16000, dtype=np.float32), tmp_path / "in.wav")
    with wav.open("rb") as f:
        return client.post("/api/sessions", files={"file": ("in.wav", f, "audio/wav")}, data={"label": label}).json()["id"]


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


def test_signed_session_is_locked_on_the_server(tmp_path):
    client, store = make_client(tmp_path)
    sid = new_session(client, tmp_path)
    client.post(f"/api/sessions/{sid}/transcribe")
    client.post(f"/api/sessions/{sid}/draft", json={})
    client.put(f"/api/sessions/{sid}/note", json={"text": "final"})
    assert client.post(f"/api/sessions/{sid}/sign", json={}).status_code == 200

    assert client.put(f"/api/sessions/{sid}/note", json={"text": "changed"}).status_code == 409
    assert client.post(f"/api/sessions/{sid}/draft", json={}).status_code == 409
    assert client.post(f"/api/sessions/{sid}/transcribe").status_code == 409
    assert client.post(f"/api/sessions/{sid}/sign", json={}).status_code == 409
    assert store.note(sid) == "final" and store.meta(sid).status == "signed"


def test_cannot_sign_without_a_note(tmp_path):
    client, store = make_client(tmp_path)
    sid = new_session(client, tmp_path)
    assert client.post(f"/api/sessions/{sid}/sign", json={}).status_code == 400
    assert store.meta(sid).status == "new"


def test_session_id_cannot_escape_the_data_folder(tmp_path):
    client, store = make_client(tmp_path)
    sid = new_session(client, tmp_path)
    for bad in ("%2e%2e", "..%2f..", "nope", sid + "%2f..", "%2e"):
        assert client.delete(f"/api/sessions/{bad}").status_code in (404, 405), bad
        assert client.get(f"/api/sessions/{bad}").status_code in (404, 405), bad
    assert store.root.is_dir() and store.path(sid, "audio.wav").exists()


def test_unknown_things_are_404_not_500(tmp_path):
    client, store = make_client(tmp_path)
    assert client.post("/api/sessions/nope/sign", json={}).status_code == 404
    assert client.put("/api/sessions/nope/note", json={"text": "x"}).status_code == 404
    assert client.post("/api/sessions/nope/transcribe").status_code == 404
    sid = new_session(client, tmp_path)
    client.post(f"/api/sessions/{sid}/transcribe")
    r = client.post(f"/api/sessions/{sid}/draft", json={"template": "nope"})
    assert r.status_code == 404 and "soap" in r.json()["detail"]


def test_only_answers_on_its_own_address(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.get("/api/sessions", headers={"Host": "evil.example"}).status_code == 400
    assert client.get("/api/sessions", headers={"Host": "localhost:8765"}).status_code == 200
    assert client.get("/api/sessions", headers={"Host": "[::1]:8765"}).status_code == 200


def test_refuses_writes_from_another_website(tmp_path):
    client, store = make_client(tmp_path)
    sid = new_session(client, tmp_path)
    r = client.post(f"/api/sessions/{sid}/transcribe", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403 and store.meta(sid).status == "new"
    r = client.post(f"/api/sessions/{sid}/transcribe", headers={"Origin": "http://127.0.0.1:8765"})
    assert r.status_code == 200


def test_extra_allowed_host(tmp_path):
    store = Store(StorageConfig(data_dir=tmp_path / "data"))
    settings = Settings(allowed_hosts=("scribe.clinic.lan",))
    pipe = Pipeline(settings, transcriber=FakeTranscriber(), llm=FakeLLM().client(), store=store)
    client = TestClient(create_app(settings, pipeline=pipe), base_url="http://scribe.clinic.lan")
    assert client.get("/api/sessions").status_code == 200


def test_old_unsigned_sessions_are_purged_when_the_app_starts(tmp_path):
    client, store = make_client(tmp_path)
    old = store.new_session("stale")
    store.update(old.id, created="2020-01-01T00:00:00+00:00")
    fresh = store.new_session("fresh")
    with client:                      # entering the context runs startup
        ids = [m["id"] for m in client.get("/api/sessions").json()]
    assert ids == [fresh.id]


def test_draft_warnings_reach_the_reviewer(tmp_path):
    store = Store(StorageConfig(data_dir=tmp_path / "data"))
    pipe = Pipeline(Settings(), transcriber=FakeTranscriber(), llm=FakeLLM(finish_reason="length").client(), store=store)
    client = TestClient(create_app(Settings(), pipeline=pipe), base_url="http://127.0.0.1:8765")
    sid = new_session(client, tmp_path)
    client.post(f"/api/sessions/{sid}/transcribe")
    assert "cut off" in client.post(f"/api/sessions/{sid}/draft", json={}).json()["warnings"][0]
    assert "cut off" in client.get(f"/api/sessions/{sid}").json()["meta"]["warnings"][0]
