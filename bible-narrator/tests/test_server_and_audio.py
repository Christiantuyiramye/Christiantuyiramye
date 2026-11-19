import io
import os
import wave
from pathlib import Path

import numpy as np
import pytest

from bible_narrator.tts import ESPEAK_VOICES, TTSManager


def test_api_requires_token_and_local_host(state):
    from fastapi.testclient import TestClient

    from bible_narrator.server import create_app

    c = TestClient(create_app(state, token="secret"))
    assert c.get("/api/status").status_code == 401
    assert c.get("/api/status", headers={"X-App-Token": "wrong"}).status_code == 401
    assert c.get("/api/status", headers={"X-App-Token": "secret", "Host": "evil.example"}).status_code == 403
    assert c.get("/api/status", headers={"X-App-Token": "secret"}).status_code == 200


def test_starter_library_is_public_domain_and_labeled(client):
    r = client.get("/api/sources").json()
    titles = {s["title"]: s for s in r["sources"]}
    assert titles["Berean Standard Bible"]["kind"] == "scripture"
    assert titles["Easton's Bible Dictionary"]["kind"] == "dictionary"
    assert all(s["license"] for s in r["sources"])


def test_passage_lookup_and_navigation(client):
    r = client.get("/api/passage", params={"ref": "Psalm 23"}).json()
    assert r["reference"] == "Psalms 23" and len(r["verses"]) == 6
    assert r["prev"] == "Psalms 22" and r["next"] == "Psalms 24"
    assert r["source"]["abbreviation"] == "BSB"
    bad = client.get("/api/passage", params={"ref": "not a passage"})
    assert bad.status_code == 400


def test_import_requires_rights_confirmation(client):
    body = b"book,chapter,verse_start,verse_end,text\nJohn,1,1,2,Sample note.\n"
    r = client.post("/api/sources/import", params={"filename": "n.csv", "kind": "commentary", "title": "Notes"}, content=body)
    assert r.status_code == 400
    r = client.post("/api/sources/import", params={"filename": "n.csv", "kind": "commentary", "title": "Notes",
                                                    "rights_confirmed": "1", "license": "CC0"}, content=body)
    assert r.status_code == 200
    sid = r.json()["source"]["id"]
    p = client.get("/api/passage", params={"ref": "John 1:1-3"}).json()
    assert any(n["title"] == "Notes" and n["kind"] == "commentary" for n in p["commentary"])
    assert client.delete(f"/api/sources/{sid}").status_code == 200


def test_settings_persist_and_reject_remote_model_servers(client, state):
    assert client.put("/api/settings", json={"playback_rate": 1.25, "volume": 0.5}).json()["playback_rate"] == 1.25
    assert state.settings.path.exists() and '"playback_rate": 1.25' in state.settings.path.read_text()
    r = client.put("/api/settings", json={"local_server_url": "https://api.example.com/v1"})
    assert r.status_code == 400


def _wav(data: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(data)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32), w.getframerate()


def _features(x: np.ndarray, sr: int) -> tuple[float, float]:
    """Spectral centroid and a rough pitch estimate — enough to tell voices apart."""
    x = x[np.abs(x) > 200] if np.any(np.abs(x) > 200) else x
    spec = np.abs(np.fft.rfft(x[: sr * 2]))
    freqs = np.fft.rfftfreq(len(x[: sr * 2]), 1 / sr)
    centroid = float((spec * freqs).sum() / spec.sum())
    band = (freqs > 70) & (freqs < 400)
    pitch = float(freqs[band][np.argmax(spec[band])])
    return centroid, pitch


def _assert_distinct(manager: TTSManager, voice_ids: list[str]):
    text = "The Lord is my shepherd; I shall not want."
    feats, lengths, hashes = [], [], set()
    for vid in voice_ids:
        data, dur = manager.synthesize(vid, text)
        assert dur > 1.0
        x, sr = _wav(data)
        hashes.add(hash(x.tobytes()))
        lengths.append(len(x))
        feats.append(_features(x, sr))
    assert len(hashes) == len(voice_ids), "two voices produced identical audio"
    # Every pair must differ audibly in timbre, pitch or timing.
    for i in range(len(feats)):
        for j in range(i + 1, len(feats)):
            (c1, p1), (c2, p2) = feats[i], feats[j]
            assert abs(c1 - c2) > 15 or abs(p1 - p2) > 4 or abs(lengths[i] - lengths[j]) > 1000, (voice_ids[i], voice_ids[j])


def test_ten_basic_voices_are_genuinely_distinct(tmp_path):
    m = TTSManager(tmp_path / "none", tmp_path / "cache")
    ids = [f"espeak:{v[0]}" for v in ESPEAK_VOICES]
    assert len(ids) >= 10
    _assert_distinct(m, ids)


@pytest.mark.skipif(not os.environ.get("KOKORO_DIR"), reason="set KOKORO_DIR to a folder with Kokoro model + voices")
def test_natural_voices_are_genuinely_distinct(tmp_path):
    m = TTSManager(Path(os.environ["KOKORO_DIR"]), tmp_path / "cache")
    voices = [v["id"] for v in m.voices() if v["engine"] == "kokoro" and v["recommended"]][:12]
    assert len(voices) >= 10
    _assert_distinct(m, voices)


def test_tts_endpoint_returns_wav_and_caches(client):
    r = client.post("/api/tts", json={"voice": "espeak:en+m1", "text": "In the beginning."})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and float(r.headers["x-duration"]) > 0.5
    r2 = client.post("/api/tts", json={"voice": "espeak:en+m1", "text": "In the beginning."})
    assert r2.content == r.content
    assert client.post("/api/tts", json={"voice": "kokoro:not_a_voice", "text": "x"}).status_code == 400


def test_recommendations_learn_from_history(client):
    client.delete("/api/history")
    assert client.get("/api/recommendations").json()["basis"] == "starter"
    client.post("/api/history", json={"book": 1, "chapter": 1, "source_id": 1, "seconds": 300, "completed": True})
    recs = client.get("/api/recommendations").json()
    assert recs["basis"] == "history"
    assert recs["items"][0]["reference"] == "Genesis 2" and recs["items"][0]["kind"] == "continue"
    assert any(i["kind"] == "similar" for i in recs["items"])
    client.put("/api/settings", json={"history_enabled": False})
    assert client.get("/api/recommendations").json()["basis"] == "disabled"
    assert client.get("/api/history").json()["history"] == []  # turning history off clears it
    client.put("/api/settings", json={"history_enabled": True})
