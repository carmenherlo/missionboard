"""The natural voice: texts read aloud with Piper, on this server, no internet
needed. Ported from an earlier version of the app, where
the family chose it: the woman's voice (speaker "F") of the Spanish model
es_ES-sharvard-medium. The browser plays it (static/js/components/speech.js);
without a model, or without Piper, there is no voice here and the tablet
reads with its own.

Each text, once said, is kept as a WAV file: routines repeat a lot.
"""

import hashlib
import io
import logging
import threading
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_NAME = "es_ES-sharvard-medium.onnx"
SPEAKER = "F"  # the woman's voice
# Piper's usual style reads rather flat: a livelier intonation, a less even
# rhythm and a bit faster (as chosen in an earlier version).
STYLE = {"noise_scale": 0.9, "noise_w_scale": 1.0, "length_scale": 0.88}
MAX_TEXT = 600  # characters; a routine's sentence is far shorter


class VoiceUnavailableError(RuntimeError):
    """No voice model, or Piper is not installed."""


class Voice:
    def __init__(self, model_path: Path, cache_dir: Path):
        self.model_path = model_path
        self.cache_dir = cache_dir
        self._piper = None  # the loaded model (loading takes a couple of seconds)
        self._lock = threading.Lock()  # one synthesis at a time

    @property
    def available(self) -> bool:
        if not self.model_path.is_file():
            return False
        try:
            import piper  # noqa: F401
        except ImportError:
            return False
        return True

    def load(self) -> None:
        """Load the model now (at startup, in the background), so the first sentence is quick."""
        try:
            with self._lock:
                self._load()
        except VoiceUnavailableError as error:
            logger.warning("No natural voice: %s", error)

    def speak(self, text: str) -> bytes:
        """The text said aloud, as a WAV file (from the cache when it was said before)."""
        key = hashlib.sha256(f"{self.model_path.name}|{SPEAKER}|{sorted(STYLE.items())}|{text}".encode()).hexdigest()
        cached = self.cache_dir / f"{key}.wav"
        if cached.is_file():
            return cached.read_bytes()
        with self._lock:
            piper = self._load()
            from piper import SynthesisConfig

            speaker = piper.config.speaker_id_map.get(SPEAKER)
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav:
                piper.synthesize_wav(text, wav, syn_config=SynthesisConfig(speaker_id=speaker, **STYLE))
        audio = buffer.getvalue()
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(audio)
        except OSError as error:  # a full or read-only disk: it still talks, just not cached
            logger.warning("Voice cache not written: %s", error)
        return audio

    def _load(self):
        if self._piper is None:
            if not self.model_path.is_file():
                raise VoiceUnavailableError(f"no voice model at {self.model_path}")
            try:
                from piper import PiperVoice
            except ImportError as error:
                raise VoiceUnavailableError("Piper is not installed (pip install piper-tts)") from error
            self._piper = PiperVoice.load(self.model_path)
        return self._piper
