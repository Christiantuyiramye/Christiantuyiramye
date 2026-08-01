# Simple Word — content pipeline (Phase 0)

Builds `bible.sqlite`, the read-only database bundled in the iOS app:
four Bible translations with FTS5 search, cross-references, two Bible
dictionaries, 286 public-domain hymns, four reading plans, three Sunday
liturgy templates, and the verse-of-the-day list.

## Usage

```sh
cd SimpleWord/content
python3 fetch_sources.py          # downloads all raw sources into sources/
python3 build.py                  # sources/ + data/ -> output/bible.sqlite
python3 integrity_check.py        # acceptance gate: must report 0 errors
```

Python 3.11+ standard library only; no third-party packages. The build is
deterministic: same sources in, byte-equivalent database out (modulo SQLite
internals). `sources/` and `output/` are gitignored — the scripts are the
source of truth.

## Layout

```
content/
├── fetch_sources.py     # documented download of every raw source
├── build.py             # normalisation into the §4.1 schema
├── integrity_check.py   # 13-section verification sweep (CI-able)
├── data/                # curated files maintained in this repo
│   ├── liturgy_templates/   # standard.json, short.json, communion.json
│   ├── verse_of_the_day.json
│   └── hymn_overrides.json  # hand-checked lyrics where auto-parse falls short
├── sources/   (gitignored)
└── output/    (gitignored)  # bible.sqlite lands here
```

## Current verified build

Last full run (2026-08-01, this repository's Phase 0):

- 4 translations × 66 books; KJV at exactly 1,189 chapters / 31,102 verses
- 344,143 cross-references, every one resolving against the default (BBE) text
- Dictionary: Easton's 3,962 + Smith's 4,488 entries
- 286 hymns (3 of 289 skipped: refrain-first scores), 147 verse-of-the-day refs
- Integrity result: **0 errors**, 1 warning (commentary table empty — see
  DECISIONS.md D-004)
- Output size: 46.3 MB

## Schema

See `SCHEMA` in `build.py` — it matches the agent brief §4.1 plus two
documented extensions (`hymns.scripture_refs`, `verse_of_the_day`;
DECISIONS.md D-006). References are stored in stable numeric form
(`book.chapter.verse`, e.g. `43.3.16` = John 3:16); display strings are
rendered by the app, never stored.
