/// Canonical 66-book metadata, mirroring the table in content/build.py.
/// Book numbers are 1-based and stable; they are the only book identifier
/// ever stored.
library;

class BookInfo {
  final int number;
  final String name;
  final String shortName;
  final bool isOldTestament;
  final int chapterCount;

  const BookInfo(
    this.number,
    this.name,
    this.shortName,
    this.isOldTestament,
    this.chapterCount,
  );
}

const List<BookInfo> books = [
  BookInfo(1, 'Genesis', 'Gen', true, 50),
  BookInfo(2, 'Exodus', 'Exo', true, 40),
  BookInfo(3, 'Leviticus', 'Lev', true, 27),
  BookInfo(4, 'Numbers', 'Num', true, 36),
  BookInfo(5, 'Deuteronomy', 'Deu', true, 34),
  BookInfo(6, 'Joshua', 'Jos', true, 24),
  BookInfo(7, 'Judges', 'Jdg', true, 21),
  BookInfo(8, 'Ruth', 'Rut', true, 4),
  BookInfo(9, '1 Samuel', '1Sa', true, 31),
  BookInfo(10, '2 Samuel', '2Sa', true, 24),
  BookInfo(11, '1 Kings', '1Ki', true, 22),
  BookInfo(12, '2 Kings', '2Ki', true, 25),
  BookInfo(13, '1 Chronicles', '1Ch', true, 29),
  BookInfo(14, '2 Chronicles', '2Ch', true, 36),
  BookInfo(15, 'Ezra', 'Ezr', true, 10),
  BookInfo(16, 'Nehemiah', 'Neh', true, 13),
  BookInfo(17, 'Esther', 'Est', true, 10),
  BookInfo(18, 'Job', 'Job', true, 42),
  BookInfo(19, 'Psalms', 'Psa', true, 150),
  BookInfo(20, 'Proverbs', 'Pro', true, 31),
  BookInfo(21, 'Ecclesiastes', 'Ecc', true, 12),
  BookInfo(22, 'Song of Solomon', 'Sng', true, 8),
  BookInfo(23, 'Isaiah', 'Isa', true, 66),
  BookInfo(24, 'Jeremiah', 'Jer', true, 52),
  BookInfo(25, 'Lamentations', 'Lam', true, 5),
  BookInfo(26, 'Ezekiel', 'Ezk', true, 48),
  BookInfo(27, 'Daniel', 'Dan', true, 12),
  BookInfo(28, 'Hosea', 'Hos', true, 14),
  BookInfo(29, 'Joel', 'Jol', true, 3),
  BookInfo(30, 'Amos', 'Amo', true, 9),
  BookInfo(31, 'Obadiah', 'Oba', true, 1),
  BookInfo(32, 'Jonah', 'Jon', true, 4),
  BookInfo(33, 'Micah', 'Mic', true, 7),
  BookInfo(34, 'Nahum', 'Nam', true, 3),
  BookInfo(35, 'Habakkuk', 'Hab', true, 3),
  BookInfo(36, 'Zephaniah', 'Zep', true, 3),
  BookInfo(37, 'Haggai', 'Hag', true, 2),
  BookInfo(38, 'Zechariah', 'Zec', true, 14),
  BookInfo(39, 'Malachi', 'Mal', true, 4),
  BookInfo(40, 'Matthew', 'Mat', false, 28),
  BookInfo(41, 'Mark', 'Mrk', false, 16),
  BookInfo(42, 'Luke', 'Luk', false, 24),
  BookInfo(43, 'John', 'Jhn', false, 21),
  BookInfo(44, 'Acts', 'Act', false, 28),
  BookInfo(45, 'Romans', 'Rom', false, 16),
  BookInfo(46, '1 Corinthians', '1Co', false, 16),
  BookInfo(47, '2 Corinthians', '2Co', false, 13),
  BookInfo(48, 'Galatians', 'Gal', false, 6),
  BookInfo(49, 'Ephesians', 'Eph', false, 6),
  BookInfo(50, 'Philippians', 'Php', false, 4),
  BookInfo(51, 'Colossians', 'Col', false, 4),
  BookInfo(52, '1 Thessalonians', '1Th', false, 5),
  BookInfo(53, '2 Thessalonians', '2Th', false, 3),
  BookInfo(54, '1 Timothy', '1Ti', false, 6),
  BookInfo(55, '2 Timothy', '2Ti', false, 4),
  BookInfo(56, 'Titus', 'Tit', false, 3),
  BookInfo(57, 'Philemon', 'Phm', false, 1),
  BookInfo(58, 'Hebrews', 'Heb', false, 13),
  BookInfo(59, 'James', 'Jas', false, 5),
  BookInfo(60, '1 Peter', '1Pe', false, 5),
  BookInfo(61, '2 Peter', '2Pe', false, 3),
  BookInfo(62, '1 John', '1Jn', false, 5),
  BookInfo(63, '2 John', '2Jn', false, 1),
  BookInfo(64, '3 John', '3Jn', false, 1),
  BookInfo(65, 'Jude', 'Jud', false, 1),
  BookInfo(66, 'Revelation', 'Rev', false, 22),
];

BookInfo bookByNumber(int number) => books[number - 1];
