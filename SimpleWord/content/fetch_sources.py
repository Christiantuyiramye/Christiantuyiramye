#!/usr/bin/env python3
"""Download all raw content sources for the Simple Word bible.sqlite build.

Every source is public domain or freely licensed for redistribution; see
SimpleWord/CREDITS.md for the licence record of each one.

Usage:
    python3 fetch_sources.py [--dest sources]

The script is idempotent: files already present and non-empty are skipped,
so an interrupted run can simply be restarted.
"""

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com"

# scrollmapper/bible_databases (2025 schema): cleaned public-domain texts.
SCROLLMAPPER_TRANSLATIONS = ["BBE", "BSB", "KJV"]

# TehShrike/world-english-bible: WEB as one JSON file per book.
WEB_BOOK_SLUGS = [
    "genesis", "exodus", "leviticus", "numbers", "deuteronomy", "joshua",
    "judges", "ruth", "1samuel", "2samuel", "1kings", "2kings",
    "1chronicles", "2chronicles", "ezra", "nehemiah", "esther", "job",
    "psalms", "proverbs", "ecclesiastes", "songofsolomon", "isaiah",
    "jeremiah", "lamentations", "ezekiel", "daniel", "hosea", "joel",
    "amos", "obadiah", "jonah", "micah", "nahum", "habakkuk", "zephaniah",
    "haggai", "zechariah", "malachi", "matthew", "mark", "luke", "john",
    "acts", "romans", "1corinthians", "2corinthians", "galatians",
    "ephesians", "philippians", "colossians", "1thessalonians",
    "2thessalonians", "1timothy", "2timothy", "titus", "philemon",
    "hebrews", "james", "1peter", "2peter", "1john", "2john", "3john",
    "jude", "revelation",
]

# neuu-org/bible-dictionary-dataset: Easton (1897) and Smith (1863),
# parsed from CCEL ThML XML. No entries under the letter X in either work.
DICT_LETTERS = [c for c in "abcdefghijklmnopqrstuvwxyz" if c != "x"]


def fetch(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 100:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  fetching {url}")
    with urllib.request.urlopen(url, timeout=120) as resp:
        data = resp.read()
    if data.startswith(b"404"):
        raise RuntimeError(f"404 from {url}")
    dest.write_bytes(data)


def clone(repo_url: str, dest: Path) -> None:
    if dest.exists():
        return
    print(f"  cloning {repo_url}")
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(dest)], check=True
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="sources")
    args = ap.parse_args()
    dest = Path(args.dest)

    print("Translations (scrollmapper/bible_databases)...")
    for code in SCROLLMAPPER_TRANSLATIONS:
        fetch(
            f"{RAW}/scrollmapper/bible_databases/master/formats/json/{code}.json",
            dest / f"{code}.json",
        )

    print("World English Bible (TehShrike/world-english-bible)...")
    for slug in WEB_BOOK_SLUGS:
        fetch(
            f"{RAW}/TehShrike/world-english-bible/master/json/{slug}.json",
            dest / "web" / f"{slug}.json",
        )

    print("Cross references (openbible.info via scrollmapper)...")
    fetch(
        f"{RAW}/scrollmapper/bible_databases/master/sources/extras/cross_references.txt",
        dest / "cross_references.txt",
    )

    print("Dictionaries (neuu-org/bible-dictionary-dataset)...")
    for source in ["easton", "smith"]:
        for letter in DICT_LETTERS:
            fetch(
                f"{RAW}/neuu-org/bible-dictionary-dataset/main/data/02_sources/{source}/{letter}.json",
                dest / "dict" / source / f"{letter}.json",
            )

    print("Hymns (mzealey/openhymnal mirror of the Open Hymnal Project)...")
    clone("https://github.com/mzealey/openhymnal.git", dest / "openhymnal")

    # Quick sanity pass: everything must parse as JSON where expected.
    bad = []
    for f in dest.rglob("*.json"):
        if "openhymnal" in f.parts:
            continue
        try:
            json.load(open(f))
        except Exception:
            bad.append(str(f))
    if bad:
        print(f"ERROR: unparseable JSON: {bad}")
        return 1
    print("All sources fetched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
