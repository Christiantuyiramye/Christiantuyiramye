import 'package:flutter_test/flutter_test.dart';
import 'package:simple_word/src/core/verse_ref.dart';

void main() {
  group('VerseRef', () {
    test('storage and display forms', () {
      const ref = VerseRef(43, 3, 16);
      expect(ref.storage, '43.3.16');
      expect(ref.display, 'John 3:16');
      expect(VerseRef.parseStorage('43.3.16'), ref);
    });

    test('rejects malformed storage strings', () {
      expect(() => VerseRef.parseStorage('43.3'), throwsFormatException);
      expect(() => VerseRef.parseStorage('67.1.1'), throwsFormatException);
      expect(() => VerseRef.parseStorage('0.1.1'), throwsFormatException);
      expect(() => VerseRef.parseStorage('a.b.c'), throwsFormatException);
    });

    test('ordering', () {
      expect(
        const VerseRef(1, 1, 1).compareTo(const VerseRef(1, 1, 2)) < 0,
        isTrue,
      );
      expect(
        const VerseRef(39, 4, 6).compareTo(const VerseRef(40, 1, 1)) < 0,
        isTrue,
      );
    });
  });

  group('ChapterRef navigation', () {
    test('crosses book boundaries forward: Malachi 4 -> Matthew 1', () {
      expect(const ChapterRef(39, 4).next, const ChapterRef(40, 1));
    });

    test('crosses book boundaries backward: Matthew 1 -> Malachi 4', () {
      expect(const ChapterRef(40, 1).previous, const ChapterRef(39, 4));
    });

    test('ends of the canon', () {
      expect(const ChapterRef(66, 22).next, isNull);
      expect(const ChapterRef(1, 1).previous, isNull);
    });

    test('within a book', () {
      expect(const ChapterRef(19, 22).next, const ChapterRef(19, 23));
      expect(const ChapterRef(19, 23).previous, const ChapterRef(19, 22));
    });
  });
}
