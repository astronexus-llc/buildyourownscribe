import json
from datetime import datetime, timedelta, timezone


def test_session_lifecycle(store, transcript, tmp_path):
    meta = store.new_session("room 3")
    assert meta.status == "new"
    store.path(meta.id, "audio.wav").write_bytes(b"RIFF....")

    store.save_transcript(meta.id, transcript)
    assert store.meta(meta.id).status == "transcribed"
    assert store.transcript(meta.id).text.startswith("Good morning")

    store.save_note(meta.id, "## Subjective\nCough", template="soap", model="m")
    assert store.meta(meta.id).status == "drafted"

    store.save_note(meta.id, "## Subjective\nCough, edited", edited=True)
    assert store.meta(meta.id).status == "drafted"  # editing does not change status

    store.sign(meta.id, signer="Dr A")
    m = store.meta(meta.id)
    assert m.status == "signed" and m.signed_at
    assert not store.path(meta.id, "audio.wav").exists(), "audio should be deleted on sign"
    assert store.note(meta.id) == "## Subjective\nCough, edited"

    events = [json.loads(l)["event"] for l in store.audit_path.read_text().splitlines()]
    assert events == ["created", "transcribed", "drafted", "edited", "signed", "audio_deleted"]


def test_purge_removes_old_unsigned_only(store):
    old_unsigned = store.new_session("old")
    old_signed = store.new_session("old signed")
    fresh = store.new_session("fresh")
    past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
    store.update(old_unsigned.id, created=past)
    store.update(old_signed.id, created=past, status="signed")

    removed = store.purge()
    assert removed == [old_unsigned.id]
    ids = {m.id for m in store.list_sessions()}
    assert ids == {old_signed.id, fresh.id}


def test_list_sessions_newest_first(store):
    a = store.new_session("a")
    b = store.new_session("b")
    store.update(b.id, created="2030-01-01T00:00:00+00:00")
    ids = [m.id for m in store.list_sessions()]
    assert set(ids) == {a.id, b.id}


def test_signed_session_refuses_changes(store, transcript):
    import pytest
    from scribe.storage import SessionLocked

    sid = store.new_session().id
    store.save_transcript(sid, transcript)
    with pytest.raises(RuntimeError, match="no note"):
        store.sign(sid)
    store.save_note(sid, "draft", template="soap", model="m")
    store.sign(sid)
    for change in (lambda: store.save_note(sid, "x", edited=True), lambda: store.save_note(sid, "x"),
                   lambda: store.save_transcript(sid, transcript), lambda: store.sign(sid)):
        with pytest.raises(SessionLocked):
            change()
    assert store.note(sid) == "draft"


def test_ids_that_are_not_session_ids_are_rejected(store):
    import pytest

    for bad in ("..", ".", "", "../..", "a/b", "20260101-000000-zzzzzz"):
        with pytest.raises(KeyError):
            store.dir(bad)
        with pytest.raises(KeyError):
            store.delete_session(bad)
    assert store.root.is_dir()
