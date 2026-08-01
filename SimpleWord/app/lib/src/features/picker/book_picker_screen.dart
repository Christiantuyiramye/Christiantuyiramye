import 'package:flutter/material.dart';

import '../../core/books.dart';
import '../../core/verse_ref.dart';

/// Two-step picker: Old/New Testament book grid, then chapter grid.
/// Pops with the chosen [ChapterRef].
class BookPickerScreen extends StatefulWidget {
  final ChapterRef initial;

  const BookPickerScreen({super.key, required this.initial});

  @override
  State<BookPickerScreen> createState() => _BookPickerScreenState();
}

class _BookPickerScreenState extends State<BookPickerScreen> {
  BookInfo? _book;

  @override
  Widget build(BuildContext context) {
    final book = _book;
    return Scaffold(
      appBar: AppBar(
        title: Text(book == null ? 'Books' : book.name),
        leading: book == null
            ? null
            : BackButton(onPressed: () => setState(() => _book = null)),
      ),
      body: book == null ? _bookGrid() : _chapterGrid(book),
    );
  }

  Widget _bookGrid() {
    return DefaultTabController(
      length: 2,
      initialIndex: widget.initial.bookNumber <= 39 ? 0 : 1,
      child: Column(
        children: [
          const TabBar(
            tabs: [
              Tab(text: 'Old Testament'),
              Tab(text: 'New Testament'),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                _testamentGrid(books.where((b) => b.isOldTestament)),
                _testamentGrid(books.where((b) => !b.isOldTestament)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _testamentGrid(Iterable<BookInfo> items) {
    final list = items.toList();
    return GridView.builder(
      padding: const EdgeInsets.all(12),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisExtent: 52,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemCount: list.length,
      itemBuilder: (context, i) {
        final b = list[i];
        return OutlinedButton(
          onPressed: () => setState(() => _book = b),
          child: Text(b.name, overflow: TextOverflow.ellipsis),
        );
      },
    );
  }

  Widget _chapterGrid(BookInfo book) {
    return GridView.builder(
      padding: const EdgeInsets.all(12),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 6,
        mainAxisExtent: 48,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemCount: book.chapterCount,
      itemBuilder: (context, i) => FilledButton.tonal(
        onPressed: () =>
            Navigator.of(context).pop(ChapterRef(book.number, i + 1)),
        child: Text('${i + 1}'),
      ),
    );
  }
}
