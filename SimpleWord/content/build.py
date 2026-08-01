#!/usr/bin/env python3
"""Build bible.sqlite for the Simple Word app from the raw sources.

Input:  sources/ (produced by fetch_sources.py) and data/ (curated files
        maintained in this repository).
Output: output/bible.sqlite — the read-only database bundled in the app.

Run integrity_check.py against the output before shipping it.
"""

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Canonical book table: (number, name, short_name, testament, chapters, osis)
# Chapter counts follow the shared Protestant 66-book canon; all four bundled
# translations use it.
# ---------------------------------------------------------------------------
BOOKS = [
    (1, "Genesis", "Gen", "OT", 50, "Gen"),
    (2, "Exodus", "Exo", "OT", 40, "Exod"),
    (3, "Leviticus", "Lev", "OT", 27, "Lev"),
    (4, "Numbers", "Num", "OT", 36, "Num"),
    (5, "Deuteronomy", "Deu", "OT", 34, "Deut"),
    (6, "Joshua", "Jos", "OT", 24, "Josh"),
    (7, "Judges", "Jdg", "OT", 21, "Judg"),
    (8, "Ruth", "Rut", "OT", 4, "Ruth"),
    (9, "1 Samuel", "1Sa", "OT", 31, "1Sam"),
    (10, "2 Samuel", "2Sa", "OT", 24, "2Sam"),
    (11, "1 Kings", "1Ki", "OT", 22, "1Kgs"),
    (12, "2 Kings", "2Ki", "OT", 25, "2Kgs"),
    (13, "1 Chronicles", "1Ch", "OT", 29, "1Chr"),
    (14, "2 Chronicles", "2Ch", "OT", 36, "2Chr"),
    (15, "Ezra", "Ezr", "OT", 10, "Ezra"),
    (16, "Nehemiah", "Neh", "OT", 13, "Neh"),
    (17, "Esther", "Est", "OT", 10, "Esth"),
    (18, "Job", "Job", "OT", 42, "Job"),
    (19, "Psalms", "Psa", "OT", 150, "Ps"),
    (20, "Proverbs", "Pro", "OT", 31, "Prov"),
    (21, "Ecclesiastes", "Ecc", "OT", 12, "Eccl"),
    (22, "Song of Solomon", "Sng", "OT", 8, "Song"),
    (23, "Isaiah", "Isa", "OT", 66, "Isa"),
    (24, "Jeremiah", "Jer", "OT", 52, "Jer"),
    (25, "Lamentations", "Lam", "OT", 5, "Lam"),
    (26, "Ezekiel", "Ezk", "OT", 48, "Ezek"),
    (27, "Daniel", "Dan", "OT", 12, "Dan"),
    (28, "Hosea", "Hos", "OT", 14, "Hos"),
    (29, "Joel", "Jol", "OT", 3, "Joel"),
    (30, "Amos", "Amo", "OT", 9, "Amos"),
    (31, "Obadiah", "Oba", "OT", 1, "Obad"),
    (32, "Jonah", "Jon", "OT", 4, "Jonah"),
    (33, "Micah", "Mic", "OT", 7, "Mic"),
    (34, "Nahum", "Nam", "OT", 3, "Nah"),
    (35, "Habakkuk", "Hab", "OT", 3, "Hab"),
    (36, "Zephaniah", "Zep", "OT", 3, "Zeph"),
    (37, "Haggai", "Hag", "OT", 2, "Hag"),
    (38, "Zechariah", "Zec", "OT", 14, "Zech"),
    (39, "Malachi", "Mal", "OT", 4, "Mal"),
    (40, "Matthew", "Mat", "NT", 28, "Matt"),
    (41, "Mark", "Mrk", "NT", 16, "Mark"),
    (42, "Luke", "Luk", "NT", 24, "Luke"),
    (43, "John", "Jhn", "NT", 21, "John"),
    (44, "Acts", "Act", "NT", 28, "Acts"),
    (45, "Romans", "Rom", "NT", 16, "Rom"),
    (46, "1 Corinthians", "1Co", "NT", 16, "1Cor"),
    (47, "2 Corinthians", "2Co", "NT", 13, "2Cor"),
    (48, "Galatians", "Gal", "NT", 6, "Gal"),
    (49, "Ephesians", "Eph", "NT", 6, "Eph"),
    (50, "Philippians", "Php", "NT", 4, "Phil"),
    (51, "Colossians", "Col", "NT", 4, "Col"),
    (52, "1 Thessalonians", "1Th", "NT", 5, "1Thess"),
    (53, "2 Thessalonians", "2Th", "NT", 3, "2Thess"),
    (54, "1 Timothy", "1Ti", "NT", 6, "1Tim"),
    (55, "2 Timothy", "2Ti", "NT", 4, "2Tim"),
    (56, "Titus", "Tit", "NT", 3, "Titus"),
    (57, "Philemon", "Phm", "NT", 1, "Phlm"),
    (58, "Hebrews", "Heb", "NT", 13, "Heb"),
    (59, "James", "Jas", "NT", 5, "Jas"),
    (60, "1 Peter", "1Pe", "NT", 5, "1Pet"),
    (61, "2 Peter", "2Pe", "NT", 3, "2Pet"),
    (62, "1 John", "1Jn", "NT", 5, "1John"),
    (63, "2 John", "2Jn", "NT", 1, "2John"),
    (64, "3 John", "3Jn", "NT", 1, "3John"),
    (65, "Jude", "Jud", "NT", 1, "Jude"),
    (66, "Revelation", "Rev", "NT", 22, "Rev"),
]

BOOK_BY_OSIS = {b[5]: b[0] for b in BOOKS}
BOOK_BY_NUMBER = {b[0]: b for b in BOOKS}

# Names as they appear in the scrollmapper JSON, where they differ from ours
# ("I Samuel" ordinals are normalised in normalize_book_name below).
SCROLLMAPPER_NAME_FIXES = {
    "Revelation of John": "Revelation",
}
BOOK_BY_NAME = {b[1]: b[0] for b in BOOKS}


def normalize_book_name(name: str) -> str:
    name = SCROLLMAPPER_NAME_FIXES.get(name, name)
    for roman, arabic in [("III ", "3 "), ("II ", "2 "), ("I ", "1 ")]:
        if name.startswith(roman):
            return arabic + name[len(roman):]
    return name

# TehShrike WEB book slugs, in canonical order.
WEB_SLUGS = [
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

TRANSLATIONS = [
    # (code, name, license, year, is_default)
    ("BBE", "Bible in Basic English", "Public Domain", 1949, 1),
    ("WEB", "World English Bible", "Public Domain", 2000, 0),
    ("BSB", "Berean Standard Bible", "Public Domain (CC0)", 2023, 0),
    ("KJV", "King James Version", "Public Domain (US)", 1769, 0),
]

# Book-name aliases accepted when parsing hymn scripture references
# (%OHSCRIP lines from the Open Hymnal ABC files).
HYMN_REF_ALIASES = {
    "gen": 1, "ex": 2, "exod": 2, "lev": 3, "num": 4, "deut": 5, "dt": 5,
    "josh": 6, "judg": 7, "ruth": 8, "1sam": 9, "2sam": 10, "1kgs": 11,
    "1kings": 11, "2kgs": 12, "2kings": 12, "1chr": 13, "2chr": 14,
    "ezra": 15, "neh": 16, "esth": 17, "job": 18, "ps": 19, "psa": 19,
    "psalm": 19, "psalms": 19, "prov": 20, "eccl": 21, "song": 22,
    "sos": 22, "isa": 23, "is": 23, "jer": 24, "lam": 25, "ezek": 26,
    "dan": 27, "hos": 28, "joel": 29, "amos": 30, "obad": 31, "jonah": 32,
    "mic": 33, "nah": 34, "hab": 35, "zeph": 36, "hag": 37, "zech": 38,
    "mal": 39, "matt": 40, "mt": 40, "mark": 41, "mk": 41, "luke": 42,
    "lk": 42, "john": 43, "jn": 43, "acts": 44, "rom": 45, "1cor": 46,
    "2cor": 47, "gal": 48, "eph": 49, "phil": 50, "php": 50, "col": 51,
    "1thess": 52, "2thess": 53, "1tim": 54, "2tim": 55, "titus": 56,
    "tit": 56, "phlm": 57, "philem": 57, "heb": 58, "jas": 59,
    "james": 59, "1pet": 60, "2pet": 61, "1jn": 62, "1john": 62,
    "2jn": 63, "2john": 63, "3jn": 64, "3john": 64, "jude": 65, "rev": 66,
}


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE translations (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    license TEXT NOT NULL,
    year INTEGER,
    is_default INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE books (
    id INTEGER PRIMARY KEY,
    translation_id INTEGER NOT NULL REFERENCES translations(id),
    number INTEGER NOT NULL,
    name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    testament TEXT NOT NULL CHECK (testament IN ('OT', 'NT')),
    chapter_count INTEGER NOT NULL
);
CREATE TABLE chapters (
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id),
    number INTEGER NOT NULL,
    verse_count INTEGER NOT NULL
);
CREATE TABLE verses (
    id INTEGER PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    number INTEGER NOT NULL,
    text TEXT NOT NULL
);
CREATE VIRTUAL TABLE verses_fts USING fts5(
    text,
    content='verses',
    content_rowid='id',
    tokenize='porter unicode61'
);
CREATE TABLE cross_refs (
    from_verse_id INTEGER NOT NULL REFERENCES verses(id),
    to_book INTEGER NOT NULL,
    to_chapter INTEGER NOT NULL,
    to_verse_start INTEGER NOT NULL,
    to_verse_end INTEGER,
    votes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE commentary (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    book_id INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    verse_start INTEGER NOT NULL,
    verse_end INTEGER,
    body TEXT NOT NULL
);
CREATE TABLE dictionary (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    term TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE reading_plans (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    day_count INTEGER NOT NULL
);
CREATE TABLE reading_plan_days (
    plan_id INTEGER NOT NULL REFERENCES reading_plans(id),
    day_number INTEGER NOT NULL,
    ref_list TEXT NOT NULL,
    PRIMARY KEY (plan_id, day_number)
);
CREATE TABLE hymns (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    year INTEGER,
    meter TEXT,
    lyrics TEXT NOT NULL,
    license TEXT NOT NULL,
    audio_filename TEXT,
    external_url TEXT,
    scripture_refs TEXT
);
CREATE TABLE liturgy_templates (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    tradition TEXT NOT NULL,
    structure_json TEXT NOT NULL
);
CREATE TABLE verse_of_the_day (
    day_index INTEGER PRIMARY KEY,
    verse_ref TEXT NOT NULL
);
CREATE INDEX idx_books_translation_number ON books(translation_id, number);
CREATE INDEX idx_chapters_book_number ON chapters(book_id, number);
CREATE INDEX idx_verses_chapter_number ON verses(chapter_id, number);
CREATE INDEX idx_cross_refs_from ON cross_refs(from_verse_id);
CREATE INDEX idx_commentary_lookup ON commentary(source, book_id, chapter);
CREATE INDEX idx_dictionary_term ON dictionary(term);
"""


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Translation loading
# ---------------------------------------------------------------------------
def load_scrollmapper(path: Path) -> dict:
    """Return {book_number: {chapter: {verse: text}}}."""
    data = json.load(open(path, encoding="utf-8"))
    out = {}
    for book in data["books"]:
        number = BOOK_BY_NAME[normalize_book_name(book["name"])]
        chapters = {}
        for ch in book["chapters"]:
            verses = {}
            for v in ch["verses"]:
                text = clean_text(v["text"])
                if text:
                    verses[int(v["verse"])] = text
            if verses:
                chapters[int(ch["chapter"])] = verses
        out[number] = chapters
    return out


def load_web(web_dir: Path) -> dict:
    """Return {book_number: {chapter: {verse: text}}} for the WEB."""
    out = {}
    for number, slug in enumerate(WEB_SLUGS, start=1):
        items = json.load(open(web_dir / f"{slug}.json", encoding="utf-8"))
        chapters = {}
        for item in items:
            if item.get("type") not in ("paragraph text", "line text"):
                continue
            ch = int(item["chapterNumber"])
            v = int(item["verseNumber"])
            chapters.setdefault(ch, {}).setdefault(v, []).append(item["value"])
        out[number] = {
            ch: {v: clean_text(" ".join(parts)) for v, parts in verses.items()}
            for ch, verses in chapters.items()
        }
        # Drop verses that end up empty after cleaning.
        for ch in list(out[number]):
            out[number][ch] = {
                v: t for v, t in out[number][ch].items() if t
            }
    return out


def insert_translation(cur, translation_id, code, name, license_, year,
                       is_default, books_data) -> None:
    cur.execute(
        "INSERT INTO translations (id, code, name, license, year, is_default)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (translation_id, code, name, license_, year, is_default),
    )
    for number, bname, short, testament, _canonical, _osis in BOOKS:
        chapters = books_data.get(number)
        if not chapters:
            raise RuntimeError(f"{code}: missing book {bname}")
        cur.execute(
            "INSERT INTO books (translation_id, number, name, short_name,"
            " testament, chapter_count) VALUES (?, ?, ?, ?, ?, ?)",
            (translation_id, number, bname, short, testament, len(chapters)),
        )
        book_id = cur.lastrowid
        for ch_number in sorted(chapters):
            verses = chapters[ch_number]
            cur.execute(
                "INSERT INTO chapters (book_id, number, verse_count)"
                " VALUES (?, ?, ?)",
                (book_id, ch_number, max(verses)),
            )
            chapter_id = cur.lastrowid
            cur.executemany(
                "INSERT INTO verses (chapter_id, number, text)"
                " VALUES (?, ?, ?)",
                [(chapter_id, v, verses[v]) for v in sorted(verses)],
            )


# ---------------------------------------------------------------------------
# Cross references (openbible.info dataset, TSK-derived; OSIS refs)
# ---------------------------------------------------------------------------
OSIS_REF = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$")


def parse_osis_ref(ref: str):
    m = OSIS_REF.match(ref)
    if not m:
        return None
    book = BOOK_BY_OSIS.get(m.group(1))
    if book is None:
        return None
    return book, int(m.group(2)), int(m.group(3))


def insert_cross_refs(cur, path: Path, default_translation_id: int) -> dict:
    # verse lookup for the default translation: (book, ch, v) -> verse_id
    cur.execute(
        """SELECT b.number, c.number, v.number, v.id
           FROM verses v
           JOIN chapters c ON v.chapter_id = c.id
           JOIN books b ON c.book_id = b.id
           WHERE b.translation_id = ?""",
        (default_translation_id,),
    )
    verse_ids = {(b, c, v): vid for b, c, v, vid in cur.fetchall()}
    max_verse = {}
    for (b, c, v) in verse_ids:
        max_verse[(b, c)] = max(max_verse.get((b, c), 0), v)

    stats = {"inserted": 0, "dropped_from": 0, "dropped_to": 0, "bad": 0}
    rows = []
    with open(path, encoding="utf-8") as f:
        next(f)  # header
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                stats["bad"] += 1
                continue
            from_ref, to_ref, votes = parts[0], parts[1], parts[2]
            frm = parse_osis_ref(from_ref)
            if frm is None or frm not in verse_ids:
                stats["dropped_from"] += 1
                continue
            if "-" in to_ref:
                start_s, end_s = to_ref.split("-", 1)
                start = parse_osis_ref(start_s)
                end = parse_osis_ref(end_s)
                if (start is None or end is None
                        or start[:2] != end[:2] or end[2] < start[2]):
                    stats["dropped_to"] += 1
                    continue
                to_book, to_ch, to_v1 = start
                to_v2 = end[2]
            else:
                to = parse_osis_ref(to_ref)
                if to is None:
                    stats["dropped_to"] += 1
                    continue
                to_book, to_ch, to_v1 = to
                to_v2 = None
            # The target must resolve in the default translation. Clamp a
            # range end that runs past the chapter; drop unresolvable starts.
            if (to_book, to_ch, to_v1) not in verse_ids:
                stats["dropped_to"] += 1
                continue
            if to_v2 is not None:
                to_v2 = min(to_v2, max_verse[(to_book, to_ch)])
                if to_v2 <= to_v1:
                    to_v2 = None
            try:
                votes_n = int(votes)
            except ValueError:
                votes_n = 0
            rows.append(
                (verse_ids[frm], to_book, to_ch, to_v1, to_v2, votes_n)
            )
    cur.executemany(
        "INSERT INTO cross_refs (from_verse_id, to_book, to_chapter,"
        " to_verse_start, to_verse_end, votes) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    stats["inserted"] = len(rows)
    return stats


# ---------------------------------------------------------------------------
# Dictionaries (Easton 1897, Smith 1863)
# ---------------------------------------------------------------------------
def insert_dictionaries(cur, dict_dir: Path) -> dict:
    stats = {}
    for source_dir, source_name in [("easton", "Easton's Bible Dictionary"),
                                    ("smith", "Smith's Bible Dictionary")]:
        n = 0
        for letter_file in sorted((dict_dir / source_dir).glob("*.json")):
            entries = json.load(open(letter_file, encoding="utf-8"))
            for entry in entries.values():
                term = clean_text(entry["name"])
                body = "\n\n".join(
                    d["text"].strip()
                    for d in entry.get("definitions", [])
                    if d.get("text", "").strip()
                )
                if term and body:
                    cur.execute(
                        "INSERT INTO dictionary (source, term, body)"
                        " VALUES (?, ?, ?)",
                        (source_name, term, body),
                    )
                    n += 1
        stats[source_name] = n
    return stats


# ---------------------------------------------------------------------------
# Hymns (Open Hymnal Project ABC files)
# ---------------------------------------------------------------------------
def _dehyphenate(tokens):
    """Join ABC lyric syllable tokens into words."""
    words = []
    pending = ""
    for tok in tokens:
        if tok in ("*", "|", "_", "-"):
            continue
        tok = tok.replace("~", " ")
        # Strip leading verse-number markers like "1." (kept by caller).
        if tok.endswith("-"):
            pending += tok[:-1]
        else:
            words.append(pending + tok)
            pending = ""
    if pending:
        words.append(pending)
    text = " ".join(words)
    text = re.sub(r"\s+", " ", text).strip()
    return text


VERSE_NUM = re.compile(r"^(\d+)\.\s*")


def read_abc(path: Path) -> str:
    """Open Hymnal files are a mix of UTF-8 and ISO-8859-1."""
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def parse_abc_hymn(path: Path):
    """Parse one Open Hymnal ABC file into hymn metadata + structured lyrics.

    Returns None when the lyric structure cannot be reconstructed cleanly.
    """
    meta = {"title": None, "author": None, "year": None, "meter": None,
            "scrip": None}
    w_lines, big_w_lines, c_lines = [], [], []
    for raw in read_abc(path).splitlines():
        line = raw.rstrip("\n")
        if line.startswith("%OHAUTHOR"):
            meta["author"] = line.split(None, 1)[1].strip() if " " in line else None
        elif line.startswith("%OHMETRICAL"):
            meta["meter"] = line.split(None, 1)[1].strip() if " " in line else None
        elif line.startswith("%OHSCRIP"):
            meta["scrip"] = line.split(None, 1)[1].strip() if " " in line else None
        elif line.startswith("T:") and meta["title"] is None:
            meta["title"] = line[2:].strip()
        elif line.startswith("C:"):
            c_lines.append(line[2:].strip())
        elif line.startswith("w:"):
            w_lines.append(line[2:].strip())
        elif line.startswith("W:"):
            big_w_lines.append(line[2:].strip())

    if not meta["title"] or not w_lines:
        return None

    # Year: first plausible year in a "Words: ..." credit line.
    for c in c_lines:
        if c.lower().startswith("words"):
            m = re.search(r"\b(1[0-9]{3}|20[0-2][0-9])\b", c)
            if m:
                meta["year"] = int(m.group(1))
            break

    # Reconstruct interleaved verses. The first system of w: lines opens
    # with "1.", "2.", ... — that count is the verse count; every system
    # then carries the verses in the same order.
    n_verses = 0
    for line in w_lines:
        m = VERSE_NUM.match(line.replace("~", " ").lstrip())
        if m and int(m.group(1)) == n_verses + 1:
            n_verses += 1
        else:
            break
    if n_verses == 0:
        return None
    # Trailing lines beyond a whole number of verse systems carry the
    # refrain/chorus (sung once, after the interleaved verse lines).
    remainder = len(w_lines) % n_verses
    chorus_lines = w_lines[len(w_lines) - remainder:] if remainder else []
    verse_lines = w_lines[:len(w_lines) - remainder]

    verses = [[] for _ in range(n_verses)]
    for i, line in enumerate(verse_lines):
        verse_idx = i % n_verses
        stripped = VERSE_NUM.sub("", line.replace("~", " ").lstrip(), count=1)
        text = _dehyphenate(stripped.split())
        if text:
            verses[verse_idx].append(text)
    verse_texts = [" ".join(parts) for parts in verses]
    chorus = _dehyphenate(
        " ".join(chorus_lines).replace("~", " ").split()
    ) if chorus_lines else None
    if any(not t for t in verse_texts):
        return None
    # Sanity: interleaving errors produce wildly uneven verse lengths.
    lengths = [len(t) for t in verse_texts]
    if max(lengths) > 2.2 * min(lengths):
        return None

    # Extra verses from W: blocks (plain text, blank-line separated).
    extra, current = [], []
    for line in big_w_lines:
        if not line.strip():
            if current:
                extra.append(" ".join(current))
                current = []
            continue
        current.append(VERSE_NUM.sub("", line.strip(), count=1))
    if current:
        extra.append(" ".join(current))
    for block in extra:
        block = clean_text(block)
        if block:
            verse_texts.append(block)

    return meta, verse_texts, chorus


def parse_hymn_scrip_refs(scrip: str):
    """Parse an %OHSCRIP line ("Jn 9:25, Eph 2:4-9") into stable refs."""
    if not scrip:
        return []
    refs = []
    for part in scrip.split(","):
        m = re.match(
            r"^\s*([1-3]?\s*[A-Za-z]+)\s+(\d+):(\d+)(?:-(\d+))?\s*$", part
        )
        if not m:
            continue
        key = m.group(1).replace(" ", "").lower()
        book = HYMN_REF_ALIASES.get(key)
        if book is None:
            continue
        refs.append(f"{book}.{m.group(2)}.{m.group(3)}")
    return refs


def insert_hymns(cur, hymnal_dir: Path, overrides_path: Path) -> dict:
    """Insert hymns parsed from the Open Hymnal ABC files.

    data/hymn_overrides.json (keyed by hymn directory name) supplies
    hand-checked lyrics for hymns whose scores interleave the refrain in a
    way the automatic parser cannot reconstruct faithfully.
    """
    overrides = {}
    if overrides_path.exists():
        overrides = json.load(open(overrides_path, encoding="utf-8"))

    stats = {"parsed": 0, "overridden": 0, "skipped": 0}
    seen_titles = set()
    for hymn_dir in sorted((hymnal_dir / "Complete").iterdir()):
        if not hymn_dir.is_dir():
            continue

        override = overrides.get(hymn_dir.name)
        parsed = None
        for abc in sorted(hymn_dir.glob("*.abc")):
            parsed = parse_abc_hymn(abc)
            if parsed:
                break

        if override:
            meta = {
                "title": override["title"],
                "author": override.get("author")
                or (parsed[0]["author"] if parsed else None),
                "year": override.get("year")
                or (parsed[0]["year"] if parsed else None),
                "meter": override.get("meter")
                or (parsed[0]["meter"] if parsed else None),
                "scrip": override.get("scrip")
                or (parsed[0]["scrip"] if parsed else None),
            }
            verse_texts = override["verses"]
            chorus = override.get("chorus")
            stats["overridden"] += 1
        elif parsed:
            meta, verse_texts, chorus = parsed
        else:
            stats["skipped"] += 1
            continue

        if meta["title"].lower() in seen_titles:
            continue
        seen_titles.add(meta["title"].lower())
        lyrics_obj = {"verses": verse_texts}
        if chorus:
            lyrics_obj["chorus"] = chorus
        lyrics = json.dumps(lyrics_obj, ensure_ascii=False)
        # Drop refs that don't resolve — the source data has occasional
        # typos (e.g. "1Thess 6:17"); never ship a broken reference.
        refs = []
        for ref in parse_hymn_scrip_refs(meta["scrip"]):
            b, c, v = (int(x) for x in ref.split("."))
            hit = cur.execute(
                "SELECT 1 FROM verses v2"
                " JOIN chapters c2 ON v2.chapter_id = c2.id"
                " JOIN books b2 ON c2.book_id = b2.id"
                " JOIN translations t2 ON b2.translation_id = t2.id"
                " WHERE t2.is_default = 1 AND b2.number = ?"
                "   AND c2.number = ? AND v2.number = ?",
                (b, c, v),
            ).fetchone()
            if hit:
                refs.append(ref)
            else:
                stats["dropped_refs"] = stats.get("dropped_refs", 0) + 1
        cur.execute(
            "INSERT INTO hymns (title, author, year, meter, lyrics, license,"
            " audio_filename, external_url, scripture_refs)"
            " VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?)",
            (
                meta["title"],
                meta["author"] if meta["author"] != "none" else None,
                meta["year"],
                meta["meter"],
                lyrics,
                "Public Domain (Open Hymnal Project, openhymnal.org)",
                json.dumps(refs) if refs else None,
            ),
        )
        stats["parsed"] += 1
    return stats


# ---------------------------------------------------------------------------
# Reading plans (deterministic, generated from the canon)
# ---------------------------------------------------------------------------
def chapter_refs(book: int, first: int, last: int):
    return [f"{book}.{ch}" for ch in range(first, last + 1)]


def split_evenly(refs, days):
    """Split refs into `days` contiguous groups differing by at most one."""
    n = len(refs)
    base, rem = divmod(n, days)
    out, i = [], 0
    for d in range(days):
        size = base + (1 if d < rem else 0)
        out.append(refs[i:i + size])
        i += size
    return out


def insert_reading_plans(cur) -> int:
    nt_books = [b for b in BOOKS if b[3] == "NT"]
    all_books = BOOKS

    plans = [
        (
            "Gospel of John in 21 Days",
            "One chapter of John each day for three weeks.",
            [[f"43.{ch}"] for ch in range(1, 22)],
        ),
        (
            "Psalms in 30 Days",
            "All 150 psalms in a month, five each day.",
            split_evenly(chapter_refs(19, 1, 150), 30),
        ),
        (
            "New Testament in 90 Days",
            "Every New Testament chapter in three months.",
            split_evenly(
                [r for b in nt_books for r in chapter_refs(b[0], 1, b[4])],
                90,
            ),
        ),
        (
            "Whole Bible in a Year",
            "The entire Bible in 365 days, three to four chapters a day.",
            split_evenly(
                [r for b in all_books for r in chapter_refs(b[0], 1, b[4])],
                365,
            ),
        ),
    ]
    for name, description, days in plans:
        cur.execute(
            "INSERT INTO reading_plans (name, description, day_count)"
            " VALUES (?, ?, ?)",
            (name, description, len(days)),
        )
        plan_id = cur.lastrowid
        cur.executemany(
            "INSERT INTO reading_plan_days (plan_id, day_number, ref_list)"
            " VALUES (?, ?, ?)",
            [
                (plan_id, day_number, json.dumps(refs))
                for day_number, refs in enumerate(days, start=1)
            ],
        )
    return len(plans)


# ---------------------------------------------------------------------------
# Curated data: liturgy templates, verse of the day
# ---------------------------------------------------------------------------
def insert_liturgy_templates(cur, templates_dir: Path) -> int:
    n = 0
    for f in sorted(templates_dir.glob("*.json")):
        t = json.load(open(f, encoding="utf-8"))
        cur.execute(
            "INSERT INTO liturgy_templates (name, tradition, structure_json)"
            " VALUES (?, ?, ?)",
            (t["name"], t["tradition"], json.dumps(t["structure"],
                                                  ensure_ascii=False)),
        )
        n += 1
    return n


def insert_verse_of_the_day(cur, votd_path: Path) -> int:
    refs = json.load(open(votd_path, encoding="utf-8"))
    cur.executemany(
        "INSERT INTO verse_of_the_day (day_index, verse_ref) VALUES (?, ?)",
        list(enumerate(refs)),
    )
    return len(refs)


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=str(HERE / "sources"))
    ap.add_argument("--data", default=str(HERE / "data"))
    ap.add_argument("--output", default=str(HERE / "output" / "bible.sqlite"))
    args = ap.parse_args()
    sources = Path(args.sources)
    data = Path(args.data)
    output = Path(args.output)

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    con = sqlite3.connect(output)
    cur = con.cursor()
    cur.executescript(SCHEMA)

    default_translation_id = None
    for tid, (code, name, license_, year, is_default) in enumerate(
            TRANSLATIONS, start=1):
        log(f"Loading {code}...")
        if code == "WEB":
            books_data = load_web(sources / "web")
        else:
            books_data = load_scrollmapper(sources / f"{code}.json")
        insert_translation(cur, tid, code, name, license_, year, is_default,
                           books_data)
        if is_default:
            default_translation_id = tid

    log("Building full-text index...")
    cur.execute(
        "INSERT INTO verses_fts (rowid, text) SELECT id, text FROM verses"
    )

    log("Cross references...")
    xref_stats = insert_cross_refs(
        cur, sources / "cross_references.txt", default_translation_id
    )
    log(f"  {xref_stats}")

    log("Dictionaries...")
    dict_stats = insert_dictionaries(cur, sources / "dict")
    log(f"  {dict_stats}")

    log("Hymns...")
    hymn_stats = insert_hymns(cur, sources / "openhymnal",
                              data / "hymn_overrides.json")
    log(f"  {hymn_stats}")

    log("Reading plans...")
    n_plans = insert_reading_plans(cur)
    log(f"  {n_plans} plans")

    log("Liturgy templates...")
    n_templates = insert_liturgy_templates(cur, data / "liturgy_templates")
    log(f"  {n_templates} templates")

    log("Verse of the day...")
    n_votd = insert_verse_of_the_day(cur, data / "verse_of_the_day.json")
    log(f"  {n_votd} verses")

    con.commit()
    cur.execute("INSERT INTO verses_fts(verses_fts) VALUES('optimize')")
    con.commit()
    cur.execute("VACUUM")
    con.close()
    log(f"Done: {output} ({output.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
