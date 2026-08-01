import 'books.dart';
import 'verse_ref.dart';

/// Result of parsing a typed reference like "jn 3:16" or "1 cor 13".
class ParsedRef {
  final int bookNumber;
  final int chapter;
  final int? verse;
  final int? verseEnd; // for ranges like "John 3:16-18"

  const ParsedRef(this.bookNumber, this.chapter, [this.verse, this.verseEnd]);

  ChapterRef get chapterRef => ChapterRef(bookNumber, chapter);

  VerseRef? get verseRef =>
      verse == null ? null : VerseRef(bookNumber, chapter, verse!);
}

/// Book-name aliases, all lowercase with spaces/periods removed.
/// Ordinal prefixes are normalised before lookup ("1st"/"i" -> "1").
final Map<String, int> _aliases = _buildAliases();

Map<String, int> _buildAliases() {
  final m = <String, int>{};
  void add(String alias, int book) => m[alias] = book;

  for (final b in books) {
    add(b.name.toLowerCase().replaceAll(' ', ''), b.number);
    add(b.shortName.toLowerCase(), b.number);
  }
  // Common abbreviations beyond name/shortName.
  const extra = <String, int>{
    'gn': 1, 'gen': 1,
    'ex': 2, 'exod': 2,
    'lv': 3,
    'nm': 4, 'nu': 4,
    'dt': 5, 'deut': 5,
    'josh': 6,
    'judg': 7, 'jdgs': 7,
    'ru': 8, 'rth': 8,
    '1sam': 9, '1sm': 9,
    '2sam': 10, '2sm': 10,
    '1kgs': 11, '1kin': 11,
    '2kgs': 12, '2kin': 12,
    '1chr': 13, '1chron': 13,
    '2chr': 14, '2chron': 14,
    'ezr': 15,
    'ne': 16,
    'esth': 17,
    'jb': 18,
    'ps': 19, 'psalm': 19, 'pslm': 19, 'psm': 19,
    'prov': 20, 'prv': 20,
    'eccl': 21, 'eccles': 21, 'qoh': 21,
    'song': 22, 'sos': 22, 'songofsongs': 22, 'canticles': 22,
    'is': 23,
    'jr': 24, 'jere': 24,
    'lam': 25,
    'ezek': 26, 'eze': 26,
    'dn': 27, 'dan': 27,
    'ho': 28,
    'jl': 29,
    'am': 30,
    'ob': 31, 'obad': 31,
    'jnh': 32, 'jon': 32,
    'mc': 33,
    'na': 34, 'nah': 34,
    'hb': 35, 'hab': 35,
    'zeph': 36, 'zp': 36,
    'hg': 37,
    'zech': 38, 'zc': 38,
    'ml': 39,
    'mt': 40, 'matt': 40,
    'mk': 41, 'mrk': 41,
    'lk': 42, 'luk': 42,
    'jn': 43, 'jhn': 43, 'joh': 43,
    'ac': 44, 'act': 44,
    'ro': 45, 'rm': 45,
    '1cor': 46, '1co': 46,
    '2cor': 47, '2co': 47,
    'ga': 48, 'gal': 48,
    'eph': 49,
    'phil': 50, 'php': 50, 'phili': 50,
    'col': 51,
    '1thess': 52, '1thes': 52, '1th': 52,
    '2thess': 53, '2thes': 53, '2th': 53,
    '1tim': 54, '1ti': 54,
    '2tim': 55, '2ti': 55,
    'tit': 56,
    'phlm': 57, 'philem': 57, 'phm': 57,
    'heb': 58,
    'jas': 59, 'jm': 59,
    '1pet': 60, '1pe': 60, '1pt': 60,
    '2pet': 61, '2pe': 61, '2pt': 61,
    '1jn': 62, '1john': 62, '1jhn': 62,
    '2jn': 63, '2john': 63, '2jhn': 63,
    '3jn': 64, '3john': 64, '3jhn': 64,
    'jud': 65, 'jde': 65,
    'rev': 66, 'rv': 66, 'apocalypse': 66,
  };
  extra.forEach(add);
  return m;
}

final RegExp _refPattern = RegExp(
  // book part (may contain digits/letters/spaces/periods), then chapter,
  // then optional :verse or .verse, then optional -end
  r'^\s*([1-3]?(?:st|nd|rd)?\s*\.?\s*[A-Za-z]+(?:\s+(?:of\s+)?[A-Za-z]+)*)'
  r'[\s.]+(\d+)'
  r'(?:[:.](\d+)(?:\s*-\s*(\d+))?)?\s*$',
);

/// Parses a typed reference. Returns null when the text is not a
/// reference (callers then fall back to full-text search).
ParsedRef? parseReference(String input) {
  final m = _refPattern.firstMatch(input);
  if (m == null) return null;

  var bookText = m.group(1)!.toLowerCase();
  // Normalise ordinals: "1st john", "i john", "iii john" -> "1john" etc.
  bookText = bookText
      .replaceAll('.', ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();
  bookText = bookText
      .replaceFirst(RegExp(r'^(1|1st|i)\s+'), '1')
      .replaceFirst(RegExp(r'^(2|2nd|ii)\s+'), '2')
      .replaceFirst(RegExp(r'^(3|3rd|iii)\s+'), '3');
  bookText = bookText.replaceAll(' ', '');

  final book = _aliases[bookText];
  if (book == null) return null;

  final info = bookByNumber(book);
  final chapter = int.parse(m.group(2)!);
  if (chapter < 1 || chapter > info.chapterCount) {
    // "Jude 5" style: single-chapter books accept a bare verse number.
    if (info.chapterCount == 1 && m.group(3) == null) {
      return ParsedRef(book, 1, chapter);
    }
    return null;
  }

  final verse = m.group(3) == null ? null : int.parse(m.group(3)!);
  final verseEnd = m.group(4) == null ? null : int.parse(m.group(4)!);
  if (verse != null && verse < 1) return null;
  if (verseEnd != null && (verse == null || verseEnd < verse)) return null;
  return ParsedRef(book, chapter, verse, verseEnd);
}
