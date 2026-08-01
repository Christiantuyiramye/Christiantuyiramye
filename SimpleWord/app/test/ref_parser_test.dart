import 'package:flutter_test/flutter_test.dart';
import 'package:simple_word/src/core/books.dart';
import 'package:simple_word/src/core/ref_parser.dart';

void main() {
  ParsedRef parse(String s) {
    final r = parseReference(s);
    expect(r, isNotNull, reason: 'should parse: "$s"');
    return r!;
  }

  test('basic forms from the brief', () {
    expect(parse('jn 3:16').bookNumber, 43);
    expect(parse('jn 3:16').chapter, 3);
    expect(parse('jn 3:16').verse, 16);

    expect(parse('John 3.16').bookNumber, 43);
    expect(parse('John 3.16').verse, 16);

    expect(parse('1 cor 13').bookNumber, 46);
    expect(parse('1 cor 13').chapter, 13);
    expect(parse('1 cor 13').verse, isNull);
  });

  test('ordinal book spellings', () {
    for (final s in ['1 John 1:9', '1st John 1:9', 'I John 1:9', '1john 1:9']) {
      final r = parse(s);
      expect(r.bookNumber, 62, reason: s);
      expect(r.verse, 9, reason: s);
    }
    expect(parse('III John 1').bookNumber, 64);
    expect(parse('2nd Tim 2:15').bookNumber, 55);
  });

  test('ranges', () {
    final r = parse('Rom 8:28-30');
    expect(r.bookNumber, 45);
    expect(r.verse, 28);
    expect(r.verseEnd, 30);
  });

  test('single-chapter books accept a bare verse number', () {
    final r = parse('Jude 5');
    expect(r.bookNumber, 65);
    expect(r.chapter, 1);
    expect(r.verse, 5);
  });

  test('every canonical book name parses with chapter 1', () {
    for (final b in books) {
      final r = parseReference('${b.name} 1');
      expect(r, isNotNull, reason: b.name);
      expect(r!.bookNumber, b.number, reason: b.name);
    }
  });

  test('every short name parses', () {
    for (final b in books) {
      final r = parseReference('${b.shortName} 1');
      expect(r, isNotNull, reason: b.shortName);
      expect(r!.bookNumber, b.number, reason: b.shortName);
    }
  });

  test('chapter bounds are enforced', () {
    expect(parseReference('John 22'), isNull); // John has 21 chapters
    expect(parseReference('Ps 151'), isNull);
    expect(parseReference('Gen 0'), isNull);
  });

  test('non-references return null (fall back to text search)', () {
    expect(parseReference('love your enemies'), isNull);
    expect(parseReference('faith'), isNull);
    expect(parseReference(''), isNull);
    expect(parseReference('3:16'), isNull);
  });

  test('descending ranges are rejected', () {
    expect(parseReference('John 3:16-2'), isNull);
  });
}
