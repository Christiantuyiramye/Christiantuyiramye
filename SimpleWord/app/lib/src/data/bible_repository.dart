import 'package:sqlite3/sqlite3.dart';

import '../core/verse_ref.dart';

class TranslationInfo {
  final int id;
  final String code;
  final String name;
  final String license;
  final bool isDefault;

  const TranslationInfo(
    this.id,
    this.code,
    this.name,
    this.license,
    this.isDefault,
  );
}

class Verse {
  final VerseRef ref;
  final String text;

  const Verse(this.ref, this.text);
}

class SearchHit {
  final VerseRef ref;
  final String snippet;

  const SearchHit(this.ref, this.snippet);
}

/// Read-only access to the bundled bible.sqlite.
///
/// Views never touch this directly; screens go through their view models
/// (or, in the current skeleton, receive query results from callers).
class BibleRepository {
  final Database _db;
  late final List<TranslationInfo> translations;
  // (translationId, bookNumber) -> books.id in the database
  final Map<int, Map<int, int>> _bookIds = {};

  BibleRepository.open(String path) : _db = sqlite3.open(path, mutex: true) {
    translations = _db
        .select(
          'SELECT id, code, name, license, is_default FROM translations '
          'ORDER BY id',
        )
        .map(
          (r) => TranslationInfo(
            r['id'] as int,
            r['code'] as String,
            r['name'] as String,
            r['license'] as String,
            (r['is_default'] as int) == 1,
          ),
        )
        .toList();
    for (final t in translations) {
      final m = <int, int>{};
      for (final r in _db.select(
        'SELECT number, id FROM books WHERE translation_id = ?',
        [t.id],
      )) {
        m[r['number'] as int] = r['id'] as int;
      }
      _bookIds[t.id] = m;
    }
  }

  TranslationInfo get defaultTranslation =>
      translations.firstWhere((t) => t.isDefault);

  TranslationInfo translationByCode(String code) =>
      translations.firstWhere((t) => t.code == code);

  /// All verses of one chapter, in order.
  List<Verse> chapter(String translationCode, ChapterRef ref) {
    final t = translationByCode(translationCode);
    final bookId = _bookIds[t.id]![ref.bookNumber]!;
    final rows = _db.select(
      'SELECT v.number, v.text FROM verses v '
      'JOIN chapters c ON v.chapter_id = c.id '
      'WHERE c.book_id = ? AND c.number = ? ORDER BY v.number',
      [bookId, ref.chapter],
    );
    return rows
        .map(
          (r) => Verse(
            VerseRef(ref.bookNumber, ref.chapter, r['number'] as int),
            r['text'] as String,
          ),
        )
        .toList();
  }

  /// A single verse, or null when the translation omits it.
  Verse? verse(String translationCode, VerseRef ref) {
    final t = translationByCode(translationCode);
    final bookId = _bookIds[t.id]![ref.bookNumber]!;
    final rows = _db.select(
      'SELECT v.text FROM verses v '
      'JOIN chapters c ON v.chapter_id = c.id '
      'WHERE c.book_id = ? AND c.number = ? AND v.number = ?',
      [bookId, ref.chapter, ref.verse],
    );
    if (rows.isEmpty) return null;
    return Verse(ref, rows.first['text'] as String);
  }

  /// FTS5 search within one translation, ranked by relevance.
  /// The query is quoted per-token so user input cannot inject FTS syntax.
  List<SearchHit> search(
    String translationCode,
    String query, {
    int limit = 50,
  }) {
    final tokens = query
        .split(RegExp(r'\s+'))
        .where((w) => w.isNotEmpty)
        .map((w) => '"${w.replaceAll('"', '')}"')
        .join(' ');
    if (tokens.isEmpty) return const [];
    final t = translationByCode(translationCode);
    final rows = _db.select(
      'SELECT b.number AS book, c.number AS chapter, v.number AS verse, '
      "snippet(verses_fts, 0, '‹', '›', '…', 20) AS snip "
      'FROM verses_fts '
      'JOIN verses v ON verses_fts.rowid = v.id '
      'JOIN chapters c ON v.chapter_id = c.id '
      'JOIN books b ON c.book_id = b.id '
      'WHERE verses_fts MATCH ? AND b.translation_id = ? '
      'ORDER BY rank LIMIT ?',
      [tokens, t.id, limit],
    );
    return rows
        .map(
          (r) => SearchHit(
            VerseRef(
              r['book'] as int,
              r['chapter'] as int,
              r['verse'] as int,
            ),
            r['snip'] as String,
          ),
        )
        .toList();
  }

  /// Today's verse from the curated bundled list.
  VerseRef verseOfTheDay(DateTime today) {
    final count = _db
        .select('SELECT COUNT(*) AS n FROM verse_of_the_day')
        .first['n'] as int;
    final dayNumber =
        today.difference(DateTime(today.year, 1, 1)).inDays +
            (today.year * 366);
    final row = _db.select(
      'SELECT verse_ref FROM verse_of_the_day WHERE day_index = ?',
      [dayNumber % count],
    ).first;
    return VerseRef.parseStorage(row['verse_ref'] as String);
  }

  void close() => _db.dispose();
}
