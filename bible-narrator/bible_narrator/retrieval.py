"""Local retrieval over the library (SQLite FTS5 / BM25).

Scripture and reference books are searched separately so the answer prompt
can always label which is which. Scripture hits are expanded with their
neighbouring verses so the model sees enough context, and identical verses
from several translations are collapsed to the best-matching one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .books import BY_NUMBER, PassageRef, find_references
from .db import Database
from .grounding import STOPWORDS, content_stems, content_words
from .library import KIND_LABELS


@dataclass
class Source:
    """One numbered source passed to the model and shown to the user."""

    kind: str  # scripture | commentary | dictionary | reference
    source_id: int
    title: str  # e.g. "Berean Standard Bible" or "Easton's Bible Dictionary"
    abbreviation: str
    label: str  # e.g. "John 3:16-17" or "“Aaron” (part 2)"
    text: str
    license: str = ""
    edition: str = ""
    book: int | None = None
    chapter: int | None = None
    verse_start: int | None = None
    verse_end: int | None = None
    page: int | None = None
    score: float = 0.0
    verses: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_scripture(self) -> bool:
        return self.kind == "scripture"

    def prompt_block(self, n: int) -> str:
        if self.is_scripture:
            head = f"[{n}] SCRIPTURE — {self.label} ({self.abbreviation or self.title})"
            body = " ".join(f"({v['chapter']}:{v['verse']}) {v['text']}" for v in self.verses) if self.verses else self.text
        else:
            head = f"[{n}] {KIND_LABELS.get(self.kind, 'Reference').upper()} (not Scripture) — {self.title}, {self.label}"
            body = self.text
        return f"{head}\n{body}"

    def to_dict(self, n: int | None = None) -> dict[str, Any]:
        d = {
            "kind": self.kind,
            "kind_label": KIND_LABELS.get(self.kind, self.kind),
            "is_scripture": self.is_scripture,
            "source_id": self.source_id,
            "title": self.title,
            "abbreviation": self.abbreviation,
            "label": self.label,
            "text": self.text,
            "license": self.license,
            "edition": self.edition,
            "book": self.book,
            "chapter": self.chapter,
            "verse_start": self.verse_start,
            "verse_end": self.verse_end,
            "page": self.page,
        }
        if self.is_scripture:
            d["citation"] = f"{self.label} ({self.abbreviation or self.title})"
        else:
            d["citation"] = f"{self.title}, {self.label}" if self.label else self.title
        if n is not None:
            d["n"] = n
        return d


def fts_query(terms: list[str]) -> str:
    safe = []
    for t in terms:
        t = re.sub(r"[^\w]", "", t)
        if t and t.lower() not in ("and", "or", "not", "near"):
            safe.append(f'"{t}"')
    return " OR ".join(dict.fromkeys(safe))


class Retriever:
    def __init__(self, db: Database):
        self.db = db

    def _enabled_sources(self) -> dict[int, dict[str, Any]]:
        return {r["id"]: dict(r) for r in self.db.query("SELECT * FROM sources WHERE enabled = 1")}

    # ------------------------------------------------------------------ scripture
    def search_verses(self, terms: list[str], source_ids: list[int], limit: int = 40) -> list[dict[str, Any]]:
        q = fts_query(terms)
        if not q or not source_ids:
            return []
        marks = ",".join("?" * len(source_ids))
        rows = self.db.query(
            "SELECT v.id, v.source_id, v.book, v.chapter, v.verse, v.text, bm25(verses_fts) AS score"
            f" FROM verses_fts JOIN verses v ON v.id = verses_fts.rowid"
            f" WHERE verses_fts MATCH ? AND v.source_id IN ({marks}) ORDER BY score LIMIT ?",
            (q, *source_ids, limit),
        )
        return [dict(r) for r in rows]

    def _context(self, source_id: int, book: int, chapter: int, v1: int, v2: int) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT book, chapter, verse, text FROM verses WHERE source_id = ? AND book = ? AND chapter = ?"
            " AND verse BETWEEN ? AND ? ORDER BY verse",
            (source_id, book, chapter, v1, v2),
        )
        return [dict(r) for r in rows]

    def scripture_sources(self, question: str, extra_terms: list[str], preferred_id: int | None, limit: int = 6) -> list[Source]:
        enabled = self._enabled_sources()
        bible_ids = [i for i, s in enabled.items() if s["kind"] == "scripture"]
        if not bible_ids:
            return []
        pref = preferred_id if preferred_id in bible_ids else bible_ids[0]
        out: list[Source] = []
        seen_refs: set[tuple[int, int, int]] = set()

        # 1) References written in the question ("What does John 3:16 mean?")
        for ref in find_references(question)[:3]:
            v1 = ref.verse or 1
            v2 = ref.end_verse if ref.end_verse is not None else (ref.verse or 200)
            v2 = min(v2, v1 + 15)
            verses = self._context(pref, ref.book, ref.chapter, v1, v2)
            if verses:
                out.append(self._make_scripture(enabled[pref], verses, score=-100.0))
                seen_refs.update((v["book"], v["chapter"], v["verse"]) for v in verses)

        # 2) Keyword search across all enabled translations, collapsed by reference.
        terms = content_words(question) + [t for t in extra_terms if t.lower() not in STOPWORDS]
        hits = self.search_verses(terms, bible_ids, limit=80)
        best: dict[tuple[int, int, int], dict[str, Any]] = {}
        for h in hits:
            key = (h["book"], h["chapter"], h["verse"])
            # Prefer the user's translation when scores tie closely.
            adj = h["score"] - (0.05 if h["source_id"] == pref else 0.0)
            if key not in best or adj < best[key]["adj"]:
                best[key] = {**h, "adj": adj}
        ranked = sorted(best.values(), key=lambda h: h["adj"])
        for h in ranked:
            if len(out) >= limit:
                break
            key = (h["book"], h["chapter"], h["verse"])
            if key in seen_refs:
                continue
            verses = self._context(h["source_id"], h["book"], h["chapter"], max(1, h["verse"] - 1), h["verse"] + 1)
            seen_refs.update((v["book"], v["chapter"], v["verse"]) for v in verses)
            out.append(self._make_scripture(enabled[h["source_id"]], verses, score=h["adj"]))
        return out

    @staticmethod
    def _make_scripture(src: dict[str, Any], verses: list[dict[str, Any]], score: float) -> Source:
        b, c = verses[0]["book"], verses[0]["chapter"]
        v1, v2 = verses[0]["verse"], verses[-1]["verse"]
        ref = PassageRef(b, c, v1, c, v2)
        return Source(
            kind="scripture", source_id=src["id"], title=src["title"], abbreviation=src["abbreviation"],
            label=ref.label(), text=" ".join(v["text"] for v in verses), license=src["license"], edition=src["edition"],
            book=b, chapter=c, verse_start=v1, verse_end=v2, score=score, verses=verses,
        )

    # ------------------------------------------------------------------ reference books
    def reference_sources(self, question: str, extra_terms: list[str], limit: int = 4) -> list[Source]:
        enabled = self._enabled_sources()
        ref_ids = [i for i, s in enabled.items() if s["kind"] != "scripture"]
        if not ref_ids:
            return []
        out: list[Source] = []
        seen: set[int] = set()
        marks = ",".join("?" * len(ref_ids))
        # Dictionary articles whose heading names something in the question ("Who was Melchizedek?")
        names = [w for w in re.findall(r"\b[A-Z][a-z]{2,}\b", question) if w.lower() not in STOPWORDS]
        if names:
            nm = ",".join("?" * len(names))
            for r in self.db.query(
                f"SELECT * FROM ref_entries WHERE source_id IN ({marks}) AND heading COLLATE NOCASE IN ({nm}) ORDER BY id LIMIT 6",
                (*ref_ids, *names),
            ):
                if r["id"] not in seen and len(out) < 2:
                    seen.add(r["id"])
                    out.append(self._make_ref(enabled[r["source_id"]], dict(r), score=-50.0))
        q = fts_query(content_words(question) + [t for t in extra_terms if t.lower() not in STOPWORDS])
        if q:
            rows = self.db.query(
                "SELECT e.*, bm25(ref_fts, 4.0, 1.0) AS score FROM ref_fts JOIN ref_entries e ON e.id = ref_fts.rowid"
                f" WHERE ref_fts MATCH ? AND e.source_id IN ({marks}) ORDER BY score LIMIT 20",
                (q, *ref_ids),
            )
            for r in rows:
                if len(out) >= limit:
                    break
                if r["id"] in seen:
                    continue
                seen.add(r["id"])
                out.append(self._make_ref(enabled[r["source_id"]], dict(r), score=r["score"]))
        return out

    @staticmethod
    def _make_ref(src: dict[str, Any], e: dict[str, Any], score: float) -> Source:
        label = e.get("location") or e.get("heading") or ""
        return Source(
            kind=src["kind"], source_id=src["id"], title=src["title"], abbreviation=src["abbreviation"], label=label,
            text=e["text"], license=src["license"], edition=src["edition"], book=e.get("book"), chapter=e.get("chapter"),
            verse_start=e.get("verse_start"), verse_end=e.get("verse_end"), page=e.get("page"), score=score,
        )

    # ------------------------------------------------------------------ public API
    def retrieve(self, question: str, extra_terms: list[str] | None = None, preferred_id: int | None = None,
                 scripture_limit: int = 6, reference_limit: int = 4) -> list[Source]:
        extra_terms = extra_terms or []
        return self.scripture_sources(question, extra_terms, preferred_id, scripture_limit) + \
            self.reference_sources(question, extra_terms, reference_limit)

    @staticmethod
    def coverage(question: str, sources: list[Source]) -> float:
        """Share of the question's key words found anywhere in the retrieved sources."""
        q = content_stems(question)
        if not q:
            return 0.0
        found: set[str] = set()
        for s in sources:
            found |= content_stems(s.text) | content_stems(s.label) | content_stems(s.title)
        return len(q & found) / len(q)

    def search(self, query: str, kinds: list[str] | None = None, limit: int = 30) -> dict[str, Any]:
        """Plain library search used by the Search view (no AI involved)."""
        enabled = self._enabled_sources()
        terms = content_words(query) or [w for w in re.findall(r"\w+", query)]
        results: dict[str, Any] = {"scripture": [], "reference": []}
        if not kinds or "scripture" in kinds:
            bible_ids = [i for i, s in enabled.items() if s["kind"] == "scripture"]
            phrase = query.strip()
            hits: list[dict[str, Any]] = []
            if bible_ids and len(phrase.split()) > 1 and '"' not in phrase:
                marks = ",".join("?" * len(bible_ids))
                hits = [dict(r) for r in self.db.query(
                    "SELECT v.id, v.source_id, v.book, v.chapter, v.verse, v.text, bm25(verses_fts) AS score"
                    " FROM verses_fts JOIN verses v ON v.id = verses_fts.rowid"
                    f" WHERE verses_fts MATCH ? AND v.source_id IN ({marks}) ORDER BY score LIMIT ?",
                    ('"' + re.sub(r"[^\w\s]", "", phrase) + '"', *bible_ids, limit),
                )]
            if len(hits) < limit:
                seen = {h["id"] for h in hits}
                hits += [h for h in self.search_verses(terms, bible_ids, limit) if h["id"] not in seen]
            seen_refs: set[tuple[int, int, int]] = set()
            for h in hits:
                key = (h["book"], h["chapter"], h["verse"])
                if key in seen_refs:
                    continue  # same verse in another translation
                seen_refs.add(key)
                if len(results["scripture"]) >= limit:
                    break
                s = enabled[h["source_id"]]
                results["scripture"].append({
                    "label": f"{BY_NUMBER[h['book']].name} {h['chapter']}:{h['verse']}", "book": h["book"],
                    "chapter": h["chapter"], "verse": h["verse"], "text": h["text"], "source_id": h["source_id"],
                    "translation": s["abbreviation"] or s["title"],
                })
        if not kinds or set(kinds) - {"scripture"}:
            for src in self.reference_sources(query, [], limit=min(limit, 15)):
                results["reference"].append(src.to_dict())
        return results
