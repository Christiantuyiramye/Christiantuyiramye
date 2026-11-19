"""Optional model downloads (the only network access the app ever makes).

Downloads start only when the user clicks a Download button. Each item lists
its size, license and origin so the user can decide. Files are written to a
temporary ".part" file, checked against a SHA-256 when one is known, and then
moved into place. Users can also skip downloading entirely and point the app
at files they already have.
"""
from __future__ import annotations

import hashlib
import logging
import shutil
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

HF = "https://huggingface.co"
KOKORO_REPO = f"{HF}/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main"
KOKORO_DEFAULT_VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_aoede", "af_kore", "af_sarah", "am_michael", "am_fenrir", "am_puck",
    "bf_emma", "bf_isabella", "bm_george", "bm_fable", "bm_lewis", "bm_daniel", "af_nova", "am_echo", "am_onyx",
]

CATALOG: list[dict[str, Any]] = [
    {
        "id": "kokoro-82m-q8",
        "type": "voices",
        "title": "Kokoro-82M natural voices",
        "description": "Neural text-to-speech with 18 English voices (US and UK, female and male). Quantized 8-bit model.",
        "license": "Apache-2.0",
        "license_url": "https://huggingface.co/hexgrad/Kokoro-82M",
        "size_mb": 102,
        "origin": "huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX",
        "files": [
            {"url": f"{KOKORO_REPO}/onnx/model_quantized.onnx", "name": "model_quantized.onnx",
             "sha256": "fbae9257e1e05ffc727e951ef9b9c98418e6d79f1c9b6b13bd59f5c9028a1478"},
            *[{"url": f"{KOKORO_REPO}/voices/{v}.bin", "name": f"voices/{v}.bin"} for v in KOKORO_DEFAULT_VOICES],
        ],
        "manual": "Or download model_quantized.onnx and the voices/*.bin files yourself and choose that folder.",
    },
    {
        "id": "qwen3-4b-q4km",
        "type": "llm",
        "title": "Qwen3 4B (recommended)",
        "description": "Good balance of accuracy and speed for grounded answers and retellings. Needs ~4 GB free RAM.",
        "license": "Apache-2.0",
        "license_url": "https://huggingface.co/Qwen/Qwen3-4B",
        "size_mb": 2500,
        "origin": "huggingface.co/Qwen/Qwen3-4B-GGUF",
        "files": [{"url": f"{HF}/Qwen/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf", "name": "Qwen3-4B-Q4_K_M.gguf"}],
    },
    {
        "id": "qwen2.5-1.5b-q4km",
        "type": "llm",
        "title": "Qwen2.5 1.5B Instruct (light)",
        "description": "Smaller and faster; for older computers (~2 GB RAM). Answers are less reliable.",
        "license": "Apache-2.0",
        "license_url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct",
        "size_mb": 1120,
        "origin": "huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        "files": [{"url": f"{HF}/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
                   "name": "qwen2.5-1.5b-instruct-q4_k_m.gguf"}],
    },
    {
        "id": "qwen3-0.6b-q4km",
        "type": "llm",
        "title": "Qwen3 0.6B (tiny, testing only)",
        "description": "Very small; useful to test the app on low-memory machines. Expect many withheld answers.",
        "license": "Apache-2.0",
        "license_url": "https://huggingface.co/Qwen/Qwen3-0.6B",
        "size_mb": 397,
        "origin": "huggingface.co/unsloth/Qwen3-0.6B-GGUF",
        "files": [{"url": f"{HF}/unsloth/Qwen3-0.6B-GGUF/resolve/50968a4468ef4233ed78cd7c3de230dd1d61a56b/Qwen3-0.6B-Q4_K_M.gguf",
                   "name": "Qwen3-0.6B-Q4_K_M.gguf"}],
    },
]


def catalog_item(item_id: str) -> dict[str, Any] | None:
    return next((c for c in CATALOG if c["id"] == item_id), None)


class DownloadManager:
    def __init__(self, models_dir: Path, kokoro_dir: Path, on_complete=None):
        self.models_dir = models_dir
        self.kokoro_dir = kokoro_dir
        self.jobs: dict[str, dict[str, Any]] = {}
        self.on_complete = on_complete
        self._lock = threading.Lock()

    def target_dir(self, item: dict[str, Any]) -> Path:
        return self.kokoro_dir if item["type"] == "voices" else self.models_dir

    def installed(self, item: dict[str, Any]) -> bool:
        d = self.target_dir(item)
        return all((d / f["name"]).exists() for f in item["files"])

    def catalog(self) -> list[dict[str, Any]]:
        out = []
        for c in CATALOG:
            d = {k: v for k, v in c.items() if k != "files"}
            d["installed"] = self.installed(c)
            d["path"] = str(self.target_dir(c) / c["files"][0]["name"])
            d["file_count"] = len(c["files"])
            d["job"] = next((j for j in self.jobs.values() if j["item_id"] == c["id"] and j["state"] in ("running", "queued")), None)
            out.append(d)
        return out

    def start(self, item_id: str) -> dict[str, Any]:
        item = catalog_item(item_id)
        if not item:
            raise ValueError("Unknown download.")
        with self._lock:
            for j in self.jobs.values():
                if j["item_id"] == item_id and j["state"] in ("running", "queued"):
                    return j
            job = {"id": uuid.uuid4().hex[:10], "item_id": item_id, "title": item["title"], "state": "running",
                   "done_bytes": 0, "total_bytes": item["size_mb"] * 1_000_000, "file": "", "error": "",
                   "cancel": False, "started": time.time()}
            self.jobs[job["id"]] = job
        threading.Thread(target=self._run, args=(job, item), daemon=True, name=f"download-{item_id}").start()
        return self.public(job)

    @staticmethod
    def public(job: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in job.items() if k != "cancel"}

    def list(self) -> list[dict[str, Any]]:
        return [self.public(j) for j in self.jobs.values()]

    def cancel(self, job_id: str) -> None:
        if job_id in self.jobs:
            self.jobs[job_id]["cancel"] = True

    def _run(self, job: dict[str, Any], item: dict[str, Any]) -> None:
        target = self.target_dir(item)
        try:
            done_before = 0
            for f in item["files"]:
                dest = target / f["name"]
                job["file"] = f["name"]
                if dest.exists():
                    done_before += dest.stat().st_size
                    job["done_bytes"] = done_before
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                part = dest.with_name(dest.name + ".part")
                req = urllib.request.Request(f["url"], headers={"User-Agent": "BibleNarrator-Downloader"})
                sha = hashlib.sha256()
                with urllib.request.urlopen(req, timeout=60) as r, open(part, "wb") as out:
                    while True:
                        if job["cancel"]:
                            raise InterruptedError("Cancelled")
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        out.write(chunk)
                        sha.update(chunk)
                        job["done_bytes"] = done_before + out.tell()
                if f.get("sha256") and sha.hexdigest() != f["sha256"]:
                    part.unlink(missing_ok=True)
                    raise ValueError(f"Checksum mismatch for {f['name']}; the file was discarded.")
                done_before += part.stat().st_size
                shutil.move(str(part), str(dest))
            job["state"] = "done"
            job["done_bytes"] = job["total_bytes"] = max(job["done_bytes"], done_before)
            if self.on_complete:
                self.on_complete(item, target)
        except InterruptedError:
            job["state"] = "cancelled"
        except Exception as e:  # noqa: BLE001
            log.warning("download failed: %s", e)
            job["state"] = "error"
            msg = str(e)
            if "403" in msg or "Tunnel" in msg or "Name or service" in msg or "getaddrinfo" in msg or "urlopen error" in msg:
                msg = (f"Couldn't reach {item['origin'].split('/')[0]} ({e}). Check your internet connection, or download "
                       "the file in a browser and use “Choose file…” instead.")
            job["error"] = msg
