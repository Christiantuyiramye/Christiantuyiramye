"""Locations of user data and the persisted user preferences.

Everything the app stores lives in one per-user data folder (overridable with
``--data-dir`` or the ``BIBLE_NARRATOR_DATA`` environment variable):

    <data>/library.sqlite3   imported Bibles and reference books
    <data>/settings.json     preferences (voice, playback speed, model, ...)
    <data>/models/           language model (.gguf) files
    <data>/voices/kokoro/    Kokoro TTS model and voice files
    <data>/cache/audio/      synthesized audio cache (safe to delete)
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir

APP_NAME = "BibleNarrator"
APP_DISPLAY_NAME = "Bible Narrator"
APP_VERSION = "1.0.0"

PACKAGE_DIR = Path(__file__).resolve().parent
WEB_DIR = PACKAGE_DIR / "web"
STARTER_DIR = PACKAGE_DIR / "data" / "starter"

DEFAULT_SETTINGS: dict[str, Any] = {
    "onboarding_complete": False,
    # Audio
    "default_voice": "",  # e.g. "kokoro:af_heart" or "espeak:en-us"
    "playback_rate": 1.0,
    "volume": 0.9,
    "announce_passage": True,  # speak "John chapter 3" before reading
    "auto_scroll": True,
    # Reading
    "default_translation": "",  # source id of the preferred Bible
    "last_passage": "John 1",
    "font_size": 20,
    "theme": "light",  # light | dark
    "auto_continue": True,  # Auto mode: keep reading into the next chapter
    "story_visuals": True,  # coloured animated scenes while narrating
    "reduce_motion": False,
    "sleep_minutes": 30,
    "sleep_fade_seconds": 60,
    "history_enabled": True,  # local reading history for suggestions
    # Language model
    "llm_backend": "llamacpp",  # llamacpp | local_server | none
    "model_path": "",
    "local_server_url": "http://127.0.0.1:11434/v1",
    "local_server_model": "",
    "n_ctx": 8192,
    "n_threads": 0,  # 0 = automatic
    "answer_detail": "brief",  # brief | detailed
    # TTS
    "kokoro_dir": "",  # defaults to <data>/voices/kokoro
}


class Paths:
    def __init__(self, data_dir: str | os.PathLike | None = None):
        base = data_dir or os.environ.get("BIBLE_NARRATOR_DATA") or user_data_dir(APP_NAME, appauthor=False)
        self.data = Path(base).expanduser().resolve()
        self.db = self.data / "library.sqlite3"
        self.settings = self.data / "settings.json"
        self.models = self.data / "models"
        self.voices = self.data / "voices"
        self.kokoro = self.voices / "kokoro"
        self.cache = self.data / "cache"
        self.audio_cache = self.cache / "audio"
        self.downloads = self.data / "downloads"
        for d in (self.data, self.models, self.kokoro, self.audio_cache, self.downloads):
            d.mkdir(parents=True, exist_ok=True)


class Settings:
    """Small JSON-backed key/value store for user preferences."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._data = dict(DEFAULT_SETTINGS)
        if path.exists():
            try:
                stored = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(stored, dict):
                    self._data.update({k: v for k, v in stored.items() if k in DEFAULT_SETTINGS})
            except (OSError, ValueError):
                pass  # a corrupt settings file falls back to defaults

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def all(self) -> dict[str, Any]:
        return dict(self._data)

    def update(self, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            for k, v in values.items():
                if k not in DEFAULT_SETTINGS:
                    continue
                default = DEFAULT_SETTINGS[k]
                if isinstance(default, bool):
                    v = bool(v)
                elif isinstance(default, float):
                    v = float(v)
                elif isinstance(default, int):
                    v = int(v)
                elif isinstance(default, str):
                    v = "" if v is None else str(v)
                self._data[k] = v
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            tmp.replace(self.path)
            return dict(self._data)
