from pathlib import Path

import pytest

from app.voice.service import MODEL_NAME, Voice

DEV_MODEL = Path(__file__).parent.parent / "data" / "voices" / MODEL_NAME


def test_without_a_model_the_tablet_reads(client):
    assert client.get("/api/voice/status").json() == {"available": False}
    assert client.get("/api/voice", params={"text": "Hola"}).status_code == 503


def test_text_too_long_or_empty(client):
    assert client.get("/api/voice", params={"text": ""}).status_code == 422
    assert client.get("/api/voice", params={"text": "a" * 601}).status_code == 422


@pytest.mark.skipif(not DEV_MODEL.is_file(), reason="the voice model is only on a development machine")
def test_the_natural_voice_says_it_and_keeps_it(tmp_path):
    voice = Voice(DEV_MODEL, tmp_path / "cache")
    audio = voice.speak("Comienza el aseo.")
    assert audio[:4] == b"RIFF" and len(audio) > 10_000
    assert len(list((tmp_path / "cache").glob("*.wav"))) == 1
    assert voice.speak("Comienza el aseo.") == audio
