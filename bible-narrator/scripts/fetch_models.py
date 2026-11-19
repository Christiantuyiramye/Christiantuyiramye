"""Download the optional model files from the command line (same catalog as the app).

    python scripts/fetch_models.py --list
    python scripts/fetch_models.py kokoro-82m-q8 qwen3-4b-q4km [--data-dir DIR]

This is the only part of the project that uses the internet, and only when you
run it. Afterwards the app works fully offline.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bible_narrator.config import Paths, Settings  # noqa: E402
from bible_narrator.downloads import CATALOG, DownloadManager  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--data-dir")
    args = ap.parse_args()
    if args.list or not args.ids:
        for c in CATALOG:
            print(f"{c['id']:<20} {c['size_mb']:>5} MB  {c['license']:<11} {c['title']}  ({c['origin']})")
        return 0
    paths = Paths(args.data_dir)
    settings = Settings(paths.settings)

    def done(item, target):
        if item["type"] == "voices":
            settings.update({"kokoro_dir": str(target)})
        else:
            settings.update({"llm_backend": "llamacpp", "model_path": str(target / item["files"][0]["name"])})

    dm = DownloadManager(paths.models, paths.kokoro, on_complete=done)
    for item_id in args.ids:
        job = dm.start(item_id)
        while dm.jobs[job["id"]]["state"] == "running":
            j = dm.jobs[job["id"]]
            print(f"\r{item_id}: {j['done_bytes'] / 1e6:,.0f} / ~{j['total_bytes'] / 1e6:,.0f} MB  {j['file']:<40}", end="", flush=True)
            time.sleep(1)
        j = dm.jobs[job["id"]]
        print(f"\r{item_id}: {j['state']} {j['error']}".ljust(100))
        if j["state"] != "done":
            return 1
    print(f"Files are in {paths.data}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
