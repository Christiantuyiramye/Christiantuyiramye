"""Parsers that turn files the user owns into library rows.

Scripture formats
    * Scrollmapper-style JSON ({"translation", "books": [{"name", "chapters": [...]}]})
    * JSON list of {"book", "chapter", "verse", "text"} records
    * CSV / TSV with book, chapter, verse, text columns
    * USFM (.usfm/.sfm, or a .zip of USFM files - e.g. eBible.org downloads)
    * OSIS XML and Zefania XML
    * Verse-per-line text ("GEN 1:1 In the beginning...", "Genesis 1:1 ...")

Reference formats (commentaries, dictionaries, other books)
    * Plain text / Markdown (split by headings, form-feed pages or paragraphs)
    * PDF (one location per page, "p. N")
    * HTML and EPUB (split by chapter files and headings)
    * JSON or CSV dictionaries: {"term", "text"}
    * JSON or CSV verse-keyed commentary: {"book", "chapter", "verse_start", "verse_end", "text"}
"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from .books import find_book, parse_reference as parse_ref


class ImportErrorWithHint(ValueError):
    """Raised with a user-facing explanation of why a file could not be imported."""


@dataclass
class ScriptureImport:
    rows: list[tuple[int, int, int, str]] = field(default_factory=list)  # (book, chapter, verse, text)
    title: str = ""
    abbreviation: str = ""
    skipped_books: set[str] = field(default_factory=set)
    fmt: str = ""


@dataclass
class ReferenceEntry:
    text: str
    heading: str = ""
    location: str = ""
    page: int | None = None
    book: int | None = None
    chapter: int | None = None
    verse_start: int | None = None
    verse_end: int | None = None


@dataclass
class ReferenceImport:
    entries: list[ReferenceEntry] = field(default_factory=list)
    title: str = ""
    fmt: str = ""


# --------------------------------------------------------------------------- helpers

_WS = re.compile(r"\s+")


def clean_text(s: str) -> str:
    return _WS.sub(" ", s or "").strip()


def _read_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            if enc == "utf-16" and "\x00" in text:
                continue
            return text
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def chunk_text(text: str, max_chars: int = 1400) -> list[str]:
    """Split long text on paragraph, then sentence boundaries."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    for p in paras:
        if len(p) <= max_chars:
            pieces.append(p)
            continue
        sentences = re.split(r"(?<=[.!?;])\s+", p)
        buf = ""
        for s in sentences:
            if len(buf) + len(s) + 1 > max_chars and buf:
                pieces.append(buf)
                buf = ""
            while len(s) > max_chars:  # pathological very long sentence
                pieces.append(s[:max_chars])
                s = s[max_chars:]
            buf = f"{buf} {s}".strip()
        if buf:
            pieces.append(buf)
    chunks: list[str] = []
    buf = ""
    for p in pieces:
        if len(buf) + len(p) + 2 > max_chars and buf:
            chunks.append(buf)
            buf = ""
        buf = f"{buf}\n\n{p}".strip()
    if buf:
        chunks.append(buf)
    return chunks


def _int(v) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- scripture

def _scripture_from_records(records: Iterable[dict], out: ScriptureImport) -> None:
    for r in records:
        low = {str(k).lower(): v for k, v in r.items()}
        bname = low.get("book_name") or low.get("book") or low.get("b")
        book = find_book(bname if not isinstance(bname, int) else int(bname))
        c = _int(low.get("chapter", low.get("c")))
        v = _int(low.get("verse", low.get("v")))
        t = clean_text(str(low.get("text", low.get("t", "")) or ""))
        if not book:
            if bname:
                out.skipped_books.add(str(bname))
            continue
        if c and v and t:
            out.rows.append((book.number, c, v, t))


def parse_scripture_json(data: bytes) -> ScriptureImport:
    obj = json.loads(_read_text(data))
    out = ScriptureImport(fmt="json")
    if isinstance(obj, dict) and "books" in obj:
        out.title = str(obj.get("translation") or obj.get("name") or "")
        books = obj["books"]
        use_position = len(books) == 66
        for i, b in enumerate(books, start=1):
            name = b.get("name") or b.get("book") or ""
            book = find_book(name) or (find_book(i) if use_position else None)
            if not book:
                out.skipped_books.add(str(name))
                continue
            for ch in b.get("chapters", []):
                c = _int(ch.get("chapter"))
                for v in ch.get("verses", []):
                    vn, t = _int(v.get("verse")), clean_text(v.get("text", ""))
                    if c and vn and t:
                        out.rows.append((book.number, c, vn, t))
    elif isinstance(obj, dict) and isinstance(obj.get("verses"), list):
        out.title = str(obj.get("translation") or obj.get("name") or "")
        _scripture_from_records(obj["verses"], out)
    elif isinstance(obj, list):
        _scripture_from_records(obj, out)
    else:
        raise ImportErrorWithHint("This JSON file doesn't look like a Bible (expected a 'books' list or verse records).")
    return out


def parse_scripture_csv(data: bytes) -> ScriptureImport:
    text = _read_text(data)
    dialect = "excel-tab" if text.split("\n", 1)[0].count("\t") >= 3 else "excel"
    # Tab-separated Bibles are not quoted; verse text may contain bare quote marks.
    reader = csv.reader(io.StringIO(text), dialect=dialect, quoting=csv.QUOTE_NONE if dialect == "excel-tab" else csv.QUOTE_MINIMAL)
    rows = [r for r in reader if r]
    if not rows:
        raise ImportErrorWithHint("The file is empty.")
    header = [h.strip().lower() for h in rows[0]]
    out = ScriptureImport(fmt="csv")
    names = {"book": None, "chapter": None, "verse": None, "text": None}
    aliases = {"book": ("book", "b", "book_name", "bookname"), "chapter": ("chapter", "c", "chap"),
               "verse": ("verse", "v", "vs"), "text": ("text", "t", "content", "scripture")}
    for key, opts in aliases.items():
        for i, h in enumerate(header):
            if h in opts:
                names[key] = i
                break
    if all(v is not None for v in names.values()):
        body = rows[1:]
    elif len(rows[0]) >= 4 and _int(rows[0][1]) and _int(rows[0][2]):
        names = {"book": 0, "chapter": 1, "verse": 2, "text": 3}
        body = rows
    else:
        raise ImportErrorWithHint("CSV/TSV Bibles need book, chapter, verse and text columns.")
    for r in body:
        try:
            rec = {k: r[i] for k, i in names.items()}
        except IndexError:
            continue
        if len(r) > names["text"] + 1 and dialect == "excel":  # unquoted commas in the text column
            rec["text"] = ",".join(r[names["text"]:])
        _scripture_from_records([rec], out)
    return out


_USFM_DROP = re.compile(r"\\(f|fe|x|ef|ex|fig|rq)\s.*?\\\1\*", re.S)
_USFM_WORD = re.compile(r"\\\+?w\s+([^|\\]*?)(\|[^\\]*?)?\\\+?w\*")
_USFM_MARK = re.compile(r"\\\+?[a-z]+[0-9]*\*?")


def _clean_usfm(s: str) -> str:
    s = _USFM_DROP.sub("", s)
    s = _USFM_WORD.sub(r"\1", s)
    s = _USFM_MARK.sub("", s)
    return clean_text(s.replace("//", " "))


def _parse_usfm_text(text: str, out: ScriptureImport) -> None:
    m = re.search(r"\\id\s+(\w+)", text)
    if not m:
        return
    book = find_book(m.group(1))
    if not book:
        out.skipped_books.add(m.group(1))
        return
    if not out.title:
        h = re.search(r"\\id\s+\w+\s+(.*)", text)
        if h:
            out.title = ""  # \id comments are usually not the translation name
    chapter = 0
    current: list[str] = []
    verse = None

    def flush():
        if verse is not None and chapter:
            t = _clean_usfm(" ".join(current))
            if t:
                out.rows.append((book.number, chapter, verse, t))

    # Drop section headings, titles, etc. which aren't verse text.
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        cm = re.match(r"\\c\s+(\d+)", line)
        if cm:
            flush()
            verse, current = None, []
            chapter = int(cm.group(1))
            continue
        if re.match(r"\\(id|ide|h|toc\d|mt\d?|ms\d?|mr|s\d?|sr|r|d|sp|cl|rem|sts|restore|imt\d?|is\d?|ip|io\d?|iot|ie)\b", line):
            continue
        for part in re.split(r"(?=\\v\s+\d)", line):
            vm = re.match(r"\\v\s+(\d+)(?:[-–]\d+)?\s*(.*)", part, re.S)
            if vm:
                flush()
                verse, current = int(vm.group(1)), [vm.group(2)]
            elif verse is not None:
                current.append(part)
    flush()


def parse_usfm(data: bytes, name: str) -> ScriptureImport:
    out = ScriptureImport(fmt="usfm")
    if name.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.filename.lower().endswith((".usfm", ".sfm", ".ptx", ".txt")) and not info.is_dir():
                    _parse_usfm_text(_read_text(z.read(info)), out)
    else:
        _parse_usfm_text(_read_text(data), out)
    return out


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_xml_bible(data: bytes) -> ScriptureImport:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise ImportErrorWithHint(f"The XML file could not be read: {e}") from e
    tag = _local(root.tag).lower()
    if tag == "xmlbible":  # Zefania
        out = ScriptureImport(fmt="zefania", title=root.get("biblename", ""))
        for b in root.iter():
            if _local(b.tag).upper() != "BIBLEBOOK":
                continue
            book = find_book(_int(b.get("bnumber")) or b.get("bname"))
            if not book or book.number > 66:
                out.skipped_books.add(b.get("bname") or b.get("bnumber") or "?")
                continue
            for ch in b:
                if _local(ch.tag).upper() != "CHAPTER":
                    continue
                c = _int(ch.get("cnumber"))
                for v in ch:
                    if _local(v.tag).upper() == "VERS":
                        t = clean_text("".join(v.itertext()))
                        vn = _int(v.get("vnumber"))
                        if c and vn and t:
                            out.rows.append((book.number, c, vn, t))
        return out
    # OSIS
    out = ScriptureImport(fmt="osis")
    work = next((e for e in root.iter() if _local(e.tag) == "title"), None)
    if work is not None and work.text:
        out.title = clean_text(work.text)
    skip_tags = {"note", "title", "reference"}

    def text_of(el) -> str:
        parts = [el.text or ""]
        for child in el:
            if _local(child.tag) not in skip_tags:
                parts.append(text_of(child))
            parts.append(child.tail or "")
        return "".join(parts)

    containers = [e for e in root.iter() if _local(e.tag) == "verse" and e.get("osisID") and not e.get("sID")]
    if containers and any((e.text or "").strip() or len(e) for e in containers):
        for e in containers:
            _add_osis(out, e.get("osisID"), text_of(e))
        return out
    # Milestone form: <verse sID=.../> text <verse eID=.../>
    current_id, buf = None, []

    def walk(el):
        nonlocal current_id, buf
        name = _local(el.tag)
        if name == "verse" and el.get("sID"):
            current_id, buf = el.get("osisID"), []
        elif name == "verse" and el.get("eID"):
            if current_id:
                _add_osis(out, current_id, "".join(buf))
            current_id, buf = None, []
        elif name in skip_tags:
            if current_id is not None and el.tail:
                buf.append(el.tail)
            return
        elif current_id is not None and el.text:
            buf.append(el.text)
        for child in el:
            walk(child)
        if current_id is not None and el.tail and name != "verse":
            buf.append(el.tail)
        elif name == "verse" and el.tail and current_id is not None:
            buf.append(el.tail)

    walk(root)
    return out


def _add_osis(out: ScriptureImport, osis_id: str, text: str) -> None:
    first = osis_id.split()[0]
    parts = first.split(".")
    if len(parts) < 3:
        return
    book = find_book(parts[0])
    if not book:
        out.skipped_books.add(parts[0])
        return
    c, v, t = _int(parts[1]), _int(parts[2]), clean_text(text)
    if c and v and t:
        out.rows.append((book.number, c, v, t))


_VPL = re.compile(r"^\s*((?:[1-3]\s?)?[A-Za-z][A-Za-z ]*?)\s+(\d+):(\d+)\s+(.+)$")


def parse_vpl(data: bytes) -> ScriptureImport:
    out = ScriptureImport(fmt="vpl")
    for line in _read_text(data).splitlines():
        m = _VPL.match(line)
        if not m:
            continue
        book = find_book(m.group(1))
        if not book:
            out.skipped_books.add(m.group(1))
            continue
        out.rows.append((book.number, int(m.group(2)), int(m.group(3)), clean_text(m.group(4))))
    return out


def parse_scripture(data: bytes, filename: str) -> ScriptureImport:
    name = filename.lower()
    if name.endswith(".json") or name.endswith(".json.gz"):
        if name.endswith(".gz"):
            import gzip
            data = gzip.decompress(data)
        result = parse_scripture_json(data)
    elif name.endswith((".csv", ".tsv")) or name.endswith((".tsv.gz", ".csv.gz")):
        if name.endswith(".gz"):
            import gzip
            data = gzip.decompress(data)
        result = parse_scripture_csv(data)
    elif name.endswith((".usfm", ".sfm", ".ptx", ".zip")):
        result = parse_usfm(data, filename)
    elif name.endswith((".xml", ".osis", ".zef")):
        result = parse_xml_bible(data)
    elif name.endswith(".txt"):
        head = data[:4000].decode("utf-8", errors="ignore")
        result = parse_usfm(data, filename) if "\\id " in head else parse_vpl(data)
    else:
        raise ImportErrorWithHint(
            "Unsupported Bible format. Use JSON, CSV/TSV, USFM (or a .zip of USFM), OSIS/Zefania XML, or verse-per-line text."
        )
    # De-duplicate (some sources repeat a verse); keep the first occurrence.
    seen: set[tuple[int, int, int]] = set()
    rows = []
    for r in result.rows:
        if r[:3] not in seen:
            seen.add(r[:3])
            rows.append(r)
    result.rows = rows
    if not rows:
        raise ImportErrorWithHint("No verses were found in this file. Check that it is a Bible in a supported format.")
    return result


# --------------------------------------------------------------------------- reference books

class _HTMLText(HTMLParser):
    """Collect text, splitting into sections at h1-h3 headings."""

    def __init__(self):
        super().__init__()
        self.sections: list[tuple[str, list[str]]] = [("", [])]
        self._in_heading = False
        self._heading: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head"):
            self._skip += 1
        elif tag in ("h1", "h2", "h3"):
            self._in_heading, self._heading = True, []
        elif tag in ("p", "br", "div", "li", "tr"):
            self.sections[-1][1].append("\n\n" if tag in ("p", "div") else "\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head"):
            self._skip = max(0, self._skip - 1)
        elif tag in ("h1", "h2", "h3") and self._in_heading:
            self._in_heading = False
            self.sections.append((clean_text("".join(self._heading)), []))

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_heading:
            self._heading.append(data)
        else:
            self.sections[-1][1].append(data)


def _ref_fields(heading: str) -> dict:
    ref = parse_ref(heading) if heading else None
    if ref:
        return {"book": ref.book, "chapter": ref.chapter, "verse_start": ref.verse,
                "verse_end": ref.end_verse if ref.end_verse is not None else ref.verse}
    return {}


def _sections_to_entries(sections: list[tuple[str, str]], label: str = "Section") -> list[ReferenceEntry]:
    entries: list[ReferenceEntry] = []
    n = 0
    for heading, body in sections:
        body = re.sub(r"[ \t]+", " ", body)
        body = re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", body).strip()
        if not body:
            continue
        chunks = chunk_text(body)
        for i, chunk in enumerate(chunks, start=1):
            n += 1
            loc = f"{label}: {heading}" if heading else f"{label} {n}"
            if len(chunks) > 1:
                loc += f" (part {i})"
            entries.append(ReferenceEntry(text=chunk, heading=heading, location=loc, **_ref_fields(heading)))
    return entries


def parse_plain_text(data: bytes, filename: str) -> ReferenceImport:
    text = _read_text(data).replace("\r\n", "\n")
    out = ReferenceImport(fmt="text")
    if "\f" in text:  # form-feed separated pages
        for i, page in enumerate(text.split("\f"), start=1):
            for j, chunk in enumerate(chunk_text(page), start=1):
                out.entries.append(ReferenceEntry(text=chunk, location=f"p. {i}" + (f" (part {j})" if j > 1 else ""), page=i))
        return out
    md_heads = list(re.finditer(r"^(#{1,3})\s+(.+)$", text, re.M))
    if md_heads:
        sections = []
        first = text[: md_heads[0].start()].strip()
        if first:
            sections.append(("", first))
        for i, m in enumerate(md_heads):
            end = md_heads[i + 1].start() if i + 1 < len(md_heads) else len(text)
            sections.append((clean_text(m.group(2)), text[m.end():end]))
        out.entries = _sections_to_entries(sections)
        out.fmt = "markdown"
        if md_heads[0].group(1) == "#" and not out.title:
            out.title = clean_text(md_heads[0].group(2))
        return out
    # Plain paragraphs, grouped into ~1400 character chunks numbered as paragraphs.
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    buf, start = "", 1
    for i, p in enumerate(paras, start=1):
        if buf and len(buf) + len(p) > 1400:
            end = i - 1
            out.entries.append(ReferenceEntry(text=buf, location=f"¶ {start}" + (f"–{end}" if end > start else "")))
            buf, start = "", i
        buf = f"{buf}\n\n{p}".strip()
    if buf:
        end = len(paras)
        out.entries.append(ReferenceEntry(text=buf, location=f"¶ {start}" + (f"–{end}" if end > start else "")))
    return out


def parse_pdf(data: bytes) -> ReferenceImport:
    try:
        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover
        raise ImportErrorWithHint("PDF support needs the 'pypdf' package.") from e
    reader = PdfReader(io.BytesIO(data))
    out = ReferenceImport(fmt="pdf")
    meta = reader.metadata
    if meta and meta.title:
        out.title = clean_text(str(meta.title))
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - damaged pages shouldn't stop the import
            text = ""
        for j, chunk in enumerate(chunk_text(text), start=1):
            out.entries.append(ReferenceEntry(text=chunk, location=f"p. {i}" + (f" (part {j})" if j > 1 else ""), page=i))
    if not out.entries:
        raise ImportErrorWithHint("No text could be extracted from this PDF (it may be scanned images; OCR is not supported).")
    return out


def parse_html(data: bytes) -> ReferenceImport:
    p = _HTMLText()
    p.feed(_read_text(data))
    sections = [(h, "".join(parts)) for h, parts in p.sections]
    return ReferenceImport(entries=_sections_to_entries(sections), fmt="html")


def parse_epub(data: bytes) -> ReferenceImport:
    out = ReferenceImport(fmt="epub")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if n.lower().endswith((".xhtml", ".html", ".htm"))]
        # Respect the reading order from the OPF spine when available.
        opf = next((n for n in z.namelist() if n.lower().endswith(".opf")), None)
        if opf:
            try:
                root = ET.fromstring(z.read(opf))
                manifest = {i.get("id"): i.get("href") for i in root.iter() if _local(i.tag) == "item"}
                spine = [manifest.get(i.get("idref")) for i in root.iter() if _local(i.tag) == "itemref"]
                base = opf.rsplit("/", 1)[0] + "/" if "/" in opf else ""
                ordered = [base + s for s in spine if s and base + s in names]
                names = ordered + [n for n in names if n not in ordered]
                title = next((e.text for e in root.iter() if _local(e.tag) == "title" and e.text), None)
                if title:
                    out.title = clean_text(title)
            except ET.ParseError:
                pass
        for n in names:
            p = _HTMLText()
            p.feed(_read_text(z.read(n)))
            sections = [(h, "".join(parts)) for h, parts in p.sections]
            out.entries.extend(_sections_to_entries(sections))
    return out


def _entries_from_records(records: list[dict]) -> list[ReferenceEntry]:
    entries: list[ReferenceEntry] = []
    for r in records:
        low = {str(k).lower(): v for k, v in r.items()}
        text = str(low.get("text") or low.get("definition") or low.get("body") or low.get("content") or "").strip()
        if not text:
            continue
        heading = clean_text(str(low.get("term") or low.get("heading") or low.get("title") or low.get("topic") or ""))
        book = find_book(low.get("book")) if low.get("book") not in (None, "") else None
        chapter = _int(low.get("chapter"))
        vs = _int(low.get("verse_start", low.get("verse")))
        ve = _int(low.get("verse_end")) or vs
        page = _int(low.get("page"))
        fields: dict = {}
        if book and chapter:
            fields = {"book": book.number, "chapter": chapter, "verse_start": vs, "verse_end": ve}
            ref_label = f"{book.name} {chapter}" + (f":{vs}" if vs else "") + (f"-{ve}" if ve and vs and ve != vs else "")
            heading = heading or ref_label
            location = f"on {ref_label}"
        else:
            fields = _ref_fields(heading)
            location = f"p. {page}" if page else (f"“{heading}”" if heading else "")
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks, start=1):
            loc = location + (f" (part {i})" if len(chunks) > 1 else "")
            entries.append(ReferenceEntry(text=chunk, heading=heading, location=loc, page=page, **fields))
    return entries


def parse_reference(data: bytes, filename: str) -> ReferenceImport:
    name = filename.lower()
    if name.endswith(".gz"):
        import gzip
        data = gzip.decompress(data)
        name = name[:-3]
    if name.endswith(".pdf"):
        out = parse_pdf(data)
    elif name.endswith((".html", ".htm", ".xhtml")):
        out = parse_html(data)
    elif name.endswith(".epub"):
        out = parse_epub(data)
    elif name.endswith(".json"):
        obj = json.loads(_read_text(data))
        title = ""
        if isinstance(obj, dict):
            title = str(obj.get("title") or "")
            obj = obj.get("entries") or obj.get("items") or obj.get("records") or []
        if not isinstance(obj, list):
            raise ImportErrorWithHint("Reference JSON must be a list of entries (or {'entries': [...]}).")
        out = ReferenceImport(entries=_entries_from_records(obj), title=title, fmt="json")
    elif name.endswith((".csv", ".tsv")):
        text = _read_text(data)
        dialect = "excel-tab" if name.endswith(".tsv") or text.split("\n", 1)[0].count("\t") else "excel"
        out = ReferenceImport(entries=_entries_from_records(list(csv.DictReader(io.StringIO(text), dialect=dialect))), fmt="csv")
    elif name.endswith((".txt", ".md", ".markdown", ".text")):
        out = parse_plain_text(data, filename)
    else:
        raise ImportErrorWithHint("Unsupported book format. Use PDF, EPUB, HTML, text/Markdown, or JSON/CSV entries.")
    if not out.entries:
        raise ImportErrorWithHint("No text was found in this file.")
    return out


def guess_title(filename: str) -> str:
    stem = Path(filename).name
    for ext in (".gz", ".json", ".csv", ".tsv", ".zip", ".usfm", ".xml", ".txt", ".pdf", ".epub", ".md", ".html", ".htm"):
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
    return clean_text(stem.replace("_", " ").replace("-", " ")).title() or "Untitled"
