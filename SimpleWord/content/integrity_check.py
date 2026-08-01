#!/usr/bin/env python3
"""Integrity sweep for bible.sqlite — the Phase 0 acceptance gate.

Checks (errors fail the run; warnings are reported but pass):
  1.  Four translations present; exactly one default.
  2.  66 books per translation, canonical chapter counts, both testaments.
  3.  No empty verse text anywhere.
  4.  KJV totals match the canon: 1,189 chapters and 31,102 verses.
  5.  Other translations' per-chapter verse counts stay within a small
      tolerance of the KJV (translations legitimately merge/renumber a few
      verses; large drift means a broken import).
  6.  Every cross reference resolves: from_verse_id exists, and the target
      book/chapter/verse (and range end) exists in the default translation.
  7.  Dictionary: both sources present with expected entry counts, no
      empty terms or bodies.
  8.  Commentary (when populated): every range resolves.
  9.  Hymns: minimum count, every hymn has parseable lyrics JSON with
      non-empty verses, a licence, and resolvable scripture refs.
  10. Reading plans: every ref resolves; plans cover what they claim
      (John 21/21, Psalms 150/150, full NT, full Bible).
  11. Liturgy templates: valid JSON structure; fixed refs resolve.
  12. Verse of the day: every ref resolves; no duplicates.
  13. FTS index answers queries and row count matches verses.

Usage: python3 integrity_check.py [path/to/bible.sqlite]
"""

import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

CANONICAL_CHAPTERS = {
    1: 50, 2: 40, 3: 27, 4: 36, 5: 34, 6: 24, 7: 21, 8: 4, 9: 31, 10: 24,
    11: 22, 12: 25, 13: 29, 14: 36, 15: 10, 16: 13, 17: 10, 18: 42, 19: 150,
    20: 31, 21: 12, 22: 8, 23: 66, 24: 52, 25: 5, 26: 48, 27: 12, 28: 14,
    29: 3, 30: 9, 31: 1, 32: 4, 33: 7, 34: 3, 35: 3, 36: 3, 37: 2, 38: 14,
    39: 4, 40: 28, 41: 16, 42: 24, 43: 21, 44: 28, 45: 16, 46: 16, 47: 13,
    48: 6, 49: 6, 50: 4, 51: 4, 52: 5, 53: 3, 54: 6, 55: 4, 56: 3, 57: 1,
    58: 13, 59: 5, 60: 5, 61: 3, 62: 5, 63: 1, 64: 1, 65: 1, 66: 22,
}
KJV_TOTAL_CHAPTERS = 1189
KJV_TOTAL_VERSES = 31102
VERSE_COUNT_TOLERANCE = 3  # per chapter, vs KJV
MIN_HYMNS = 100
MIN_DICT = {"Easton's Bible Dictionary": 3900, "Smith's Bible Dictionary": 4400}

errors = []
warnings = []


def err(msg):
    errors.append(msg)
    print(f"  ERROR: {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  warn:  {msg}")


def check(db: Path) -> int:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cur = con.cursor()

    print("1. Translations")
    rows = cur.execute(
        "SELECT id, code, is_default FROM translations ORDER BY id"
    ).fetchall()
    codes = [r[1] for r in rows]
    if sorted(codes) != sorted(["BBE", "WEB", "BSB", "KJV"]):
        err(f"expected BBE/WEB/BSB/KJV, got {codes}")
    defaults = [r[1] for r in rows if r[2]]
    if defaults != ["BBE"]:
        err(f"default translation should be exactly BBE, got {defaults}")
    trans_ids = {r[1]: r[0] for r in rows}
    default_id = trans_ids.get("BBE")

    print("2. Books and chapters")
    for code, tid in trans_ids.items():
        books = cur.execute(
            "SELECT number, testament, chapter_count FROM books"
            " WHERE translation_id = ? ORDER BY number", (tid,)
        ).fetchall()
        if len(books) != 66:
            err(f"{code}: {len(books)} books, expected 66")
            continue
        for number, testament, chapter_count in books:
            want = CANONICAL_CHAPTERS[number]
            if chapter_count != want:
                err(f"{code} book {number}: {chapter_count} chapters,"
                    f" canonical {want}")
            want_testament = "OT" if number <= 39 else "NT"
            if testament != want_testament:
                err(f"{code} book {number}: testament {testament}")

    print("3. Empty verses")
    n = cur.execute(
        "SELECT COUNT(*) FROM verses WHERE TRIM(text) = ''"
    ).fetchone()[0]
    if n:
        err(f"{n} empty verse rows")

    print("4. KJV canonical totals")
    kjv = trans_ids.get("KJV")
    n_ch = cur.execute(
        "SELECT COUNT(*) FROM chapters c JOIN books b ON c.book_id = b.id"
        " WHERE b.translation_id = ?", (kjv,)
    ).fetchone()[0]
    n_v = cur.execute(
        "SELECT COUNT(*) FROM verses v JOIN chapters c ON v.chapter_id = c.id"
        " JOIN books b ON c.book_id = b.id WHERE b.translation_id = ?",
        (kjv,)
    ).fetchone()[0]
    if n_ch != KJV_TOTAL_CHAPTERS:
        err(f"KJV chapters {n_ch} != {KJV_TOTAL_CHAPTERS}")
    if n_v != KJV_TOTAL_VERSES:
        err(f"KJV verses {n_v} != {KJV_TOTAL_VERSES}")

    print("5. Per-chapter verse counts vs KJV")

    def chapter_counts(tid):
        return dict(
            ((b, c), n) for b, c, n in cur.execute(
                "SELECT b.number, c.number, COUNT(v.id)"
                " FROM verses v JOIN chapters c ON v.chapter_id = c.id"
                " JOIN books b ON c.book_id = b.id"
                " WHERE b.translation_id = ? GROUP BY b.number, c.number",
                (tid,),
            )
        )

    kjv_counts = chapter_counts(kjv)
    for code in ["BBE", "WEB", "BSB"]:
        counts = chapter_counts(trans_ids[code])
        missing = set(kjv_counts) - set(counts)
        if missing:
            err(f"{code}: {len(missing)} chapters missing entirely,"
                f" e.g. {sorted(missing)[:5]}")
        drift = {
            k: (counts[k], kjv_counts[k])
            for k in counts
            if k in kjv_counts
            and abs(counts[k] - kjv_counts[k]) > VERSE_COUNT_TOLERANCE
        }
        if drift:
            sample = dict(list(drift.items())[:5])
            warn(f"{code}: {len(drift)} chapters differ from KJV by more"
                 f" than {VERSE_COUNT_TOLERANCE} verses, e.g. {sample}")

    # Verse lookup for the default translation, used by refs checks below.
    verse_set = set(
        cur.execute(
            "SELECT b.number, c.number, v.number"
            " FROM verses v JOIN chapters c ON v.chapter_id = c.id"
            " JOIN books b ON c.book_id = b.id WHERE b.translation_id = ?",
            (default_id,),
        )
    )
    default_verse_ids = set(
        r[0] for r in cur.execute(
            "SELECT v.id FROM verses v JOIN chapters c ON v.chapter_id = c.id"
            " JOIN books b ON c.book_id = b.id WHERE b.translation_id = ?",
            (default_id,),
        )
    )

    def ref_resolves(book, chapter, verse=None):
        if verse is None:
            return any(k[0] == book and k[1] == chapter for k in verse_set)
        return (book, chapter, verse) in verse_set

    print("6. Cross references")
    n_xref = cur.execute("SELECT COUNT(*) FROM cross_refs").fetchone()[0]
    if n_xref < 300000:
        err(f"only {n_xref} cross references (expected ~340k)")
    bad_from = cur.execute(
        "SELECT COUNT(*) FROM cross_refs x WHERE x.from_verse_id NOT IN"
        " (SELECT v.id FROM verses v JOIN chapters c ON v.chapter_id = c.id"
        "  JOIN books b ON c.book_id = b.id WHERE b.translation_id = ?)",
        (default_id,),
    ).fetchone()[0]
    if bad_from:
        err(f"{bad_from} cross refs with from_verse_id outside the default"
            " translation")
    bad_to = 0
    for to_book, to_ch, v1, v2 in cur.execute(
        "SELECT to_book, to_chapter, to_verse_start, to_verse_end"
        " FROM cross_refs"
    ):
        if not ref_resolves(to_book, to_ch, v1):
            bad_to += 1
        elif v2 is not None and not ref_resolves(to_book, to_ch, v2):
            bad_to += 1
    if bad_to:
        err(f"{bad_to} cross refs with unresolvable targets")

    print("7. Dictionary")
    for source, minimum in MIN_DICT.items():
        n = cur.execute(
            "SELECT COUNT(*) FROM dictionary WHERE source = ?", (source,)
        ).fetchone()[0]
        if n < minimum:
            err(f"{source}: {n} entries, expected >= {minimum}")
    n = cur.execute(
        "SELECT COUNT(*) FROM dictionary WHERE TRIM(term) = ''"
        " OR TRIM(body) = ''"
    ).fetchone()[0]
    if n:
        err(f"{n} dictionary entries with empty term or body")

    print("8. Commentary")
    n_comm = cur.execute("SELECT COUNT(*) FROM commentary").fetchone()[0]
    if n_comm == 0:
        warn("commentary table is empty (population deferred; see"
             " DECISIONS.md)")
    else:
        bad = 0
        for book_id, ch, v1, v2 in cur.execute(
            "SELECT book_id, chapter, verse_start, verse_end FROM commentary"
        ):
            if not ref_resolves(book_id, ch, v1):
                bad += 1
            elif v2 is not None and not ref_resolves(book_id, ch, v2):
                bad += 1
        if bad:
            err(f"{bad} commentary entries with unresolvable ranges")

    print("9. Hymns")
    hymns = cur.execute(
        "SELECT id, title, lyrics, license, scripture_refs FROM hymns"
    ).fetchall()
    if len(hymns) < MIN_HYMNS:
        err(f"{len(hymns)} hymns, expected >= {MIN_HYMNS}")
    for hid, title, lyrics, license_, scrip in hymns:
        try:
            parsed = json.loads(lyrics)
            verses = parsed["verses"]
            assert isinstance(verses, list) and verses
            assert all(isinstance(v, str) and v.strip() for v in verses)
        except Exception:
            err(f"hymn {hid} '{title}': malformed lyrics")
            continue
        if not license_ or not license_.strip():
            err(f"hymn {hid} '{title}': missing licence")
        if scrip:
            for ref in json.loads(scrip):
                b, c, v = (int(x) for x in ref.split("."))
                if not ref_resolves(b, c, v):
                    err(f"hymn {hid} '{title}': scripture ref {ref} does"
                        " not resolve")

    print("10. Reading plans")
    plans = cur.execute(
        "SELECT id, name, day_count FROM reading_plans"
    ).fetchall()
    if len(plans) < 4:
        err(f"{len(plans)} reading plans, expected >= 4")
    expected_coverage = {
        "Gospel of John in 21 Days": {(43, ch) for ch in range(1, 22)},
        "Psalms in 30 Days": {(19, ch) for ch in range(1, 151)},
        "New Testament in 90 Days": {
            (b, ch) for b, n in CANONICAL_CHAPTERS.items() if b >= 40
            for ch in range(1, n + 1)
        },
        "Whole Bible in a Year": {
            (b, ch) for b, n in CANONICAL_CHAPTERS.items()
            for ch in range(1, n + 1)
        },
    }
    for pid, name, day_count in plans:
        days = cur.execute(
            "SELECT day_number, ref_list FROM reading_plan_days"
            " WHERE plan_id = ? ORDER BY day_number", (pid,)
        ).fetchall()
        if len(days) != day_count:
            err(f"plan '{name}': {len(days)} day rows vs day_count"
                f" {day_count}")
        covered = set()
        for _day, ref_list in days:
            for ref in json.loads(ref_list):
                b, ch = (int(x) for x in ref.split("."))
                if not ref_resolves(b, ch):
                    err(f"plan '{name}': ref {ref} does not resolve")
                covered.add((b, ch))
        want = expected_coverage.get(name)
        if want is not None and covered != want:
            err(f"plan '{name}': coverage mismatch"
                f" ({len(covered)} vs {len(want)} chapters)")

    print("11. Liturgy templates")
    templates = cur.execute(
        "SELECT id, name, structure_json FROM liturgy_templates"
    ).fetchall()
    if len(templates) < 3:
        err(f"{len(templates)} liturgy templates, expected >= 3")
    for tid_, name, structure_json in templates:
        try:
            items = json.loads(structure_json)
            assert isinstance(items, list) and items
        except Exception:
            err(f"template '{name}': malformed structure_json")
            continue
        orders = [it.get("order") for it in items]
        if orders != sorted(orders) or len(set(orders)) != len(orders):
            err(f"template '{name}': item order values not strictly"
                " increasing")
        for it in items:
            if not it.get("kind") or not it.get("title"):
                err(f"template '{name}': item missing kind/title")
            rule = it.get("passageRule") or {}
            if rule.get("source") == "fixed":
                ref = rule["ref"]
                start, _, end = ref.partition("-")
                for r in filter(None, [start, end]):
                    b, c, v = (int(x) for x in r.split("."))
                    if not ref_resolves(b, c, v):
                        err(f"template '{name}': fixed ref {r} does not"
                            " resolve")

    print("12. Verse of the day")
    votd = [r[0] for r in cur.execute(
        "SELECT verse_ref FROM verse_of_the_day ORDER BY day_index"
    )]
    if len(votd) < 100:
        err(f"{len(votd)} verse-of-the-day entries, expected >= 100")
    if len(set(votd)) != len(votd):
        err("duplicate verse-of-the-day refs")
    for ref in votd:
        b, c, v = (int(x) for x in ref.split("."))
        if not ref_resolves(b, c, v):
            err(f"verse of the day {ref} does not resolve")

    print("13. Full-text search")
    n_fts = cur.execute("SELECT COUNT(*) FROM verses_fts").fetchone()[0]
    n_verses = cur.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    if n_fts != n_verses:
        err(f"FTS rows {n_fts} != verse rows {n_verses}")
    hits = cur.execute(
        "SELECT COUNT(*) FROM verses_fts WHERE verses_fts MATCH ?",
        ("shepherd",),
    ).fetchone()[0]
    if hits == 0:
        err("FTS query for 'shepherd' returned nothing")

    con.close()

    print()
    print(f"RESULT: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        HERE / "output" / "bible.sqlite"
    )
    if not db.exists():
        print(f"No database at {db}; run build.py first")
        sys.exit(2)
    sys.exit(check(db))
