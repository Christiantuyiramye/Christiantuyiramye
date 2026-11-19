import json

import pytest

from bible_narrator.books import find_book, find_references, parse_reference
from bible_narrator.importers import ImportErrorWithHint, parse_reference as parse_ref_book, parse_scripture


@pytest.mark.parametrize("text,label", [
    ("John 3:16", "John 3:16"),
    ("Jn 3:16-18", "John 3:16-18"),
    ("Gen 1", "Genesis 1"),
    ("1 Cor 13:4-7", "1 Corinthians 13:4-7"),
    ("Genesis 1:1-2:3", "Genesis 1:1-2:3"),
    ("Ps 23", "Psalms 23"),
    ("Song of Solomon 2:1", "Song of Solomon 2:1"),
    ("ii kings 2:11", "2 Kings 2:11"),
    ("Revelation of John 21", "Revelation 21"),
])
def test_parse_reference(text, label):
    ref = parse_reference(text)
    assert ref is not None and ref.label() == label


def test_parse_reference_rejects_non_references():
    assert parse_reference("What is love?") is None
    assert parse_reference("Hello 3") is None


def test_find_book_variants():
    assert find_book("III John").number == 64
    assert find_book("GEN").number == 1
    assert find_book("Phil").number == 50
    assert find_book(66).name == "Revelation"


def test_inline_references_ignore_ordinary_words():
    assert [r.label() for r in find_references("What does John 3:16 mean?")] == ["John 3:16"]
    assert find_references("Is 3 a holy number?") == []


USFM = r"""\id JHN Test
\c 1
\s1 The Word
\p
\v 1 In the beginning was the \w Word|strong="G3056"\w*\f + \fr 1:1 \ft note\f*.
\v 2 He was with God.
\c 2
\v 1 On the third day.
"""

OSIS = """<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace"><osisText><header><work><title>Test OSIS</title></work></header>
<div type="book" osisID="Gen"><chapter osisID="Gen.1">
<verse osisID="Gen.1.1" sID="a"/>In the beginning<note>a note</note> God created.<verse eID="a"/>
<verse osisID="Gen.1.2" sID="b"/>The earth was formless.<verse eID="b"/>
</chapter></div></osisText></osis>"""

ZEFANIA = """<XMLBIBLE biblename="Zef Test"><BIBLEBOOK bnumber="19" bname="Psalms"><CHAPTER cnumber="23">
<VERS vnumber="1">The LORD is my shepherd.</VERS><VERS vnumber="2">He makes me lie down.</VERS></CHAPTER></BIBLEBOOK></XMLBIBLE>"""


def test_import_usfm_strips_markup():
    r = parse_scripture(USFM.encode(), "jhn.usfm")
    assert r.rows[0] == (43, 1, 1, "In the beginning was the Word.")
    assert (43, 2, 1, "On the third day.") in r.rows
    assert all("The Word" != t for *_, t in r.rows)  # section heading is not verse text


def test_import_osis_milestones_skip_notes():
    r = parse_scripture(OSIS.encode(), "gen.xml")
    assert r.rows[0] == (1, 1, 1, "In the beginning God created.")
    assert len(r.rows) == 2


def test_import_zefania():
    r = parse_scripture(ZEFANIA.encode(), "ps.xml")
    assert r.title == "Zef Test" and r.rows[0] == (19, 23, 1, "The LORD is my shepherd.")


def test_import_csv_tsv_vpl_json():
    csv_rows = parse_scripture(b'book,chapter,verse,text\nJohn,3,16,"For God so loved the world, that"\n', "b.csv").rows
    assert csv_rows == [(43, 3, 16, "For God so loved the world, that")]
    tsv = parse_scripture(b'book\tchapter\tverse\ttext\n1\t1\t1\tSaid "light"\n', "b.tsv").rows
    assert tsv == [(1, 1, 1, 'Said "light"')]
    vpl = parse_scripture(b"GEN 1:1 In the beginning\nJohn 1:1 The Word\n", "b.txt").rows
    assert vpl == [(1, 1, 1, "In the beginning"), (43, 1, 1, "The Word")]
    js = {"translation": "T: Test", "books": [{"name": "Jude", "chapters": [{"chapter": 1, "verses": [{"verse": 1, "text": "Jude"}]}]}]}
    assert parse_scripture(json.dumps(js).encode(), "t.json").rows == [(65, 1, 1, "Jude")]


def test_import_reports_unsupported_and_empty():
    with pytest.raises(ImportErrorWithHint):
        parse_scripture(b"nothing here", "x.txt")
    with pytest.raises(ImportErrorWithHint):
        parse_scripture(b"x", "x.docx")


def test_reference_books_keep_locations():
    md = parse_ref_book(b"# My Book\nIntro\n\n## Abraham\nFather of many.\n\n## John 3:16\nA note on the verse.", "book.md")
    locs = {e.heading: e for e in md.entries}
    assert locs["Abraham"].location == "Section: Abraham"
    assert (locs["John 3:16"].book, locs["John 3:16"].chapter, locs["John 3:16"].verse_start) == (43, 3, 16)
    paged = parse_ref_book("page one text\fpage two text".encode(), "book.txt")
    assert [e.location for e in paged.entries] == ["p. 1", "p. 2"]
    comm = parse_ref_book(b"book,chapter,verse_start,verse_end,text\nGen,22,1,2,Abraham is tested.\n", "c.csv")
    e = comm.entries[0]
    assert (e.book, e.chapter, e.verse_start, e.verse_end, e.location) == (1, 22, 1, 2, "on Genesis 22:1-2")
    dic = parse_ref_book(json.dumps([{"term": "Aaron", "text": "Brother of Moses."}]).encode(), "d.json")
    assert dic.entries[0].location == "“Aaron”"
