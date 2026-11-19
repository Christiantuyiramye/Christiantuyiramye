"""Local reading history and "what to read next" suggestions.

History is stored only in the local SQLite library and can be switched off or
cleared in Settings. Suggestions come from a small content-based model that
runs on this computer: each chapter is represented by TF-IDF weights of its
words, the user's interests are the weighted sum of the chapters they spent
time with, and unread chapters closest to that profile (cosine similarity) are
suggested, together with the shared words that explain why.
"""
from __future__ import annotations

import math
import threading
import time
from collections import Counter, defaultdict
from typing import Any

from .books import BY_NUMBER, PassageRef
from .db import Database
from .grounding import content_stems

HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS reading_history (
    id        INTEGER PRIMARY KEY,
    book      INTEGER NOT NULL,
    chapter   INTEGER NOT NULL,
    source_id INTEGER,
    mode      TEXT NOT NULL DEFAULT 'read',
    seconds   REAL NOT NULL DEFAULT 0,
    completed INTEGER NOT NULL DEFAULT 0,
    ts        REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS reading_history_ts ON reading_history(ts);
"""

STARTERS = [
    ("John 1", "The opening of John's Gospel"),
    ("Genesis 1", "The first chapter of the Bible"),
    ("Psalm 23", "A short, well-known psalm"),
    ("Luke 15", "Three parables Jesus told"),
    ("Matthew 5", "The beginning of the Sermon on the Mount"),
]


class Recommender:
    def __init__(self, db: Database):
        self.db = db
        with db.lock:
            db.conn.executescript(HISTORY_SCHEMA)
            db.conn.commit()
        self._vectors: dict[int, dict[tuple[int, int], dict[str, float]]] = {}
        self._words: dict[int, dict[tuple[int, int], Counter]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ history
    def record(self, book: int, chapter: int, source_id: int | None, mode: str, seconds: float, completed: bool) -> None:
        if book not in BY_NUMBER or chapter < 1:
            return
        self.db.execute(
            "INSERT INTO reading_history(book, chapter, source_id, mode, seconds, completed, ts) VALUES (?,?,?,?,?,?,?)",
            (book, chapter, source_id, mode[:20], max(0.0, min(float(seconds), 7200.0)), 1 if completed else 0, time.time()),
        )

    def clear(self) -> None:
        self.db.execute("DELETE FROM reading_history")

    def history(self, limit: int = 30) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT book, chapter, MAX(ts) AS last, SUM(seconds) AS seconds, MAX(completed) AS completed, COUNT(*) AS visits"
            " FROM reading_history GROUP BY book, chapter ORDER BY last DESC LIMIT ?",
            (limit,),
        )
        return [{**dict(r), "label": f"{BY_NUMBER[r['book']].name} {r['chapter']}"} for r in rows]

    # ------------------------------------------------------------------ model
    def _chapter_vectors(self, source_id: int) -> dict[tuple[int, int], dict[str, float]]:
        with self._lock:
            if source_id in self._vectors:
                return self._vectors[source_id]
            words: dict[tuple[int, int], Counter] = defaultdict(Counter)
            for r in self.db.query("SELECT book, chapter, text FROM verses WHERE source_id = ?", (source_id,)):
                words[(r["book"], r["chapter"])].update(content_stems(r["text"]))
            df: Counter = Counter()
            for c in words.values():
                df.update(c.keys())
            n = max(1, len(words))
            vectors = {}
            for key, c in words.items():
                vec = {t: (1 + math.log(tf)) * math.log(n / df[t]) for t, tf in c.items() if df[t] < n * 0.5}
                norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
                vectors[key] = {t: v / norm for t, v in vec.items()}
            self._vectors[source_id] = vectors
            self._words[source_id] = words
            return vectors

    def recommendations(self, source_id: int | None, limit: int = 6) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        hist = self.db.query("SELECT book, chapter, seconds, completed, ts FROM reading_history ORDER BY ts DESC LIMIT 400")
        if not source_id:
            return {"items": [], "basis": "none"}
        max_ch = {r["book"]: r["m"] for r in self.db.query(
            "SELECT book, MAX(chapter) AS m FROM verses WHERE source_id = ? GROUP BY book", (source_id,))}
        read = {(r["book"], r["chapter"]) for r in hist}

        def next_of(b: int, c: int) -> tuple[int, int] | None:
            if c < max_ch.get(b, 0):
                return b, c + 1
            nb = b + 1
            while nb <= 66 and nb not in max_ch:
                nb += 1
            return (nb, 1) if nb <= 66 else None

        if not hist:
            for ref, why in STARTERS:
                items.append({"reference": ref, "reason": why, "kind": "start"})
            return {"items": items[:limit], "basis": "starter"}

        last = hist[0]
        nxt = next_of(last["book"], last["chapter"])
        if nxt:
            items.append({"reference": PassageRef(nxt[0], nxt[1]).label(), "kind": "continue",
                          "reason": f"Continue after {BY_NUMBER[last['book']].name} {last['chapter']}"})

        # Books started but not finished
        started: dict[int, set[int]] = defaultdict(set)
        for r in hist:
            started[r["book"]].add(r["chapter"])
        for b, chs in sorted(started.items(), key=lambda kv: -len(kv[1])):
            total = max_ch.get(b, 0)
            if b == last["book"] or not total or len(chs) >= total:
                continue
            first_unread = next((c for c in range(1, total + 1) if c not in chs), None)
            if first_unread:
                items.append({"reference": PassageRef(b, first_unread).label(), "kind": "finish",
                              "reason": f"You've read {len(chs)} of {total} chapters of {BY_NUMBER[b].name}"})
            if len(items) >= 3:
                break

        # Content-based suggestions from time spent per chapter (recent reading counts more).
        vectors = self._chapter_vectors(source_id)
        now = time.time()
        weights: Counter = Counter()
        for r in hist:
            age_days = (now - r["ts"]) / 86400
            weights[(r["book"], r["chapter"])] += (1 + min(r["seconds"], 900) / 120 + 2 * r["completed"]) * math.exp(-age_days / 45)
        profile: Counter = Counter()
        for key, w in weights.items():
            for t, v in vectors.get(key, {}).items():
                profile[t] += w * v
        if profile:
            top_terms = dict(profile.most_common(60))
            norm = math.sqrt(sum(v * v for v in top_terms.values())) or 1.0
            scored = []
            for key, vec in vectors.items():
                if key in read:
                    continue
                s = sum(vec.get(t, 0.0) * v for t, v in top_terms.items()) / norm
                if s > 0:
                    scored.append((s, key))
            scored.sort(reverse=True)
            shown_books: Counter = Counter()
            words = self._words.get(source_id, {})
            for s, (b, c) in scored:
                if shown_books[b] >= 1 or any(i["reference"] == PassageRef(b, c).label() for i in items):
                    continue
                shared = [t for t, _ in Counter({t: vectors[(b, c)].get(t, 0) * top_terms[t] for t in top_terms}).most_common(3)
                          if vectors[(b, c)].get(t)]
                readable = self._readable_terms(words.get((b, c), Counter()), shared, source_id, b, c)
                items.append({"reference": PassageRef(b, c).label(), "kind": "similar", "score": round(s, 3),
                              "reason": "Related to what you've been reading" + (f": {', '.join(readable)}" if readable else "")})
                shown_books[b] += 1
                if len(items) >= limit:
                    break
        return {"items": items[:limit], "basis": "history"}

    def _readable_terms(self, counts: Counter, stems: list[str], source_id: int, b: int, c: int) -> list[str]:
        """Map stems back to a word as written in the chapter, for display."""
        if not stems:
            return []
        text = " ".join(r["text"] for r in self.db.query(
            "SELECT text FROM verses WHERE source_id=? AND book=? AND chapter=? LIMIT 60", (source_id, b, c)))
        from .grounding import stem

        from .grounding import words as all_words

        found = {}
        for w in all_words(text):
            s = stem(w)
            if s in stems and (s not in found or (found[s].islower() and not w.islower())):
                found[s] = w
        return [found[s] for s in stems if s in found]
