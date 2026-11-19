"""Local HTTP API used by the desktop window.

The server only listens on 127.0.0.1 and every /api request must carry the
per-launch token, so other programs and web pages cannot read the library or
drive the app. No analytics, telemetry or remote AI calls exist anywhere.
"""
from __future__ import annotations

import logging
import re
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from platformdirs import user_downloads_dir

from .answer import AnswerEngine
from .books import BOOKS, BY_NUMBER, PassageRef, find_book, parse_reference
from .config import APP_DISPLAY_NAME, APP_VERSION, WEB_DIR, Paths, Settings
from .db import Database
from .downloads import DownloadManager
from .grounding import STOPWORDS
from .importers import ImportErrorWithHint
from .library import KINDS, LICENSE_CHOICES, Library
from .llm import LLMManager, is_loopback_url
from .recommend import Recommender
from .retell import RetellEngine
from .retrieval import Retriever
from .tts import TTSManager

log = logging.getLogger(__name__)


class AppState:
    def __init__(self, data_dir: str | None = None, install_starter: bool = True):
        self.paths = Paths(data_dir)
        self.settings = Settings(self.paths.settings)
        self.db = Database(self.paths.db)
        self.library = Library(self.db)
        if install_starter:
            first_run = not self.library.sources()
            if first_run:
                self.library.install_starter_content()
                bsb = self.db.one("SELECT id FROM sources WHERE builtin_key = 'bsb'")
                if bsb and not self.settings.get("default_translation"):
                    self.settings.update({"default_translation": str(bsb["id"])})
        self.retriever = Retriever(self.db)
        self.llm = LLMManager(self.settings)
        kokoro_dir = Path(self.settings.get("kokoro_dir") or self.paths.kokoro)
        self.tts = TTSManager(kokoro_dir, self.paths.audio_cache)
        self.answers = AnswerEngine(self.retriever, self.llm)
        self.retell = RetellEngine(self.library, self.llm)
        self.recommender = Recommender(self.db)
        self.downloads = DownloadManager(self.paths.models, self.paths.kokoro, on_complete=self._download_complete)
        if not self.settings.get("default_voice"):
            self.settings.update({"default_voice": self.tts.default_voice()})

    def _download_complete(self, item: dict[str, Any], target: Path) -> None:
        if item["type"] == "voices":
            self.settings.update({"kokoro_dir": str(target)})
            self.tts.reload_kokoro(target)
            if self.settings.get("default_voice", "").startswith("espeak:") or not self.settings.get("default_voice"):
                self.settings.update({"default_voice": self.tts.default_voice()})
        elif item["type"] == "llm":
            self.settings.update({"llm_backend": "llamacpp", "model_path": str(target / item["files"][0]["name"])})
            self.llm.configure()

    def bible_id(self, requested: Any = None) -> int:
        sid = self.library.default_scripture_id(requested or self.settings.get("default_translation"))
        if sid is None:
            raise HTTPException(400, "Your library has no Bible yet. Add one in Library.")
        return sid


def create_app(state: AppState, token: str | None = None, allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost")) -> FastAPI:
    token = token or secrets.token_urlsafe(24)
    app = FastAPI(title=APP_DISPLAY_NAME, version=APP_VERSION, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.token = token
    app.state.app_state = state

    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = (request.headers.get("host") or "").rsplit(":", 1)[0].strip("[]")
        if host not in allowed_hosts and host != "testserver":
            return JSONResponse({"detail": "Forbidden host"}, status_code=403)
        if request.url.path.startswith("/api/"):
            supplied = request.headers.get("x-app-token") or request.query_params.get("token")
            if not supplied or not secrets.compare_digest(supplied, token):
                return JSONResponse({"detail": "Missing or invalid app token"}, status_code=401)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob: data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; font-src 'self'"
        )
        return response

    s = state

    # ------------------------------------------------------------------ status & settings
    @app.get("/api/status")
    def status():
        active = [j for j in s.downloads.list() if j["state"] == "running"]
        return {
            "app": {"name": APP_DISPLAY_NAME, "version": APP_VERSION, "data_dir": str(s.paths.data)},
            "library": s.library.stats(),
            "llm": s.llm.status(),
            "tts": s.tts.status(),
            "network": {"downloading": bool(active), "telemetry": False,
                        "statement": "Offline: your library, questions and audio stay on this computer."},
            "settings": s.settings.all(),
        }

    @app.get("/api/settings")
    def get_settings():
        return s.settings.all()

    @app.put("/api/settings")
    async def put_settings(request: Request):
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(400, "Expected an object")
        if "local_server_url" in body and body["local_server_url"] and not is_loopback_url(body["local_server_url"]):
            raise HTTPException(400, "Only a model server on this computer (localhost / 127.0.0.1) can be used.")
        if "playback_rate" in body:
            body["playback_rate"] = max(0.5, min(2.5, float(body["playback_rate"])))
        if "volume" in body:
            body["volume"] = max(0.0, min(1.0, float(body["volume"])))
        if "default_voice" in body and body["default_voice"]:
            if body["default_voice"] not in {v["id"] for v in s.tts.voices()}:
                raise HTTPException(400, "That voice is not installed.")
        if body.get("history_enabled") is False:
            s.recommender.clear()
        out = s.settings.update(body)
        s.llm.configure()
        return out

    # ------------------------------------------------------------------ library
    @app.get("/api/sources")
    def sources():
        return {"sources": s.library.sources(), "kinds": list(KINDS), "licenses": LICENSE_CHOICES,
                "starter": s.library.starter_catalog()}

    @app.post("/api/sources/import")
    async def import_source(request: Request):
        q = request.query_params
        if q.get("rights_confirmed") != "1":
            raise HTTPException(400, "Please confirm you have the right to use this content.")
        filename = q.get("filename") or "upload"
        data = await request.body()
        if not data:
            raise HTTPException(400, "The file is empty.")
        if len(data) > 400 * 1024 * 1024:
            raise HTTPException(413, "Files larger than 400 MB are not supported.")
        meta = {k: q.get(k, "") for k in ("title", "abbreviation", "edition", "language", "license", "attribution", "source_url", "notes")}
        try:
            return s.library.import_file(data, filename, q.get("kind", ""), meta)
        except ImportErrorWithHint as e:
            raise HTTPException(400, str(e)) from e
        except Exception as e:  # noqa: BLE001
            log.exception("import failed")
            raise HTTPException(400, f"Could not import “{filename}”: {e}") from e

    @app.patch("/api/sources/{source_id}")
    async def update_source(source_id: int, request: Request):
        src = s.library.update_source(source_id, await request.json())
        if not src:
            raise HTTPException(404, "Source not found")
        return src

    @app.delete("/api/sources/{source_id}")
    def delete_source(source_id: int):
        if not s.library.source(source_id):
            raise HTTPException(404, "Source not found")
        s.library.delete_source(source_id)
        if str(s.settings.get("default_translation")) == str(source_id):
            s.settings.update({"default_translation": ""})
        return {"ok": True}

    @app.post("/api/starter/install")
    async def install_starter(request: Request):
        body = await request.json()
        keys = set(body.get("keys") or []) or None
        return {"installed": s.library.install_starter_content(keys)}

    # ------------------------------------------------------------------ reading
    @app.get("/api/books")
    def books(source_id: int | None = None):
        sid = s.bible_id(source_id)
        return {"source": s.library.source(sid), "books": s.library.books(sid)}

    @app.get("/api/passage")
    def passage(ref: str, source_id: int | None = None):
        r = parse_reference(ref)
        if not r:
            b = find_book(ref)
            if b:
                r = PassageRef(b.number, 1)
        if not r:
            raise HTTPException(400, f"“{ref}” isn't a passage reference. Try “John 3” or “Psalm 23:1-6”.")
        sid = s.bible_id(source_id)
        verses = s.library.passage(sid, r)
        if not verses:
            raise HTTPException(404, f"{r.label()} isn't in this translation.")
        src = s.library.source(sid)
        book = BY_NUMBER[r.book]
        first, last = verses[0], verses[-1]
        whole = r.verse is None
        label = r.label() if whole else PassageRef(r.book, first["chapter"], first["verse"], last["chapter"], last["verse"]).label()
        nchap = s.library.chapter_count(sid, r.book)
        prev_ref = next_ref = None
        if first["chapter"] > 1:
            prev_ref = f"{book.name} {first['chapter'] - 1}"
        elif r.book > 1:
            pb = BY_NUMBER[r.book - 1]
            prev_ref = f"{pb.name} {s.library.chapter_count(sid, pb.number) or 1}"
        if last["chapter"] < nchap:
            next_ref = f"{book.name} {last['chapter'] + 1}"
        elif r.book < 66:
            next_ref = f"{BY_NUMBER[r.book + 1].name} 1"
        notes = s.library.notes_for_passage(r.book, first["chapter"], r.verse, r.end_verse)
        text = " ".join(v["text"] for v in verses)
        names = []
        for m in re.finditer(r"\b([A-Z][a-z]{2,})\b", text):
            w = m.group(1)
            if w.lower() not in STOPWORDS and w not in names and w not in ("God", "Lord", "And", "But", "The", "Then", "When", "Now"):
                names.append(w)
        dictionary = s.library.dictionary_entries_for_terms(names[:40], limit=10)
        return {
            "reference": label, "book": book.number, "book_name": book.name, "chapter": first["chapter"],
            "whole_chapter": whole, "verses": verses, "source": src, "prev": prev_ref, "next": next_ref,
            "chapters_in_book": nchap, "commentary": notes, "dictionary": dictionary,
        }

    @app.get("/api/canon")
    def canon():
        return {"books": [{"number": b.number, "name": b.name, "testament": b.testament} for b in BOOKS]}

    @app.get("/api/search")
    def search(q: str, kinds: str = ""):
        if not q.strip():
            return {"scripture": [], "reference": []}
        r = parse_reference(q)
        res = s.retriever.search(q, [k for k in kinds.split(",") if k] or None)
        res["reference_match"] = r.label() if r else None
        return res

    # ------------------------------------------------------------------ AI
    @app.post("/api/ask")
    async def ask(request: Request):
        body = await request.json()
        try:
            return s.answers.ask(str(body.get("question", "")), str(body.get("detail") or s.settings.get("answer_detail")),
                                 s.library.default_scripture_id(body.get("source_id") or s.settings.get("default_translation")))
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

    @app.post("/api/retell")
    async def retell(request: Request):
        body = await request.json()
        sid = s.bible_id(body.get("source_id"))
        try:
            return s.retell.retell(str(body.get("reference", "")), sid)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

    @app.get("/api/retell/candidates")
    def retell_candidates(q: str, source_id: int | None = None):
        sid = s.bible_id(source_id)
        r = parse_reference(q)
        if r:
            return {"reference": r.label(), "candidates": []}
        return {"reference": None, "candidates": s.retell.candidates(q, sid)}

    # ------------------------------------------------------------------ voices
    @app.get("/api/voices")
    def voices():
        return {"voices": s.tts.voices(), "status": s.tts.status(), "default": s.settings.get("default_voice")}

    @app.post("/api/tts")
    async def tts(request: Request):
        body = await request.json()
        voice = str(body.get("voice") or s.settings.get("default_voice") or s.tts.default_voice())
        text = str(body.get("text") or "")[:5000]
        try:
            data, duration = s.tts.synthesize(voice, text)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        except Exception as e:  # noqa: BLE001
            log.exception("tts failed")
            raise HTTPException(500, f"Speech synthesis failed: {e}") from e
        return Response(data, media_type="audio/wav", headers={"X-Duration": f"{duration:.3f}"})

    @app.post("/api/voices/kokoro-folder")
    async def kokoro_folder(request: Request):
        body = await request.json()
        folder = Path(str(body.get("path") or "")).expanduser()
        if folder.is_file():
            folder = folder.parent
        if not folder.is_dir():
            raise HTTPException(400, "That folder doesn't exist.")
        s.tts.reload_kokoro(folder)
        if not s.tts.kokoro.installed:
            raise HTTPException(400, "No Kokoro model (.onnx) and voice files (.bin) were found in that folder.")
        s.settings.update({"kokoro_dir": str(folder)})
        if not str(s.settings.get("default_voice", "")).startswith("kokoro:"):
            s.settings.update({"default_voice": s.tts.default_voice()})
        return s.tts.status()

    @app.delete("/api/audio-cache")
    def clear_audio():
        return {"removed": s.tts.clear_cache()}

    # ------------------------------------------------------------------ models & downloads
    @app.get("/api/models/catalog")
    def models_catalog():
        local = sorted(str(p) for p in s.paths.models.glob("*.gguf"))
        return {"catalog": s.downloads.catalog(), "local_models": local, "llm": s.llm.status(),
                "models_dir": str(s.paths.models), "kokoro_dir": str(s.paths.kokoro)}

    @app.post("/api/models/use")
    async def use_model(request: Request):
        body = await request.json()
        path = Path(str(body.get("path") or "")).expanduser()
        if not path.is_file() or path.suffix.lower() != ".gguf":
            raise HTTPException(400, "Choose an existing .gguf model file.")
        with open(path, "rb") as f:
            if f.read(4) != b"GGUF":
                raise HTTPException(400, "That file is not a GGUF model.")
        s.settings.update({"llm_backend": "llamacpp", "model_path": str(path)})
        s.llm.configure()
        return s.llm.status()

    @app.post("/api/downloads")
    async def start_download(request: Request):
        body = await request.json()
        try:
            return s.downloads.start(str(body.get("id")))
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

    @app.get("/api/downloads")
    def list_downloads():
        return {"jobs": s.downloads.list()}

    @app.post("/api/downloads/{job_id}/cancel")
    def cancel_download(job_id: str):
        s.downloads.cancel(job_id)
        return {"ok": True}

    # ------------------------------------------------------------------ history & suggestions
    @app.post("/api/history")
    async def history_add(request: Request):
        if not s.settings.get("history_enabled"):
            return {"ok": False, "reason": "history disabled"}
        b = await request.json()
        s.recommender.record(int(b.get("book", 0)), int(b.get("chapter", 0)), b.get("source_id"), str(b.get("mode", "read")),
                             float(b.get("seconds", 0)), bool(b.get("completed")))
        return {"ok": True}

    @app.get("/api/history")
    def history_list():
        return {"history": s.recommender.history(), "enabled": s.settings.get("history_enabled")}

    @app.delete("/api/history")
    def history_clear():
        s.recommender.clear()
        return {"ok": True}

    @app.get("/api/recommendations")
    def recommendations():
        if not s.settings.get("history_enabled"):
            return {"items": [], "basis": "disabled"}
        sid = s.library.default_scripture_id(s.settings.get("default_translation"))
        return s.recommender.recommendations(sid)

    # ------------------------------------------------------------------ story video export
    @app.post("/api/export/video")
    async def export_video(request: Request):
        name = re.sub(r"[^\w .-]", "", request.query_params.get("name", "story"))[:80] or "story"
        ext = "mp4" if "mp4" in (request.headers.get("content-type") or "") else "webm"
        data = await request.body()
        if not data:
            raise HTTPException(400, "Empty video")
        folder = Path(user_downloads_dir()) / "Bible Narrator"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{name} {time.strftime('%Y-%m-%d %H%M%S')}.{ext}"
        path.write_bytes(data)
        return {"path": str(path)}

    # ------------------------------------------------------------------ static UI
    @app.get("/")
    def index():
        return FileResponse(WEB_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(WEB_DIR)), name="web")
    return app
