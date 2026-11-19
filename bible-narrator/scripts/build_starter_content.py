"""Build the public-domain starter library bundled with the app.

Usage (run once by maintainers; the output is committed under
bible_narrator/data/starter/):

    python scripts/build_starter_content.py --src <download-folder>

The download folder must contain these files (fetched with explicit URLs, see
docs/CONTENT_LICENSES.md):

    BSB.json, KJV.json, ASV.json   from github.com/scrollmapper/bible_databases (formats/json/)
    easton.json                    from github.com/robertrouse/theographic-bible-metadata (json/)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bible_narrator.importers import parse_scripture_json  # noqa: E402
from bible_narrator.library import write_starter_file  # noqa: E402

OUT = ROOT / "bible_narrator" / "data" / "starter"

BIBLES = [
    {
        "key": "bsb",
        "src": "BSB.json",
        "title": "Berean Standard Bible",
        "abbreviation": "BSB",
        "edition": "BSB (2023 public-domain release)",
        "license": "CC0 1.0 (public domain dedication)",
        "attribution": "The Holy Bible, Berean Standard Bible, BSB. Dedicated to the public domain by Bible Hub / Berean Bible (April 2023).",
        "source_url": "https://berean.bible/ (text via github.com/scrollmapper/bible_databases)",
        "notes": "Modern English translation. Section headings and footnotes are not included.",
    },
    {
        "key": "kjv",
        "src": "KJV.json",
        "title": "King James Version",
        "abbreviation": "KJV",
        "edition": "1769 Oxford edition (Blayney), 66 books",
        "license": "Public domain",
        "attribution": "King James Version (1769). Public domain in most countries; in the United Kingdom the KJV is subject to Crown letters patent held by Cambridge University Press.",
        "source_url": "https://github.com/scrollmapper/bible_databases (CrossWire KJV module, Strong's tags removed)",
        "notes": "Italicised supplied words are shown as plain text.",
    },
    {
        "key": "asv",
        "src": "ASV.json",
        "title": "American Standard Version",
        "abbreviation": "ASV",
        "edition": "1901",
        "license": "Public domain",
        "attribution": "American Standard Version (1901). Public domain.",
        "source_url": "https://github.com/scrollmapper/bible_databases",
        "notes": "",
    },
]

EASTON = {
    "key": "easton",
    "src": "easton.json",
    "kind": "dictionary",
    "title": "Easton's Bible Dictionary",
    "abbreviation": "Easton",
    "edition": "M. G. Easton, Illustrated Bible Dictionary, 3rd ed. (1897)",
    "license": "Public domain text; digital edition CC BY-SA 4.0",
    "attribution": "M. G. Easton (1897), public domain. Digitised entries from the Theographic Bible Metadata project by Robert Rouse (viz.bible), licensed CC BY-SA 4.0; this bundled copy converts the entries to plain text.",
    "source_url": "https://github.com/robertrouse/theographic-bible-metadata",
    "notes": "A 19th-century reference work. It reflects its author's views and the scholarship of its time; it is not Scripture.",
}

_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path)
    args = ap.parse_args()
    manifest = {"sources": []}
    for b in BIBLES:
        parsed = parse_scripture_json((args.src / b["src"]).read_bytes())
        assert len(parsed.rows) > 30000, (b["key"], len(parsed.rows))
        fname = f"{b['key']}.tsv.gz"
        write_starter_file(OUT / fname, parsed.rows, "scripture")
        manifest["sources"].append({"kind": "scripture", "file": fname, "language": "en", "items": len(parsed.rows),
                                    **{k: v for k, v in b.items() if k != "src"}})
        print(b["key"], len(parsed.rows), "verses")

    records = json.loads((args.src / EASTON["src"]).read_text(encoding="utf-8"))
    entries = []
    for r in records:
        f = r.get("fields", {})
        term = (f.get("termLabel") or f.get("dictLookup") or "").strip()
        text = _MD_LINK.sub(r"\1", f.get("dictText") or "").strip()
        if term and text:
            entries.append({"term": term, "text": text})
    fname = "easton.json.gz"
    write_starter_file(OUT / fname, entries, "dictionary")
    manifest["sources"].append({"file": fname, "language": "en", "items": len(entries),
                                **{k: v for k, v in EASTON.items() if k != "src"}})
    print("easton", len(entries), "entries")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
