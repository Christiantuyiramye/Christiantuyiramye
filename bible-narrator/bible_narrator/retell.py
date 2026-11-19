"""Retell a Bible passage: a short, plain narration of only what the passage says.

The model receives nothing but the passage text. Every sentence it writes
must cite verses, and is checked against those verses (names, quotations,
wording, no added morals). Sentences that fail are removed and the user is
told. If no model is installed, or the retelling fails the checks twice, a
"condensed reading" of exact key verses is offered instead and labeled as such.
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Any

from .books import BY_NUMBER, PassageRef, parse_reference
from .grounding import (
    content_stems,
    content_words,
    is_moralizing,
    support_ratio,
    unsupported_names,
    unsupported_quotes,
)
from .library import Library
from .llm import LLMManager

log = logging.getLogger(__name__)

MAX_VERSES = 80

SYSTEM_PROMPT = """You retell Bible passages in plain, simple modern English for listeners.
Strict rules:
- Include ONLY events and statements that are in the passage. Keep the order of the passage.
- Do NOT add dialogue, quotations, thoughts, feelings, motives, descriptions of people or places, weather, sounds, new characters or new names.
- Do NOT explain, interpret, or add a moral, lesson, application, introduction or conclusion.
- Do not add any other story or background knowledge.
- Use the names exactly as the passage gives them. If the passage doesn't name someone, don't name them.
- Each sentence must list the verse reference(s) it retells, written as chapter:verse (for example "3:16").
- Short, clear sentences. Reply in JSON."""


def _schema(max_sentences: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "sentences": {
                "type": "array",
                "minItems": 1,
                "maxItems": max_sentences,
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "refs": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 6},
                    },
                    "required": ["text", "refs"],
                },
            }
        },
        "required": ["sentences"],
    }


class RetellEngine:
    def __init__(self, library: Library, llm: LLMManager):
        self.library = library
        self.llm = llm

    # ------------------------------------------------------------------ lookup
    def candidates(self, query: str, source_id: int, limit: int = 5) -> list[dict[str, Any]]:
        """Find passages for an event described in words ("the parting of the Red Sea").

        Keyword search always runs. If a model is installed it may also suggest
        references; a suggestion is kept only if the passage exists in the library
        and shares words with the request, and it is labeled as a model suggestion.
        The user sees the passage text before anything is retold."""
        terms = content_words(query)
        if not terms:
            return []
        suggested: list[dict[str, Any]] = []
        if self.llm.backend is not None:
            suggested = self._model_suggestions(query, source_id)
        found = self._keyword_candidates(query, terms, source_id, limit)
        labels = {s["reference"] for s in suggested}
        return (suggested + [c for c in found if c["reference"] not in labels])[:limit]

    def _model_suggestions(self, query: str, source_id: int) -> list[dict[str, Any]]:
        schema = {"type": "object", "properties": {"references": {"type": "array", "items": {"type": "string"}, "maxItems": 3}},
                  "required": ["references"]}
        try:
            raw = self.llm.chat_json(
                [{"role": "system", "content": "You map descriptions of Bible events to passage references. Reply in JSON."},
                 {"role": "user", "content": f"Which Bible passages (book chapter:verse-verse) describe this event: {query}? "
                                             "Give at most 3 references, most relevant first."}],
                schema, max_tokens=80, temperature=0.0)
        except Exception as e:  # noqa: BLE001
            log.info("model suggestions skipped: %s", e)
            return []
        qstems = content_stems(query)
        out = []
        for r in raw.get("references", [])[:3]:
            ref = parse_reference(str(r))
            if not ref:
                continue
            verses = self.library.passage(source_id, ref)
            if not verses or len(verses) > MAX_VERSES:
                continue
            text = " ".join(v["text"] for v in verses)
            overlap = qstems & content_stems(text)
            if not overlap:
                continue  # the model's guess doesn't mention what was asked about
            first, last = verses[0], verses[-1]
            label = PassageRef(ref.book, first["chapter"], first["verse"], last["chapter"], last["verse"]).label()
            best = max(verses, key=lambda v: len(qstems & content_stems(v["text"])))
            out.append({"reference": label, "score": 1000, "snippet": best["text"],
                        "snippet_ref": f"{BY_NUMBER[ref.book].name} {best['chapter']}:{best['verse']}",
                        "origin": "model", "note": "Suggested by the AI model — check the passage before retelling."})
        return out

    def _keyword_candidates(self, query: str, terms: list[str], source_id: int, limit: int) -> list[dict[str, Any]]:
        from .retrieval import fts_query

        rows = self.library.db.query(
            "SELECT v.book, v.chapter, v.verse, v.text, bm25(verses_fts) AS score FROM verses_fts"
            " JOIN verses v ON v.id = verses_fts.rowid WHERE verses_fts MATCH ? AND v.source_id = ?"
            " ORDER BY score LIMIT 200",
            (fts_query(terms), source_id),
        )
        by_chapter: dict[tuple[int, int], list[dict[str, Any]]] = {}
        qstems = content_stems(query)
        for r in rows:
            r = dict(r)
            r["match"] = len(qstems & content_stems(r["text"]))
            by_chapter.setdefault((r["book"], r["chapter"]), []).append(r)
        scored = []
        for (b, c), hits in by_chapter.items():
            covered = set()
            for h in hits:
                covered |= qstems & content_stems(h["text"])
            score = len(covered) * 10 + sum(-h["score"] for h in hits[:5])
            hits.sort(key=lambda h: h["verse"])
            v1 = max(1, hits[0]["verse"] - 2)
            v2 = hits[-1]["verse"] + 2
            if v2 - v1 > 40:  # keep suggestions retellable
                best = max(hits, key=lambda h: (h["match"], -h["score"]))
                v1, v2 = max(1, best["verse"] - 6), best["verse"] + 8
            last = self.library.db.one("SELECT MAX(verse) AS m FROM verses WHERE source_id=? AND book=? AND chapter=?", (source_id, b, c))
            v2 = min(v2, int(last["m"] or v2))
            best = max(hits, key=lambda h: (h["match"], -h["score"]))
            ref = PassageRef(b, c, v1, c, v2)
            scored.append({"reference": ref.label(), "score": score, "snippet": best["text"],
                           "snippet_ref": f"{BY_NUMBER[b].name} {c}:{best['verse']}", "origin": "search"})
        scored.sort(key=lambda x: -x["score"])
        return scored[:limit]

    # ------------------------------------------------------------------ retell
    def retell(self, reference: str, source_id: int) -> dict[str, Any]:
        ref = parse_reference(reference)
        if not ref:
            raise ValueError("Enter a passage like “Genesis 22:1-19” or pick one of the suggestions.")
        verses = self.library.passage(source_id, ref)
        if not verses:
            raise ValueError(f"{ref.label()} wasn't found in this translation.")
        if len(verses) > MAX_VERSES:
            raise ValueError(f"{ref.label()} has {len(verses)} verses. Retell up to {MAX_VERSES} verses at a time (for example one chapter).")
        src = self.library.source(source_id) or {}
        first, last = verses[0], verses[-1]
        exact = PassageRef(ref.book, first["chapter"], first["verse"], last["chapter"], last["verse"])
        base = {
            "reference": exact.label(),
            "translation": src.get("title", ""),
            "abbreviation": src.get("abbreviation", ""),
            "license": src.get("license", ""),
            "source_id": source_id,
            "verses": verses,
        }
        if self.llm.backend is None:
            return {**base, **self.condensed(verses, exact),
                    "notes": ["AI retelling needs a local language model (Settings → Language model). "
                              "Here are exact key verses from the passage instead."]}
        result = None
        for attempt in range(2):
            try:
                result = self._ai_retell(verses, exact, temperature=0.2 if attempt == 0 else 0.0)
            except Exception as e:  # noqa: BLE001
                log.exception("retell failed")
                result = {"error": str(e)}
                break
            if result["ok"]:
                break
        if not result or not result.get("ok"):
            fallback = self.condensed(verses, exact)
            note = ("The AI retelling didn't pass the accuracy checks, so here are exact key verses instead."
                    if result and "error" not in result else f"The language model failed ({(result or {}).get('error', 'unknown error')}). "
                    "Here are exact key verses instead.")
            return {**base, **fallback, "notes": [note], "removed": (result or {}).get("removed", [])}
        notes = []
        if result["removed"]:
            notes.append(f"{len(result['removed'])} sentence(s) were removed because they weren't supported by the passage.")
        return {**base, "mode": "retelling", "sentences": result["sentences"], "removed": result["removed"], "notes": notes,
                "model": self.llm.status().get("model", "")}

    def _ai_retell(self, verses: list[dict[str, Any]], ref: PassageRef, temperature: float) -> dict[str, Any]:
        target = max(2, min(12, round(len(verses) / 2.5)))
        lines = "\n".join(f"({v['chapter']}:{v['verse']}) {v['text']}" for v in verses)
        prompt = (f"PASSAGE: {ref.label()}\n{lines}\n\n"
                  f"Retell this passage in about {target} sentences, following the rules. Reply in JSON.")
        raw = self.llm.chat_json(
            [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            _schema(target + 4), max_tokens=120 + 60 * target, temperature=temperature,
        )
        by_key = {(v["chapter"], v["verse"]): v for v in verses}
        passage_text = " ".join(v["text"] for v in verses)
        kept, removed = [], []
        produced = raw.get("sentences") or []
        for item in produced:
            if not isinstance(item, dict):
                continue
            text = re.sub(r"\s+", " ", str(item.get("text") or "")).strip()
            text = re.sub(r"\s*[\[(]\d+:\d+(?:[-–]\d+)?[\])]\s*", " ", text).strip()
            if not text or not content_words(text):
                if text:
                    removed.append({"text": text, "reason": "not a retelling sentence"})
                continue
            keys = self._parse_refs(item.get("refs") or [], ref.chapter, by_key)
            reason = self._check(text, keys, verses, by_key, passage_text)
            if reason == "recite":
                keys = self._best_verses(text, verses)
                reason = None
            if reason:
                removed.append({"text": text, "reason": reason})
                continue
            kept.append({"text": text, "refs": [f"{BY_NUMBER[ref.book].name} {c}:{v}" for c, v in keys],
                         "verse_keys": [f"{c}:{v}" for c, v in keys]})
        ok = bool(kept) and len(kept) >= max(1, math.ceil(0.6 * len(kept + removed)))
        # A retelling must be shorter than the passage; copying the text out is not a retelling.
        passage_words = len(passage_text.split())
        told_words = sum(len(k["text"].split()) for k in kept)
        if passage_words > 80 and told_words > 0.8 * passage_words:
            ok = False
            removed.append({"text": "(whole retelling)", "reason": "not concise: nearly as long as the passage itself"})
        return {"ok": ok, "sentences": kept, "removed": removed}

    @staticmethod
    def _parse_refs(refs: list[Any], chapter: int, by_key: dict) -> list[tuple[int, int]]:
        keys: list[tuple[int, int]] = []
        for r in refs:
            for m in re.finditer(r"(?:(\d+):)?(\d+)(?:\s*[-–]\s*(\d+))?", str(r)):
                c = int(m.group(1)) if m.group(1) else chapter
                a = int(m.group(2))
                b = int(m.group(3)) if m.group(3) else a
                for v in range(a, min(b, a + 30) + 1):
                    if (c, v) in by_key and (c, v) not in keys:
                        keys.append((c, v))
        return sorted(keys)

    @staticmethod
    def _best_verses(text: str, verses: list[dict[str, Any]]) -> list[tuple[int, int]]:
        stems = content_stems(text)
        scored = sorted(verses, key=lambda v: -len(stems & content_stems(v["text"])))
        best = sorted((v["chapter"], v["verse"]) for v in scored[:2])
        return best

    @staticmethod
    def _check(text: str, keys: list[tuple[int, int]], verses: list[dict[str, Any]], by_key: dict, passage_text: str) -> str | None:
        if is_moralizing(text):
            return "adds a lesson or application"
        if len(text.split()) > 45:
            return "too long for a retelling sentence"
        names = unsupported_names(text, passage_text)
        if names:
            return f"adds names not in the passage: {', '.join(names[:3])}"
        if unsupported_quotes(text, passage_text):
            return "adds quoted words that aren't in the passage"
        if keys:
            # Cited verses plus their neighbours (models often cite one verse off).
            idx = {(v["chapter"], v["verse"]): i for i, v in enumerate(verses)}
            window = set()
            for k in keys:
                i = idx[k]
                window.update(range(max(0, i - 1), min(len(verses), i + 2)))
            cited_text = " ".join(verses[i]["text"] for i in sorted(window))
            if support_ratio(text, cited_text) >= 0.55:
                return None
        if support_ratio(text, passage_text) >= 0.7:
            return "recite"
        return "wording not supported by the passage"

    # ------------------------------------------------------------------ no-model fallback
    @staticmethod
    def condensed(verses: list[dict[str, Any]], ref: PassageRef) -> dict[str, Any]:
        """Pick distinctive verses, verbatim, in order. Not a retelling - labeled as such."""
        k = max(2, min(8, round(len(verses) / 4)))
        if len(verses) <= k:
            chosen = verses
        else:
            df: Counter[str] = Counter()
            stems = [content_stems(v["text"]) for v in verses]
            for s in stems:
                df.update(s)
            n = len(verses)
            scores = []
            for i, s in enumerate(stems):
                score = sum(math.log((n + 1) / (df[t] + 0.5)) for t in s) / (1 + len(s)) ** 0.5
                if i == 0:
                    score += 5  # always start where the passage starts
                scores.append((score, i))
            idx = sorted(i for _, i in sorted(scores, reverse=True)[:k])
            chosen = [verses[i] for i in idx]
        book = BY_NUMBER[ref.book].name
        return {
            "mode": "condensed",
            "sentences": [{"text": v["text"], "refs": [f"{book} {v['chapter']}:{v['verse']}"],
                           "verse_keys": [f"{v['chapter']}:{v['verse']}"], "verbatim": True} for v in chosen],
            "removed": [],
        }
