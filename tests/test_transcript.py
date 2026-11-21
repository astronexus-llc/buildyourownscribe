import numpy as np

from scribe.transcribe import Segment, Transcript


def test_as_lines_and_roundtrip(tmp_path, transcript):
    lines = transcript.as_lines().splitlines()
    assert lines[0] == "[00:00] Good morning, how have you been?"
    assert lines[2].startswith("[01:10]")
    p = tmp_path / "t.json"
    transcript.save(p)
    back = Transcript.load(p)
    assert back.to_dict() == transcript.to_dict()


def test_text_skips_empty_segments():
    t = Transcript(segments=[Segment(0, 1, "  "), Segment(1, 2, "hello"), Segment(2, 3, "world ")])
    assert t.text == "hello world"


def test_audio_roundtrip(tmp_path):
    from scribe.audio import duration_seconds, load, save_wav

    sr = 16000
    tone = (0.3 * np.sin(2 * np.pi * 440 * np.arange(sr * 2) / sr)).astype(np.float32)
    p = save_wav(tone, tmp_path / "tone.wav")
    assert abs(duration_seconds(p) - 2.0) < 0.01
    back = load(p)
    assert back.dtype == np.float32 and abs(len(back) - len(tone)) < 10


def test_importing_the_transcriber_switches_onnxruntime_telemetry_off():
    import os

    import scribe.transcribe  # noqa: F401

    assert os.environ.get("ORT_DISABLE_TELEMETRY") == "1"


def test_whisper_model_given_as_a_folder_is_used_as_is(tmp_path):
    from scribe.transcribe import resolve_whisper_model

    assert resolve_whisper_model(str(tmp_path)) == str(tmp_path)


def test_cached_whisper_model_is_not_fetched_again(monkeypatch):
    import faster_whisper.utils as fw

    from scribe.transcribe import resolve_whisper_model

    calls = []

    def fake_download(name, local_files_only=False, **kw):
        calls.append(local_files_only)
        return "/cache/" + name

    monkeypatch.setattr(fw, "download_model", fake_download)
    assert resolve_whisper_model("small.en") == "/cache/small.en"
    assert calls == [True]


def test_missing_whisper_model_is_downloaded_once(monkeypatch, capsys):
    import faster_whisper.utils as fw

    from scribe.transcribe import resolve_whisper_model

    calls = []

    def fake_download(name, local_files_only=False, **kw):
        calls.append(local_files_only)
        if local_files_only:
            raise FileNotFoundError("not cached")
        return "/cache/" + name

    monkeypatch.setattr(fw, "download_model", fake_download)
    assert resolve_whisper_model("small.en") == "/cache/small.en"
    assert calls == [True, False]
    assert "downloading it once" in capsys.readouterr().err
