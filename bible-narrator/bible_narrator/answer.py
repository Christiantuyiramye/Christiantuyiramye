"""Ask a question: grounded answers from the local library, with citations.

Pipeline
1. Retrieve Scripture and reference passages locally (FTS5/BM25).
2. If the key words of the question are not in the library at all, stop and
   say so - no model call is made.
3. Ask the local model to answer ONLY from the numbered sources, in JSON.
4. Verify every sentence against the sources it cites (see grounding.py).
   Unsupported sentences are removed; if nothing survives, the user is told
   plainly that no answer was found.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from .grounding import (
    STOPWORDS,
    content_words,
    split_sentences,
    support_ratio,
    unsupported_names,
    unsupported_quotes,
)
from .books import find_references
from .grounding import content_stems
from .llm import LLMManager, LLMUnavailable
from .retrieval import Retriever, Source

log = logging.getLogger(__name__)

NOT_FOUND = "I couldn't find an answer to that in your library."

SYSTEM_PROMPT = """You answer questions about the Bible using ONLY the numbered sources given to you.
Sources marked SCRIPTURE are Bible text. Sources marked COMMENTARY, BIBLE DICTIONARY or REFERENCE BOOK are human-written books ABOUT the Bible; they are not Scripture.

Rules:
1. Use only facts stated in the sources. Do not use outside knowledge, even if you are sure it is true.
2. After every statement, cite the supporting source number in square brackets, like [2].
3. If the sources do not answer the question, set "status" to "not_in_sources" and leave "answer" empty. Do not guess.
4. If the sources answer only part of the question, set "status" to "partial" and say what the sources do not cover.
5. If sources disagree, set "status" to "sources_disagree" and briefly give each view with its citation.
6. When information comes from a commentary or dictionary, say so (for example "Easton's Bible Dictionary says ..."). Never present it as Bible text.
7. Only put words in quotation marks if they are copied exactly from a source.
8. Be direct. Do not preach, add applications, or add details that are not in the sources."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["answered", "partial", "not_in_sources", "sources_disagree"]},
        "answer": {"type": "string"},
        "missing": {"type": "string"},
    },
    "required": ["status", "answer"],
}

KEYWORD_SCHEMA = {
    "type": "object",
    "properties": {"keywords": {"type": "array", "items": {"type": "string"}, "maxItems": 8}},
    "required": ["keywords"],
}

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {"supported": {"type": "string", "enum": ["yes", "no"]}},
    "required": ["supported"],
}

_DANGLING = re.compile(r",?\s*\b(?:as (?:stated|mentioned|noted|described|seen|recorded|written|shown|said)(?: in| by)?|according to|see|(?:is |are )?(?:also )?(?:referenced|mentioned|described|recorded) in)\s*(?=[.!?;:,]|$)", re.I)
_CITE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


class AnswerEngine:
    def __init__(self, retriever: Retriever, llm: LLMManager):
        self.retriever = retriever
        self.llm = llm

    # ------------------------------------------------------------------ helpers
    def _keywords(self, question: str) -> list[str]:
        """Let the model suggest search words (synonyms, older word forms). These are
        only used to search the library - never shown as facts."""
        try:
            r = self.llm.chat_json(
                [
                    {"role": "system", "content": "You suggest search keywords for finding Bible passages. Reply in JSON."},
                    {"role": "user", "content": "Give up to 8 single-word search keywords (include names, synonyms and "
                                                "King James-style word forms) for finding Bible passages about this "
                                                f"question:\n{question}"},
                ],
                KEYWORD_SCHEMA, max_tokens=80, temperature=0.0,
            )
            kws = [str(k).strip() for k in r.get("keywords", []) if isinstance(k, str)]
            return [k for k in kws if re.fullmatch(r"[A-Za-z][A-Za-z'-]{1,30}", k)][:8]
        except Exception as e:  # noqa: BLE001 - keyword expansion is optional
            log.info("keyword expansion skipped: %s", e)
            return []

    @staticmethod
    def _names_in_question(question: str) -> list[str]:
        toks = re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", question)
        return [t for i, t in enumerate(toks)
                if i > 0 and t[0].isupper() and t.lower() not in STOPWORDS and t.lower() not in ("i", "god", "lord")]

    @staticmethod
    def _source_text(s: Source) -> str:
        return f"{s.title} {s.abbreviation} {s.label} {s.text}"

    def _check(self, sentence: str, sources: list[Source]) -> str | None:
        """Return a reason string if the sentence is NOT supported by these sources."""
        text = _CITE.sub("", sentence).strip()
        if not content_words(text):
            return None
        joined = " ".join(self._source_text(s) for s in sources)
        names = unsupported_names(text, joined)
        if names:
            return f"names not in the cited sources: {', '.join(names[:3])}"
        quotes = unsupported_quotes(text, joined)
        if quotes:
            return "quoted words not found in the cited sources"
        if support_ratio(text, joined) < 0.65:
            return "wording not supported by the cited sources"
        # Bible references written in the sentence must be inside the cited passages.
        for ref in find_references(text):
            if not any(s.is_scripture and s.book == ref.book and s.chapter == ref.chapter and
                       (ref.verse is None or (s.verse_start or 0) <= ref.verse <= (s.verse_end or 999)) for s in sources):
                return f"mentions {ref.label()}, which is not in the cited sources"
        return None

    def _verify(self, sentence: str, sources: list[Source]) -> str:
        """Ask the model whether the cited text states the sentence. Returns yes/no/unknown."""
        text = "\n\n".join(s.prompt_block(i + 1) for i, s in enumerate(sources))
        try:
            r = self.llm.chat_json(
                [{"role": "system", "content": "You check facts strictly. Answer only from the given text, never from your own knowledge."},
                 {"role": "user", "content": f"TEXT:\n{text}\n\nCLAIM: {sentence}\n\nDoes the TEXT clearly state this CLAIM? "
                                             "Answer \"yes\" only if every part of the claim is stated in the TEXT. Answer \"no\" if any part "
                                             "is missing, different, or contradicted. Reply in JSON."}],
                VERIFY_SCHEMA, max_tokens=20, temperature=0.0)
            return str(r.get("supported", "unknown")).lower()
        except Exception as e:  # noqa: BLE001 - verification failure keeps the lexical checks only
            log.info("verification skipped: %s", e)
            return "unknown"

    def _search_only(self, question: str, sources: list[Source]) -> list[dict[str, Any]]:
        return [s.to_dict(i + 1) for i, s in enumerate(sources)]

    # ------------------------------------------------------------------ main entry
    def ask(self, question: str, detail: str = "brief", preferred_id: int | None = None) -> dict[str, Any]:
        question = (question or "").strip()
        if not question:
            raise ValueError("Please type a question.")
        have_model = self.llm.backend is not None
        extra = self._keywords(question) if have_model else []
        sources = self.retriever.retrieve(question, extra, preferred_id)
        coverage = self.retriever.coverage(question, sources)
        names = self._names_in_question(question)
        joined_all = " ".join(self._source_text(s) for s in sources).lower()
        missing_names = [n for n in names if n.lower().rstrip("'s") not in joined_all]
        base = {"question": question, "detail": detail, "searched_sources": len(sources)}

        if not sources or coverage < 0.5 or missing_names:
            return {**base, "status": "not_found", "answer": NOT_FOUND, "segments": [], "citations": [],
                    "notes": ["None of your library's sources matched the key words of this question."],
                    "removed": [], "related": []}

        if not have_model:
            return {**base, "status": "no_model", "answer": "", "segments": [], "citations": [], "removed": [],
                    "notes": ["Answering questions needs a local language model (Settings → Language model). "
                              "Below are the passages that matched your words — they are search results, not an answer."],
                    "related": self._search_only(question, sources)}

        limit = "Answer in at most 3 short sentences." if detail != "detailed" else \
            "Answer in up to 8 sentences, using every relevant source."
        prompt = "SOURCES:\n\n" + "\n\n".join(s.prompt_block(i + 1) for i, s in enumerate(sources)) + \
            f"\n\nQUESTION: {question}\n\n{limit} Cite sources like [1]. Reply in JSON."
        try:
            raw = self.llm.chat_json(
                [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                ANSWER_SCHEMA, max_tokens=700 if detail == "detailed" else 350, temperature=0.1,
            )
        except LLMUnavailable as e:
            return {**base, "status": "error", "answer": "", "segments": [], "citations": [], "removed": [],
                    "notes": [str(e)], "related": self._search_only(question, sources)}
        except Exception as e:  # noqa: BLE001
            log.exception("model call failed")
            return {**base, "status": "error", "answer": "", "segments": [], "citations": [], "removed": [],
                    "notes": [f"The language model failed: {e}"], "related": self._search_only(question, sources)}

        status = str(raw.get("status") or "answered")
        answer = str(raw.get("answer") or "").strip()
        if status == "not_in_sources" or not answer:
            return {**base, "status": "not_found", "answer": NOT_FOUND, "segments": [], "citations": [], "removed": [],
                    "notes": ["The sources that were searched don't contain the answer."],
                    "related": self._search_only(question, sources[:4])}

        kept: list[dict[str, Any]] = []
        removed: list[dict[str, str]] = []
        for sent in split_sentences(answer):
            nums = [int(n) for g in _CITE.findall(sent) for n in g.split(",")]
            cited = [sources[n - 1] for n in dict.fromkeys(nums) if 1 <= n <= len(sources)]
            clean = _CITE.sub("", sent).strip()
            # Drop phrases left dangling once citation markers are removed ("as stated in.").
            clean = _DANGLING.sub("", clean)
            clean = re.sub(r"\s+([.,;:!?])", r"\1", clean).strip()
            clean = re.sub(r",\s*([.!?])$", r"\1", clean)
            if not content_words(clean):
                continue
            reason = self._check(clean, cited) if cited else "no citation"
            if reason:
                # The model may simply have cited the wrong number: accept the sentence
                # only if a single retrieved source fully supports it.
                best = None
                for s in sources:
                    if self._check(clean, [s]) is None:
                        best = s
                        break
                if best is None:
                    removed.append({"text": clean, "reason": reason})
                    continue
                cited = [best]
            kept.append({"text": clean, "sources": cited})

        if not kept:
            return {**base, "status": "not_found", "answer": NOT_FOUND, "segments": [], "citations": [],
                    "removed": removed,
                    "notes": ["The model's draft answer could not be verified against your library, so it was withheld."],
                    "related": self._search_only(question, sources[:4])}

        # The answer as a whole must be about what was asked: it has to share key
        # words with the question (otherwise e.g. a list of Noah's sons would pass
        # as an answer about Noah's wife).
        q_stems = content_stems(question)
        answer_stems = content_stems(" ".join(k["text"] for k in kept))
        if q_stems and not (q_stems & answer_stems):
            removed.extend({"text": k["text"], "reason": "does not address the question"} for k in kept)
            kept = []
        if not kept:
            return {**base, "status": "not_found", "answer": NOT_FOUND, "segments": [], "citations": [],
                    "removed": removed,
                    "notes": ["The model's draft answer did not address the question using your library, so it was withheld."],
                    "related": self._search_only(question, sources[:4])}
        if detail != "detailed":
            kept = kept[:4]
        # Second, independent check: the model judges each sentence against ONLY the
        # text it cites (an entailment test). Sentences it can't confirm are removed.
        verified = []
        for k in kept:
            verdict = self._verify(k["text"], k["sources"])
            if verdict == "no":
                removed.append({"text": k["text"], "reason": "the cited source does not state this (verification check)"})
            else:
                verified.append(k)
        kept = verified
        if not kept:
            return {**base, "status": "not_found", "answer": NOT_FOUND, "segments": [], "citations": [],
                    "removed": removed,
                    "notes": ["The model's draft answer could not be confirmed by the cited sources, so it was withheld."],
                    "related": self._search_only(question, sources[:4])}
        # Renumber citations in order of first use.
        order: list[Source] = []
        segments = []
        for k in kept:
            ns = []
            for s in k["sources"]:
                if s not in order:
                    order.append(s)
                ns.append(order.index(s) + 1)
            segments.append({"text": k["text"], "cites": ns})
        answer_text = " ".join(f"{seg['text']} " + "".join(f"[{n}]" for n in seg["cites"]) for seg in segments).strip()

        notes = []
        if status == "partial":
            missing = str(raw.get("missing") or "").strip()
            notes.append("Your library only partly answers this." + (f" Not covered: {missing}" if missing and len(missing) < 300 else ""))
        if status == "sources_disagree":
            notes.append("Your sources don't fully agree on this. Compare the sources below.")
        if order and not any(s.is_scripture for s in order):
            notes.append("This answer comes from reference books in your library, not directly from Scripture.")
        if removed:
            notes.append(f"{len(removed)} statement(s) from the model were removed because the cited sources didn't support them.")
        return {**base, "status": "partial" if status == "partial" else ("disagree" if status == "sources_disagree" else "answered"),
                "answer": answer_text, "segments": segments, "citations": [s.to_dict(i + 1) for i, s in enumerate(order)],
                "removed": removed, "notes": notes, "related": [],
                "model": self.llm.status().get("model", "")}
