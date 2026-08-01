import 'books.dart';

/// Canonical verse reference: (bookNumber, chapter, verse).
///
/// Stored form is the stable string "43.3.16"; display form is "John 3:16".
/// Display strings are never stored (brief §4).
class VerseRef implements Comparable<VerseRef> {
  final int bookNumber;
  final int chapter;
  final int verse;

  const VerseRef(this.bookNumber, this.chapter, this.verse)
      : assert(bookNumber >= 1 && bookNumber <= 66),
        assert(chapter >= 1),
        assert(verse >= 1);

  /// Parses the stable storage form "43.3.16". Throws [FormatException]
  /// on malformed input.
  factory VerseRef.parseStorage(String storage) {
    final parts = storage.split('.');
    if (parts.length != 3) {
      throw FormatException('Bad verse ref: $storage');
    }
    final b = int.parse(parts[0]);
    final c = int.parse(parts[1]);
    final v = int.parse(parts[2]);
    if (b < 1 || b > 66 || c < 1 || v < 1) {
      throw FormatException('Bad verse ref: $storage');
    }
    return VerseRef(b, c, v);
  }

  String get storage => '$bookNumber.$chapter.$verse';

  String get display => '${bookByNumber(bookNumber).name} $chapter:$verse';

  @override
  int compareTo(VerseRef other) {
    if (bookNumber != other.bookNumber) {
      return bookNumber.compareTo(other.bookNumber);
    }
    if (chapter != other.chapter) return chapter.compareTo(other.chapter);
    return verse.compareTo(other.verse);
  }

  @override
  bool operator ==(Object other) =>
      other is VerseRef &&
      other.bookNumber == bookNumber &&
      other.chapter == chapter &&
      other.verse == verse;

  @override
  int get hashCode => Object.hash(bookNumber, chapter, verse);

  @override
  String toString() => display;
}

/// A chapter position (no verse), used for navigation.
class ChapterRef implements Comparable<ChapterRef> {
  final int bookNumber;
  final int chapter;

  const ChapterRef(this.bookNumber, this.chapter);

  String get display => '${bookByNumber(bookNumber).name} $chapter';

  /// The chapter after this one, crossing book boundaries
  /// (Malachi 4 -> Matthew 1). Returns null after Revelation 22.
  ChapterRef? get next {
    if (chapter < bookByNumber(bookNumber).chapterCount) {
      return ChapterRef(bookNumber, chapter + 1);
    }
    if (bookNumber < 66) return ChapterRef(bookNumber + 1, 1);
    return null;
  }

  /// The chapter before this one, crossing book boundaries.
  /// Returns null before Genesis 1.
  ChapterRef? get previous {
    if (chapter > 1) return ChapterRef(bookNumber, chapter - 1);
    if (bookNumber > 1) {
      final prevBook = bookByNumber(bookNumber - 1);
      return ChapterRef(prevBook.number, prevBook.chapterCount);
    }
    return null;
  }

  @override
  int compareTo(ChapterRef other) {
    if (bookNumber != other.bookNumber) {
      return bookNumber.compareTo(other.bookNumber);
    }
    return chapter.compareTo(other.chapter);
  }

  @override
  bool operator ==(Object other) =>
      other is ChapterRef &&
      other.bookNumber == bookNumber &&
      other.chapter == chapter;

  @override
  int get hashCode => Object.hash(bookNumber, chapter);

  @override
  String toString() => display;
}
