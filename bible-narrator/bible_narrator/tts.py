"""Local text-to-speech.

Engines
* Kokoro-82M (Apache-2.0) - natural neural voices, run with onnxruntime.
  Needs a one-time download (~115 MB: model + voice files).
* eSpeak NG (GPL-3.0) - small formant synthesizer that ships inside the
  ``espeakng-loader`` wheel (it is also Kokoro's phonemizer). Robotic, but
  always available, so Read Scripture works before any download.

All synthesis happens in this process; audio is cached on disk by
(engine, voice, text) so replays are instant.
"""
from __future__ import annotations

import ctypes
import glob
import hashlib
import io
import logging
import os
import re
import threading
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

try:  # never send onnxruntime usage events (only relevant on Windows builds)
    import onnxruntime as _ort

    if hasattr(_ort, "disable_telemetry_events"):
        _ort.disable_telemetry_events()
except Exception:  # noqa: BLE001
    _ort = None


@dataclass
class Voice:
    id: str  # "<engine>:<name>"
    engine: str
    name: str
    label: str
    accent: str
    gender: str
    quality: str
    description: str
    license: str
    recommended: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in ("id", "engine", "name", "label", "accent", "gender", "quality",
                                              "description", "license", "recommended")}


# --------------------------------------------------------------------------- text prep

_ALLCAPS = re.compile(r"\b([A-Z]{2,})\b")
_KEEP_CAPS = {"I", "O", "II", "III", "IV", "BC", "AD", "OK"}


def speakable(text: str) -> str:
    """Prepare text for speech: LORD -> Lord, drop citation markers and symbols."""
    text = re.sub(r"\[\d+(?:\s*,\s*\d+)*\]", "", text or "")
    text = _ALLCAPS.sub(lambda m: m.group(1) if m.group(1) in _KEEP_CAPS else m.group(1).capitalize(), text)
    text = text.replace("¶", " ").replace("—", ", ").replace("–", "-")
    text = re.sub(r"(\d+):(\d+)", r"\1, verse \2", text)  # "3:16" -> "3, verse 16"
    return re.sub(r"\s+", " ", text).strip()


def to_wav(samples: np.ndarray, sample_rate: int) -> bytes:
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def wav_duration(data: bytes) -> float:
    with wave.open(io.BytesIO(data), "rb") as w:
        return w.getnframes() / float(w.getframerate())


# --------------------------------------------------------------------------- Kokoro

# Voice names, accents and quality grades follow the Kokoro-82M model card.
KOKORO_VOICES: list[tuple[str, str, str, bool]] = [
    # (id, label, grade, recommended)
    ("af_heart", "Heart", "A", True),
    ("af_bella", "Bella", "A-", True),
    ("af_nicole", "Nicole (soft, close)", "B-", True),
    ("af_aoede", "Aoede", "C+", True),
    ("af_kore", "Kore", "C+", True),
    ("af_sarah", "Sarah", "C+", True),
    ("af_nova", "Nova", "C", False),
    ("af_alloy", "Alloy", "C", False),
    ("af_sky", "Sky", "C-", False),
    ("af_jessica", "Jessica", "D", False),
    ("af_river", "River", "D", False),
    ("am_michael", "Michael", "C+", True),
    ("am_fenrir", "Fenrir", "C+", True),
    ("am_puck", "Puck", "C+", True),
    ("am_echo", "Echo", "D", False),
    ("am_eric", "Eric", "D", False),
    ("am_liam", "Liam", "D", False),
    ("am_onyx", "Onyx", "D", False),
    ("am_adam", "Adam", "F+", False),
    ("bf_emma", "Emma", "B-", True),
    ("bf_isabella", "Isabella", "C", True),
    ("bf_alice", "Alice", "D", False),
    ("bf_lily", "Lily", "D", False),
    ("bm_george", "George", "C", True),
    ("bm_fable", "Fable", "C", True),
    ("bm_lewis", "Lewis", "D+", True),
    ("bm_daniel", "Daniel", "D", True),
]
KOKORO_LICENSE = "Apache-2.0 (Kokoro-82M by hexgrad; voices included in the model release)"


def find_kokoro_files(folder: Path) -> tuple[Path | None, Path | None, list[Path]]:
    """Locate the ONNX model, a voices .bin/.npz pack, or a folder of per-voice .bin files."""
    if not folder or not folder.exists():
        return None, None, []
    onnx = sorted(folder.rglob("*.onnx"), key=lambda p: p.stat().st_size)
    model = onnx[0] if onnx else None  # prefer the smaller quantized model if both exist
    pack = None
    for name in ("voices-v1.0.bin", "voices.npz", "voices.bin"):
        p = next(iter(folder.rglob(name)), None)
        if p:
            pack = p
            break
    singles = [Path(p) for p in glob.glob(str(folder / "**" / "*.bin"), recursive=True)
               if re.fullmatch(r"[ab][fm]_[a-z]+\.bin", Path(p).name)]
    return model, pack, singles


class KokoroEngine:
    name = "kokoro"
    sample_rate = 24000

    def __init__(self, folder: Path, cache_dir: Path):
        self.folder = Path(folder)
        self.cache_dir = cache_dir
        self._kokoro = None
        self._lock = threading.Lock()
        self.error = ""
        self.model_path, self.pack_path, self.single_voices = find_kokoro_files(self.folder)
        self.voice_names: set[str] = set()
        if self.pack_path is not None:
            try:
                self.voice_names = set(np.load(self.pack_path).files)
            except Exception as e:  # noqa: BLE001
                self.error = f"Voice pack unreadable: {e}"
        self.voice_names |= {p.stem for p in self.single_voices}

    @property
    def installed(self) -> bool:
        return self.model_path is not None and bool(self.voice_names)

    def status(self) -> dict[str, Any]:
        return {
            "engine": "kokoro",
            "installed": self.installed,
            "loaded": self._kokoro is not None,
            "folder": str(self.folder),
            "model": str(self.model_path or ""),
            "voices": len(self.voices()),
            "error": self.error,
            "license": KOKORO_LICENSE,
        }

    def voices(self) -> list[Voice]:
        out = []
        for vid, label, grade, rec in KOKORO_VOICES:
            if vid not in self.voice_names:
                continue
            accent = "American English" if vid[0] == "a" else "British English"
            gender = "female" if vid[1] == "f" else "male"
            out.append(Voice(
                id=f"kokoro:{vid}", engine="kokoro", name=vid, label=label, accent=accent, gender=gender,
                quality=f"Natural · grade {grade}", description=f"{accent}, {gender} voice ({vid})",
                license=KOKORO_LICENSE, recommended=rec,
            ))
        return out

    def _load(self):
        if self._kokoro is not None:
            return self._kokoro
        if not self.installed:
            raise RuntimeError("Kokoro voices are not installed. Open Voices to download or select them.")
        from kokoro_onnx import Kokoro

        pack = self.pack_path
        if pack is None:
            # Build an .npz voice pack from individual <voice>.bin files (raw float32 [510,1,256]).
            pack = self.cache_dir / "kokoro-voices.npz"
            sig = "|".join(sorted(f"{p.name}:{p.stat().st_size}" for p in self.single_voices))
            sig_file = pack.with_suffix(".sig")
            if not pack.exists() or not sig_file.exists() or sig_file.read_text() != sig:
                arrays = {p.stem: np.fromfile(p, dtype=np.float32).reshape(-1, 1, 256) for p in self.single_voices}
                with open(pack, "wb") as f:
                    np.savez(f, **arrays)
                sig_file.write_text(sig)
        self._kokoro = Kokoro(str(self.model_path), str(pack))
        return self._kokoro

    def synthesize(self, voice: str, text: str) -> tuple[np.ndarray, int]:
        with self._lock:
            k = self._load()
            lang = "en-gb" if voice.startswith("b") else "en-us"
            samples, sr = k.create(text, voice=voice, speed=1.0, lang=lang)
            return np.asarray(samples, dtype=np.float32), int(sr)


# --------------------------------------------------------------------------- eSpeak NG

ESPEAK_VOICES: list[tuple[str, str, str, str, str]] = [
    # (voice spec, label, accent, gender, description)
    ("en-us+m3", "Basic · Samuel", "American English", "male", "Steady mid-pitch American voice"),
    ("en-us+f3", "Basic · Ruth", "American English", "female", "Clear American voice"),
    ("en-gb+m1", "Basic · Thomas", "British English", "male", "Lower British voice"),
    ("en-gb+f2", "Basic · Lydia", "British English", "female", "Bright British voice"),
    ("en-gb-scotland+m4", "Basic · Andrew", "Scottish English", "male", "Scottish accent"),
    ("en-gb-x-rp+f4", "Basic · Martha", "British (RP) English", "female", "Received Pronunciation"),
    ("en-029+m2", "Basic · Silas", "Caribbean English", "male", "Caribbean accent"),
    ("en-us-nyc+m7", "Basic · Jonah", "New York English", "male", "New York accent, deep"),
    ("en-gb-x-gbcwmd+f5", "Basic · Naomi", "West Midlands English", "female", "Soft West Midlands accent"),
    ("en-us+klatt4", "Basic · Ezra", "American English", "male", "Klatt synthesiser timbre"),
]
ESPEAK_LICENSE = "GPL-3.0-or-later (eSpeak NG, bundled via espeakng-loader)"


class EspeakEngine:
    """eSpeak NG through its C API (synchronous mode, audio returned via callback)."""

    name = "espeak"

    def __init__(self):
        self._lib = None
        self._lock = threading.Lock()
        self.sample_rate = 22050
        self.error = ""
        self._chunks: list[np.ndarray] = []
        self._cb = None
        try:
            import espeakng_loader  # noqa: F401

            self.available = True
        except ImportError:
            self.available = False
            self.error = "espeakng-loader is not installed"

    def status(self) -> dict[str, Any]:
        return {"engine": "espeak", "installed": self.available, "voices": len(ESPEAK_VOICES) if self.available else 0,
                "error": self.error, "license": ESPEAK_LICENSE}

    def voices(self) -> list[Voice]:
        if not self.available:
            return []
        return [Voice(id=f"espeak:{spec}", engine="espeak", name=spec, label=label, accent=accent, gender=gender,
                      quality="Basic · robotic", description=desc, license=ESPEAK_LICENSE, recommended=True)
                for spec, label, accent, gender, desc in ESPEAK_VOICES]

    def _load(self):
        if self._lib is not None:
            return self._lib
        import espeakng_loader

        lib = ctypes.CDLL(espeakng_loader.get_library_path())
        lib.espeak_Initialize.restype = ctypes.c_int
        lib.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        sr = lib.espeak_Initialize(2, 0, espeakng_loader.get_data_path().encode(), 0)  # AUDIO_OUTPUT_SYNCHRONOUS
        if sr <= 0:
            raise RuntimeError("eSpeak NG failed to initialise")
        self.sample_rate = sr
        CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)

        def on_audio(wav, numsamples, events):
            if numsamples > 0 and wav:
                self._chunks.append(np.ctypeslib.as_array(wav, shape=(numsamples,)).astype(np.float32) / 32768.0)
            return 0

        self._cb = CALLBACK(on_audio)
        lib.espeak_SetSynthCallback(self._cb)
        lib.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
        lib.espeak_SetParameter.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lib.espeak_Synth.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_int, ctypes.c_uint,
                                     ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        self._lib = lib
        return lib

    def synthesize(self, voice: str, text: str) -> tuple[np.ndarray, int]:
        with self._lock:
            lib = self._load()
            if lib.espeak_SetVoiceByName(voice.encode()) != 0:
                raise RuntimeError(f"eSpeak voice '{voice}' is not available")
            lib.espeak_SetParameter(1, 155, 0)  # espeakRATE (words per minute)
            self._chunks = []
            data = text.encode("utf-8") + b"\0"
            buf = ctypes.create_string_buffer(data)
            lib.espeak_Synth(buf, len(data), 0, 1, 0, 1, None, None)  # POS_CHARACTER, espeakCHARS_UTF8
            lib.espeak_Synchronize()
            samples = np.concatenate(self._chunks) if self._chunks else np.zeros(1, dtype=np.float32)
            return samples, self.sample_rate


# --------------------------------------------------------------------------- manager

class TTSManager:
    def __init__(self, kokoro_dir: Path, cache_dir: Path):
        self.cache_dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.espeak = EspeakEngine()
        self.kokoro = KokoroEngine(kokoro_dir, cache_dir)

    def reload_kokoro(self, folder: Path) -> None:
        self.kokoro = KokoroEngine(folder, self.cache_dir)

    def voices(self) -> list[dict[str, Any]]:
        return [v.to_dict() for v in self.kokoro.voices() + self.espeak.voices()]

    def default_voice(self) -> str:
        kv = self.kokoro.voices()
        if kv:
            return next((v.id for v in kv if v.name == "af_heart"), kv[0].id)
        ev = self.espeak.voices()
        return ev[0].id if ev else ""

    def status(self) -> dict[str, Any]:
        return {"kokoro": self.kokoro.status(), "espeak": self.espeak.status(), "default_voice": self.default_voice(),
                "voice_count": len(self.voices())}

    def synthesize(self, voice_id: str, text: str) -> tuple[bytes, float]:
        engine_name, _, voice = (voice_id or "").partition(":")
        text = speakable(text)
        if not text:
            raise ValueError("Nothing to read.")
        engine = {"kokoro": self.kokoro, "espeak": self.espeak}.get(engine_name)
        if engine is None:
            raise ValueError(f"Unknown voice '{voice_id}'.")
        if engine_name == "kokoro" and voice not in self.kokoro.voice_names:
            raise ValueError(f"Kokoro voice '{voice}' is not installed.")
        key = hashlib.sha1(f"{engine_name}|{voice}|{getattr(engine, 'model_path', '')}|{text}".encode()).hexdigest()
        path = self.cache_dir / key[:2] / f"{key}.wav"
        if path.exists():
            data = path.read_bytes()
            return data, wav_duration(data)
        samples, sr = engine.synthesize(voice, text)
        # A short silence at the end gives natural spacing between verses.
        samples = np.concatenate([samples, np.zeros(int(sr * 0.25), dtype=np.float32)])
        data = to_wav(samples, sr)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        return data, wav_duration(data)

    def clear_cache(self) -> int:
        n = 0
        for p in self.cache_dir.rglob("*.wav"):
            try:
                p.unlink()
                n += 1
            except OSError:
                pass
        return n
