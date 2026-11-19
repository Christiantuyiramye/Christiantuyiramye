"""Deterministic checks that keep generated text tied to its sources.

The language model is asked to stay within the sources, but small local
models do not always obey. Every generated sentence is therefore checked
against the text it cites before it is shown or spoken:

* support      - most content words of the sentence must occur in the cited text
* names        - capitalised names must occur in the cited text
* quotations   - anything in quotation marks must appear verbatim in the cited text
* moralising   - retellings may not add lessons or applications
"""
from __future__ import annotations

import re
import unicodedata

STOPWORDS = set(
    """a about above after again against all also am an and any are aren't as at be because been before being below
    between both but by can could did didn't do does doesn't doing don't down during each either else even ever every
    few for from further had has have having he he'd he'll he's her here hers herself him himself his how however i
    i'd i'll i'm i've if in into is isn't it it's its itself just let let's may me might more most much must my myself
    no nor not now of off on once only or other ought our ours ourselves out over own per same shall she should so
    some such than that that's the their theirs them themselves then there there's these they they'd they'll they're
    they've this those though through thus to too toward towards under until up upon us very was wasn't we we'd we'll
    we're we've were weren't what what's when where which while who whom whose why will with within without would
    yes yet you your yours yourself yourselves thee thou thy thine ye unto hath doth art shalt wilt hast
    also later next first then after afterward afterwards soon finally meanwhile one two another many again still
    tell explain describe according bible biblical scripture scriptures verse verses passage passages book books
    say says said saying mention mentioned mentions happen happened happens give gives gave given know known
    called named name names something someone anything anyone thing things way often really actually""".split()
)

# Words that legitimately appear capitalised in a retelling or answer without
# being "new names".
CAPITAL_OK = {"god", "lord", "i", "he", "him", "his", "spirit", "holy", "heaven", "heavens", "son", "father",
              "scripture", "bible", "christ", "messiah", "king", "the", "a", "an"}

_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_SUFFIXES = ("ings", "ing", "eth", "est", "edst", "ed", "es", "s")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return text


def stem(word: str) -> str:
    w = word.lower().strip("'-")
    if w.endswith("'s"):
        w = w[:-2]
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            break
    if w.endswith("e") and len(w) > 3:
        w = w[:-1]
    if w.endswith("i") and len(w) > 3:  # carries/carried -> carri -> carry-ish
        w = w[:-1] + "y"
    return w


def words(text: str) -> list[str]:
    return _WORD.findall(normalize(text))


def content_words(text: str) -> list[str]:
    return [w.lower().strip("'-") for w in words(text) if w.lower().strip("'-") not in STOPWORDS and len(w) > 2]


def content_stems(text: str) -> set[str]:
    return {stem(w) for w in content_words(text)}


def all_stems(text: str) -> set[str]:
    return {stem(w) for w in words(text)}


def support_ratio(sentence: str, source_text: str) -> float:
    """Share of the sentence's content words that also occur in the source."""
    s = content_stems(sentence)
    if not s:
        return 1.0
    src = all_stems(source_text)
    return len(s & src) / len(s)


def unsupported_names(sentence: str, source_text: str) -> list[str]:
    """Capitalised words (not sentence-initial) that never occur in the source."""
    src_lower = {w.lower() for w in words(source_text)}
    src_stems = all_stems(source_text)
    out = []
    for sent in re.split(r"(?<=[.!?;:])\s+", normalize(sentence)):
        toks = words(sent)
        for i, tok in enumerate(toks):
            if i == 0 or not tok[0].isupper():
                continue
            base = tok.lower().removesuffix("'s").strip("'-")
            if base in CAPITAL_OK or base in src_lower or stem(base) in src_stems:
                continue
            out.append(tok)
    return out


_QUOTE = re.compile(r'"([^"]{3,})"')


def _squash(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize(s).lower()).strip()


def unsupported_quotes(sentence: str, source_text: str) -> list[str]:
    """Quoted passages that do not appear (ignoring punctuation/case) in the source."""
    src = _squash(source_text)
    bad = []
    for q in _QUOTE.findall(normalize(sentence)):
        sq = _squash(q)
        if sq and sq not in src:
            bad.append(q)
    return bad


_MORAL = re.compile(
    r"\b(lesson|moral|teaches us|teach us|we (?:can|should|must|may) (?:learn|see|remember)|reminds? us|"
    r"shows? us|this (?:story|passage) (?:shows|teaches|reminds)|application|let us|we learn|our lives|for us today)\b",
    re.I,
)


def is_moralizing(sentence: str) -> bool:
    return bool(_MORAL.search(sentence))


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    # Keep citation markers like "[2]" attached to the sentence they follow.
    parts = re.split(r"(?<=[.!?])(?:\s*(\[\d+(?:\s*,\s*\d+)*\]))?\s+(?=[A-Z\"“(])", text)
    out: list[str] = []
    i = 0
    while i < len(parts):
        sent = parts[i]
        if i + 1 < len(parts) and parts[i + 1]:
            sent = f"{sent} {parts[i + 1]}"
        if sent and sent.strip():
            out.append(sent.strip())
        i += 2
    return out
