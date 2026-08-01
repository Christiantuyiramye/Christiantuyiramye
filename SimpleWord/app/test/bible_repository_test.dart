import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_word/src/core/verse_ref.dart';
import 'package:simple_word/src/data/bible_repository.dart';

/// These tests run against the real Phase 0 database. Build it first:
///   cd ../content && python3 fetch_sources.py && python3 build.py
const dbPath = '../content/output/bible.sqlite';

void main() {
  if (!File(dbPath).existsSync()) {
    test('bible.sqlite present', () {
      fail(
        'Missing $dbPath — run the content pipeline first '
        '(content/fetch_sources.py then content/build.py).',
      );
    });
    return;
  }

  late BibleRepository repo;

  setUpAll(() => repo = BibleRepository.open(dbPath));
  tearDownAll(() => repo.close());

  test('four translations, BBE default', () {
    expect(repo.translations.map((t) => t.code).toSet(), {
      'BBE',
      'WEB',
      'BSB',
      'KJV',
    });
    expect(repo.defaultTranslation.code, 'BBE');
  });

  test('John 3:16 reads correctly in each translation', () {
    const ref = VerseRef(43, 3, 16);
    final bbe = repo.verse('BBE', ref)!.text;
    final kjv = repo.verse('KJV', ref)!.text;
    expect(bbe, contains('God had such love for the world'));
    expect(kjv, contains('For God so loved the world'));
  });

  test('chapters come back complete and ordered', () {
    final psalm23 = repo.chapter('BBE', const ChapterRef(19, 23));
    expect(psalm23.length, 6);
    expect(
      psalm23.map((v) => v.ref.verse).toList(),
      List.generate(6, (i) => i + 1),
    );
    final john1 = repo.chapter('WEB', const ChapterRef(43, 1));
    expect(john1.length, 51);
  });

  test('chapter navigation across the Malachi/Matthew boundary has text',
      () {
    final malachi4 = repo.chapter('BBE', const ChapterRef(39, 4));
    final matthew1 = repo.chapter('BBE', const ChapterRef(39, 4).next!);
    expect(malachi4, isNotEmpty);
    expect(matthew1.first.ref.bookNumber, 40);
    expect(matthew1.first.ref.chapter, 1);
    expect(matthew1, isNotEmpty);
  });

  test('full-text search finds and ranks results', () {
    final hits = repo.search('KJV', 'shepherd');
    expect(hits, isNotEmpty);
    expect(hits.first.snippet.toLowerCase(), contains('shepherd'));
    // Quoting protects against FTS syntax injection.
    expect(() => repo.search('KJV', 'faith AND "hope'), returnsNormally);
  });

  test('search respects the translation it is given', () {
    // BBE's controlled vocabulary never uses the word "shepherd".
    expect(repo.search('BBE', 'shepherd'), isEmpty);
    expect(repo.search('BBE', 'keeper of sheep'), isNotEmpty);
  });

  test('verse of the day is stable within a day and always resolves', () {
    final today = DateTime(2026, 8, 1);
    final a = repo.verseOfTheDay(today);
    final b = repo.verseOfTheDay(today);
    expect(a, b);
    expect(repo.verse('BBE', a), isNotNull);
    // A different day may give a different verse, and it must also resolve.
    final other = repo.verseOfTheDay(DateTime(2026, 8, 2));
    expect(repo.verse('BBE', other), isNotNull);
  });
}
