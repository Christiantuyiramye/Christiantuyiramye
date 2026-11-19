"""Canonical Bible book list, name/abbreviation matching and reference parsing.

Books are identified internally by their position in the 66-book Protestant
canon (1 = Genesis ... 66 = Revelation) and by their OSIS/USFM codes, so any
importer can map the many naming conventions found in public-domain sources
onto one stable key.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# (number, OSIS id, USFM id, display name, extra aliases)
_BOOKS: list[tuple[int, str, str, str, tuple[str, ...]]] = [
    (1, "Gen", "GEN", "Genesis", ("ge", "gn", "gen")),
    (2, "Exod", "EXO", "Exodus", ("ex", "exo", "exod")),
    (3, "Lev", "LEV", "Leviticus", ("le", "lv", "lev")),
    (4, "Num", "NUM", "Numbers", ("nu", "nm", "nb", "num")),
    (5, "Deut", "DEU", "Deuteronomy", ("dt", "deu", "deut")),
    (6, "Josh", "JOS", "Joshua", ("jos", "jsh", "josh")),
    (7, "Judg", "JDG", "Judges", ("jdg", "jg", "jdgs", "judg")),
    (8, "Ruth", "RUT", "Ruth", ("ru", "rth", "rut")),
    (9, "1Sam", "1SA", "1 Samuel", ("1sa", "1sam", "1sm", "i samuel", "first samuel", "1 kingdoms")),
    (10, "2Sam", "2SA", "2 Samuel", ("2sa", "2sam", "2sm", "ii samuel", "second samuel", "2 kingdoms")),
    (11, "1Kgs", "1KI", "1 Kings", ("1ki", "1kgs", "1kg", "i kings", "first kings", "3 kingdoms")),
    (12, "2Kgs", "2KI", "2 Kings", ("2ki", "2kgs", "2kg", "ii kings", "second kings", "4 kingdoms")),
    (13, "1Chr", "1CH", "1 Chronicles", ("1ch", "1chr", "1chron", "i chronicles", "first chronicles")),
    (14, "2Chr", "2CH", "2 Chronicles", ("2ch", "2chr", "2chron", "ii chronicles", "second chronicles")),
    (15, "Ezra", "EZR", "Ezra", ("ezr",)),
    (16, "Neh", "NEH", "Nehemiah", ("ne", "neh")),
    (17, "Esth", "EST", "Esther", ("es", "est", "esth")),
    (18, "Job", "JOB", "Job", ("jb",)),
    (19, "Ps", "PSA", "Psalms", ("ps", "psa", "psalm", "pss", "psm")),
    (20, "Prov", "PRO", "Proverbs", ("pr", "pro", "prov", "prv")),
    (21, "Eccl", "ECC", "Ecclesiastes", ("ec", "ecc", "eccl", "eccles", "qoheleth")),
    (22, "Song", "SNG", "Song of Solomon", ("song", "sos", "sng", "song of songs", "canticles", "canticle of canticles")),
    (23, "Isa", "ISA", "Isaiah", ("is", "isa")),
    (24, "Jer", "JER", "Jeremiah", ("je", "jer", "jr")),
    (25, "Lam", "LAM", "Lamentations", ("la", "lam")),
    (26, "Ezek", "EZK", "Ezekiel", ("eze", "ezek", "ezk")),
    (27, "Dan", "DAN", "Daniel", ("da", "dan", "dn")),
    (28, "Hos", "HOS", "Hosea", ("ho", "hos")),
    (29, "Joel", "JOL", "Joel", ("jl", "joe", "jol")),
    (30, "Amos", "AMO", "Amos", ("am", "amo")),
    (31, "Obad", "OBA", "Obadiah", ("ob", "oba", "obad")),
    (32, "Jonah", "JON", "Jonah", ("jon", "jnh")),
    (33, "Mic", "MIC", "Micah", ("mi", "mic")),
    (34, "Nah", "NAM", "Nahum", ("na", "nah", "nam")),
    (35, "Hab", "HAB", "Habakkuk", ("hab", "hb")),
    (36, "Zeph", "ZEP", "Zephaniah", ("zep", "zeph", "zp")),
    (37, "Hag", "HAG", "Haggai", ("hag", "hg")),
    (38, "Zech", "ZEC", "Zechariah", ("zec", "zech", "zc")),
    (39, "Mal", "MAL", "Malachi", ("mal", "ml")),
    (40, "Matt", "MAT", "Matthew", ("mt", "mat", "matt")),
    (41, "Mark", "MRK", "Mark", ("mk", "mar", "mrk")),
    (42, "Luke", "LUK", "Luke", ("lk", "luk")),
    (43, "John", "JHN", "John", ("jn", "jhn", "joh")),
    (44, "Acts", "ACT", "Acts", ("ac", "act", "acts of the apostles")),
    (45, "Rom", "ROM", "Romans", ("ro", "rom", "rm")),
    (46, "1Cor", "1CO", "1 Corinthians", ("1co", "1cor", "i corinthians", "first corinthians")),
    (47, "2Cor", "2CO", "2 Corinthians", ("2co", "2cor", "ii corinthians", "second corinthians")),
    (48, "Gal", "GAL", "Galatians", ("ga", "gal")),
    (49, "Eph", "EPH", "Ephesians", ("eph", "ephes")),
    (50, "Phil", "PHP", "Philippians", ("php", "phil", "pp")),
    (51, "Col", "COL", "Colossians", ("col",)),
    (52, "1Thess", "1TH", "1 Thessalonians", ("1th", "1thess", "1thes", "i thessalonians", "first thessalonians")),
    (53, "2Thess", "2TH", "2 Thessalonians", ("2th", "2thess", "2thes", "ii thessalonians", "second thessalonians")),
    (54, "1Tim", "1TI", "1 Timothy", ("1ti", "1tim", "i timothy", "first timothy")),
    (55, "2Tim", "2TI", "2 Timothy", ("2ti", "2tim", "ii timothy", "second timothy")),
    (56, "Titus", "TIT", "Titus", ("tit", "ti")),
    (57, "Phlm", "PHM", "Philemon", ("phm", "phlm", "philem")),
    (58, "Heb", "HEB", "Hebrews", ("heb",)),
    (59, "Jas", "JAS", "James", ("jas", "jm", "jam")),
    (60, "1Pet", "1PE", "1 Peter", ("1pe", "1pet", "1pt", "i peter", "first peter")),
    (61, "2Pet", "2PE", "2 Peter", ("2pe", "2pet", "2pt", "ii peter", "second peter")),
    (62, "1John", "1JN", "1 John", ("1jn", "1jo", "1joh", "i john", "first john")),
    (63, "2John", "2JN", "2 John", ("2jn", "2jo", "2joh", "ii john", "second john")),
    (64, "3John", "3JN", "3 John", ("3jn", "3jo", "3joh", "iii john", "third john")),
    (65, "Jude", "JUD", "Jude", ("jud", "jde")),
    (66, "Rev", "REV", "Revelation", ("re", "rev", "rv", "revelation of john", "revelations", "apocalypse", "the revelation")),
]


@dataclass(frozen=True)
class Book:
    number: int
    osis: str
    usfm: str
    name: str

    @property
    def testament(self) -> str:
        return "OT" if self.number <= 39 else "NT"


BOOKS: list[Book] = [Book(n, o, u, name) for n, o, u, name, _ in _BOOKS]
BY_NUMBER: dict[int, Book] = {b.number: b for b in BOOKS}

_ROMAN = {"i": "1", "ii": "2", "iii": "3"}


def _norm(name: str) -> str:
    s = name.lower().strip().replace(".", "").replace("_", " ")
    s = re.sub(r"\s+", " ", s)
    parts = s.split(" ")
    if parts and parts[0] in _ROMAN:
        parts[0] = _ROMAN[parts[0]]
    if parts and parts[0] in ("first", "second", "third"):
        parts[0] = {"first": "1", "second": "2", "third": "3"}[parts[0]]
    s = " ".join(parts)
    s = re.sub(r"^(\d) ", r"\1", s)  # "1 samuel" -> "1samuel"
    return s.replace(" ", "")


_ALIASES: dict[str, int] = {}
for _n, _o, _u, _name, _extra in _BOOKS:
    for alias in (_o, _u, _name, *_extra):
        _ALIASES[_norm(alias)] = _n


def find_book(name: str | int | None) -> Book | None:
    """Resolve a book from a number, OSIS/USFM code, full name or abbreviation."""
    if name is None:
        return None
    if isinstance(name, int):
        return BY_NUMBER.get(name)
    s = str(name).strip()
    if s.isdigit():
        return BY_NUMBER.get(int(s))
    key = _norm(s)
    if key in _ALIASES:
        return BY_NUMBER[_ALIASES[key]]
    # Unambiguous prefix match ("Philipp", "Genes")
    if len(key) >= 3:
        matches = {n for alias, n in _ALIASES.items() if alias.startswith(key)}
        if len(matches) == 1:
            return BY_NUMBER[matches.pop()]
    return None


@dataclass(frozen=True)
class PassageRef:
    """A contiguous passage. verse=None means "whole chapter"."""

    book: int
    chapter: int
    verse: int | None = None
    end_chapter: int | None = None
    end_verse: int | None = None

    @property
    def book_obj(self) -> Book:
        return BY_NUMBER[self.book]

    def label(self) -> str:
        b = self.book_obj.name
        if self.verse is None:
            if self.end_chapter and self.end_chapter != self.chapter:
                return f"{b} {self.chapter}-{self.end_chapter}"
            return f"{b} {self.chapter}"
        s = f"{b} {self.chapter}:{self.verse}"
        ec = self.end_chapter or self.chapter
        if self.end_verse is not None:
            if ec != self.chapter:
                s += f"-{ec}:{self.end_verse}"
            elif self.end_verse != self.verse:
                s += f"-{self.end_verse}"
        return s


_REF_RE = re.compile(
    r"""^\s*
    (?P<book>(?:[1-3]|i{1,3})?\s*[A-Za-z][A-Za-z .]*?)\s*
    (?P<c1>\d+)
    (?:\s*[:.]\s*(?P<v1>\d+))?
    (?:\s*[-–—]\s*(?P<a>\d+)(?:\s*[:.]\s*(?P<b>\d+))?)?
    \s*$""",
    re.X | re.I,
)


def parse_reference(text: str) -> PassageRef | None:
    """Parse "John 3:16", "Jn 3:16-18", "Gen 1", "1 Cor 13:4-7", "Gen 1:1-2:3", "Ps 23"."""
    m = _REF_RE.match(text or "")
    if not m:
        return None
    book = find_book(m.group("book"))
    if not book:
        return None
    c1 = int(m.group("c1"))
    v1 = int(m.group("v1")) if m.group("v1") else None
    a, b = m.group("a"), m.group("b")
    if v1 is None:
        # "Gen 1" or "Gen 1-3"
        if a and not b:
            return PassageRef(book.number, c1, None, int(a), None)
        return PassageRef(book.number, c1)
    if a and b:  # Gen 1:1-2:3
        return PassageRef(book.number, c1, v1, int(a), int(b))
    if a:  # John 3:16-18
        return PassageRef(book.number, c1, v1, c1, int(a))
    return PassageRef(book.number, c1, v1, c1, v1)


_INLINE_REF_RE = re.compile(
    r"\b((?:[1-3]\s?)?[A-Z][a-z]{1,15}\.?)\s+(\d{1,3})(?::(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?)?\b"
)


def find_references(text: str) -> list[PassageRef]:
    """Find Bible references mentioned inside free text (used to seed retrieval)."""
    out: list[PassageRef] = []
    for m in _INLINE_REF_RE.finditer(text or ""):
        token = m.group(1).replace(".", "").strip()
        v = int(m.group(3)) if m.group(3) else None
        # Very short abbreviations ("Is", "Am") are ordinary English words;
        # only accept them when a verse number makes the reference explicit.
        if len(token.replace(" ", "")) <= 3 and v is None and token.lower() not in ("job", "joel", "acts", "ruth", "mark", "luke", "john", "jude", "amos"):
            continue
        book = find_book(token)
        if not book:
            continue
        c = int(m.group(2))
        ev = int(m.group(4)) if m.group(4) else v
        out.append(PassageRef(book.number, c, v, c if v else None, ev))
    return out


def verse_label(book: int, chapter: int, verse: int) -> str:
    return f"{BY_NUMBER[book].name} {chapter}:{verse}"
