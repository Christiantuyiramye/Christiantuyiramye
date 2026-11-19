"""The user's local library: Bible translations and reference books."""
from __future__ import annotations

import gzip
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .books import BY_NUMBER, PassageRef
from .config import STARTER_DIR
from .db import Database
from .importers import (
    ImportErrorWithHint,
    ReferenceImport,
    ScriptureImport,
    guess_title,
    parse_reference,
    parse_scripture,
)

KINDS = ("scripture", "commentary", "dictionary", "reference")
KIND_LABELS = {
    "scripture": "Scripture",
    "commentary": "Commentary",
    "dictionary": "Bible dictionary",
    "reference": "Reference book",
}
LICENSE_CHOICES = [
    "Public domain",
    "CC0 1.0 (public domain dedication)",
    "CC BY 4.0",
    "CC BY-SA 4.0",
    "Licensed to me for personal use",
    "Other (see notes)",
    "Unknown",
]

SOURCE_FIELDS = ("title", "abbreviation", "edition", "language", "license", "attribution", "source_url", "notes")


class Library:
    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------ sources
    def sources(self, kind: str | None = None, enabled_only: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT * FROM sources"
        conds, params = [], []
        if kind:
            conds.append("kind = ?")
            params.append(kind)
        if enabled_only:
            conds.append("enabled = 1")
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY CASE kind WHEN 'scripture' THEN 0 WHEN 'commentary' THEN 1 WHEN 'dictionary' THEN 2 ELSE 3 END, title"
        return [self._source_dict(r) for r in self.db.query(sql, tuple(params))]

    def source(self, source_id: int) -> dict[str, Any] | None:
        r = self.db.one("SELECT * FROM sources WHERE id = ?", (source_id,))
        return self._source_dict(r) if r else None

    @staticmethod
    def _source_dict(r) -> dict[str, Any]:
        d = dict(r)
        d["enabled"] = bool(d["enabled"])
        d["builtin"] = bool(d.get("builtin_key"))
        d["kind_label"] = KIND_LABELS.get(d["kind"], d["kind"])
        d["is_scripture"] = d["kind"] == "scripture"
        return d

    def update_source(self, source_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        sets, params = [], []
        for k in SOURCE_FIELDS:
            if k in values:
                sets.append(f"{k} = ?")
                params.append(str(values[k] or "").strip())
        if "enabled" in values:
            sets.append("enabled = ?")
            params.append(1 if values["enabled"] else 0)
        if "kind" in values and values["kind"] in KINDS:
            src = self.source(source_id)
            # Scripture and reference books are stored differently; only allow
            # switching between the reference kinds.
            if src and src["kind"] != "scripture" and values["kind"] != "scripture":
                sets.append("kind = ?")
                params.append(values["kind"])
        if sets:
            params.append(source_id)
            self.db.execute(f"UPDATE sources SET {', '.join(sets)} WHERE id = ?", tuple(params))
        return self.source(source_id)

    def delete_source(self, source_id: int) -> None:
        with self.db.lock:
            c = self.db.conn
            c.execute("DELETE FROM verses WHERE source_id = ?", (source_id,))
            c.execute("DELETE FROM ref_entries WHERE source_id = ?", (source_id,))
            c.execute("DELETE FROM sources WHERE id = ?", (source_id,))
            c.commit()

    # ------------------------------------------------------------------ imports
    def import_file(self, data: bytes, filename: str, kind: str, meta: dict[str, Any]) -> dict[str, Any]:
        if kind not in KINDS:
            raise ImportErrorWithHint("Choose what kind of book this is (Scripture, commentary, dictionary or reference).")
        if kind == "scripture":
            parsed = parse_scripture(data, filename)
            return self._store_scripture(parsed, filename, meta)
        parsed_ref = parse_reference(data, filename)
        return self._store_reference(parsed_ref, filename, kind, meta)

    def _insert_source(self, kind: str, fmt: str, meta: dict[str, Any], builtin_key: str = "") -> int:
        vals = {k: str(meta.get(k) or "").strip() for k in SOURCE_FIELDS}
        if not vals["title"]:
            raise ImportErrorWithHint("Please give the source a title.")
        cur = self.db.conn.execute(
            "INSERT INTO sources(kind, title, abbreviation, edition, language, license, attribution, source_url, notes, format, builtin_key)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (kind, vals["title"], vals["abbreviation"], vals["edition"], vals["language"] or "en", vals["license"],
             vals["attribution"], vals["source_url"], vals["notes"], fmt, builtin_key),
        )
        return int(cur.lastrowid)

    def _store_scripture(self, parsed: ScriptureImport, filename: str, meta: dict[str, Any], builtin_key: str = "") -> dict[str, Any]:
        meta = dict(meta)
        if not meta.get("title"):
            title = parsed.title.split(":", 1)[-1].strip() if parsed.title else guess_title(filename)
            meta["title"] = title
        if not meta.get("abbreviation"):
            abbr = parsed.title.split(":", 1)[0].strip() if ":" in parsed.title else ""
            meta["abbreviation"] = abbr or re.sub(r"[^A-Z]", "", meta["title"].title())[:6]
        with self.db.lock:
            c = self.db.conn
            try:
                sid = self._insert_source("scripture", parsed.fmt, meta, builtin_key)
                c.executemany(
                    "INSERT OR IGNORE INTO verses(source_id, book, chapter, verse, text) VALUES (?,?,?,?,?)",
                    ((sid, b, ch, v, t) for b, ch, v, t in parsed.rows),
                )
                c.execute("UPDATE sources SET item_count = ? WHERE id = ?", (len(parsed.rows), sid))
                c.commit()
            except Exception:
                c.rollback()
                raise
        books = len({r[0] for r in parsed.rows})
        result = {"source": self.source(sid), "verses": len(parsed.rows), "books": books}
        if parsed.skipped_books:
            result["skipped"] = sorted(parsed.skipped_books)[:20]
            result["warning"] = (
                f"{len(parsed.skipped_books)} book(s) outside the 66-book canon were not imported "
                "(deuterocanonical/apocryphal books are not supported yet)."
            )
        return result

    def _store_reference(self, parsed: ReferenceImport, filename: str, kind: str, meta: dict[str, Any], builtin_key: str = "") -> dict[str, Any]:
        meta = dict(meta)
        if not meta.get("title"):
            meta["title"] = parsed.title or guess_title(filename)
        with self.db.lock:
            c = self.db.conn
            try:
                sid = self._insert_source(kind, parsed.fmt, meta, builtin_key)
                c.executemany(
                    "INSERT INTO ref_entries(source_id, heading, location, page, book, chapter, verse_start, verse_end, text)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    ((sid, e.heading, e.location, e.page, e.book, e.chapter, e.verse_start, e.verse_end, e.text) for e in parsed.entries),
                )
                c.execute("UPDATE sources SET item_count = ? WHERE id = ?", (len(parsed.entries), sid))
                c.commit()
            except Exception:
                c.rollback()
                raise
        return {"source": self.source(sid), "entries": len(parsed.entries)}

    # ------------------------------------------------------------------ starter content
    def install_starter_content(self, only: set[str] | None = None) -> list[str]:
        """Install the public-domain texts bundled with the app (once)."""
        manifest_path = STARTER_DIR / "manifest.json"
        if not manifest_path.exists():
            return []
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing = {r["builtin_key"] for r in self.db.query("SELECT builtin_key FROM sources WHERE builtin_key != ''")}
        installed = []
        for item in manifest["sources"]:
            key = item["key"]
            if key in existing or (only is not None and key not in only):
                continue
            path = STARTER_DIR / item["file"]
            if not path.exists():
                continue
            data = path.read_bytes()
            meta = {k: item.get(k, "") for k in SOURCE_FIELDS}
            if item["kind"] == "scripture":
                self._store_scripture(parse_scripture(data, item["file"]), item["file"], meta, builtin_key=key)
            else:
                self._store_reference(parse_reference(data, item["file"]), item["file"], item["kind"], meta, builtin_key=key)
            installed.append(key)
        return installed

    def starter_catalog(self) -> list[dict[str, Any]]:
        manifest_path = STARTER_DIR / "manifest.json"
        if not manifest_path.exists():
            return []
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing = {r["builtin_key"] for r in self.db.query("SELECT builtin_key FROM sources WHERE builtin_key != ''")}
        return [{**{k: v for k, v in i.items() if k != "file"}, "installed": i["key"] in existing} for i in manifest["sources"]]

    # ------------------------------------------------------------------ scripture reading
    def default_scripture_id(self, preferred: str | int | None = None) -> int | None:
        if preferred:
            try:
                r = self.db.one("SELECT id FROM sources WHERE id = ? AND kind = 'scripture'", (int(preferred),))
                if r:
                    return int(r["id"])
            except (TypeError, ValueError):
                pass
        r = self.db.one("SELECT id FROM sources WHERE kind = 'scripture' AND enabled = 1 ORDER BY id LIMIT 1")
        r = r or self.db.one("SELECT id FROM sources WHERE kind = 'scripture' ORDER BY id LIMIT 1")
        return int(r["id"]) if r else None

    def books(self, source_id: int) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT book, MAX(chapter) AS chapters FROM verses WHERE source_id = ? GROUP BY book ORDER BY book",
            (source_id,),
        )
        out = []
        for r in rows:
            b = BY_NUMBER.get(r["book"])
            if b:
                out.append({"number": b.number, "name": b.name, "osis": b.osis, "testament": b.testament, "chapters": r["chapters"]})
        return out

    def passage(self, source_id: int, ref: PassageRef) -> list[dict[str, Any]]:
        """Verses for a reference. Whole chapters if no verse was given."""
        if ref.verse is None:
            end_c = ref.end_chapter or ref.chapter
            rows = self.db.query(
                "SELECT book, chapter, verse, text FROM verses WHERE source_id = ? AND book = ? AND chapter BETWEEN ? AND ?"
                " ORDER BY chapter, verse",
                (source_id, ref.book, ref.chapter, end_c),
            )
        else:
            end_c = ref.end_chapter or ref.chapter
            end_v = ref.end_verse if ref.end_verse is not None else ref.verse
            rows = self.db.query(
                "SELECT book, chapter, verse, text FROM verses WHERE source_id = ? AND book = ?"
                " AND (chapter * 1000 + verse) BETWEEN ? AND ? ORDER BY chapter, verse",
                (source_id, ref.book, ref.chapter * 1000 + ref.verse, end_c * 1000 + end_v),
            )
        return [dict(r) for r in rows]

    def verses_by_ids(self, ids: list[int]) -> list[dict[str, Any]]:
        if not ids:
            return []
        q = ",".join("?" * len(ids))
        return [dict(r) for r in self.db.query(f"SELECT id, source_id, book, chapter, verse, text FROM verses WHERE id IN ({q})", tuple(ids))]

    def chapter_count(self, source_id: int, book: int) -> int:
        r = self.db.one("SELECT MAX(chapter) AS m FROM verses WHERE source_id = ? AND book = ?", (source_id, book))
        return int(r["m"] or 0) if r else 0

    def notes_for_passage(self, book: int, chapter: int, v1: int | None, v2: int | None, limit: int = 20) -> list[dict[str, Any]]:
        """Verse-keyed commentary entries overlapping the passage (never Scripture)."""
        v1 = v1 or 1
        v2 = v2 or 999
        rows = self.db.query(
            "SELECT e.id, e.source_id, e.heading, e.location, e.text, e.verse_start, e.verse_end, s.title, s.kind, s.license, s.edition"
            " FROM ref_entries e JOIN sources s ON s.id = e.source_id"
            " WHERE s.enabled = 1 AND e.book = ? AND e.chapter = ?"
            " AND COALESCE(e.verse_start, 1) <= ? AND COALESCE(e.verse_end, e.verse_start, 999) >= ?"
            " ORDER BY s.title, e.verse_start LIMIT ?",
            (book, chapter, v2, v1, limit),
        )
        return [dict(r) for r in rows]

    def dictionary_entries_for_terms(self, terms: list[str], limit: int = 12) -> list[dict[str, Any]]:
        if not terms:
            return []
        q = ",".join("?" * len(terms))
        rows = self.db.query(
            "SELECT e.id, e.source_id, e.heading, e.location, e.text, s.title, s.kind, s.license"
            f" FROM ref_entries e JOIN sources s ON s.id = e.source_id WHERE s.enabled = 1 AND s.kind = 'dictionary'"
            f" AND e.heading COLLATE NOCASE IN ({q}) ORDER BY e.id",
            tuple(terms),
        )
        seen: set[tuple[int, str]] = set()
        out = []
        for r in rows:  # first chunk of each article only
            key = (r["source_id"], r["heading"].lower())
            if key in seen:
                continue
            seen.add(key)
            out.append(dict(r))
        return out[:limit]

    def stats(self) -> dict[str, int]:
        r = self.db.one(
            "SELECT SUM(kind='scripture') AS scripture, SUM(kind!='scripture') AS reference, COUNT(*) AS total FROM sources"
        )
        return {k: int(r[k] or 0) for k in ("scripture", "reference", "total")}


def write_starter_file(path: Path, rows_or_entries: list, kind: str) -> None:
    """Used by scripts/build_starter_content.py to write compact bundled data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "scripture":
        lines = ["book\tchapter\tverse\ttext"] + [f"{b}\t{c}\t{v}\t{t}" for b, c, v, t in rows_or_entries]
        payload = ("\n".join(lines) + "\n").encode("utf-8")
    else:
        payload = json.dumps([asdict(e) if not isinstance(e, dict) else e for e in rows_or_entries], ensure_ascii=False).encode("utf-8")
    path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
