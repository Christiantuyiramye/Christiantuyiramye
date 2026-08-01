import 'package:flutter/material.dart';

import '../../core/ref_parser.dart';
import '../../core/verse_ref.dart';
import '../../data/bible_repository.dart';

/// Search: typed references ("jn 3:16", "1 cor 13") jump straight to the
/// passage; anything else is FTS full-text search. Pops with a
/// [ChapterRef] when the user picks a destination.
class SearchScreen extends StatefulWidget {
  final BibleRepository repository;
  final String translationCode;

  const SearchScreen({
    super.key,
    required this.repository,
    required this.translationCode,
  });

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final TextEditingController _controller = TextEditingController();
  List<SearchHit> _hits = const [];
  ParsedRef? _parsed;

  void _run(String query) {
    final parsed = parseReference(query);
    setState(() {
      _parsed = parsed;
      _hits = parsed != null || query.trim().length < 2
          ? const []
          : widget.repository.search(widget.translationCode, query);
    });
  }

  @override
  Widget build(BuildContext context) {
    final parsed = _parsed;
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _controller,
          autofocus: true,
          decoration: const InputDecoration(
            hintText: 'Search, or type a reference like jn 3:16',
            border: InputBorder.none,
          ),
          textInputAction: TextInputAction.search,
          onChanged: _run,
          onSubmitted: _run,
        ),
      ),
      body: ListView(
        children: [
          if (parsed != null)
            ListTile(
              leading: const Icon(Icons.menu_book),
              title: Text(
                parsed.verse == null
                    ? parsed.chapterRef.display
                    : parsed.verseRef!.display,
              ),
              subtitle: const Text('Go to passage'),
              onTap: () => Navigator.of(context).pop(parsed.chapterRef),
            ),
          for (final hit in _hits)
            ListTile(
              title: Text(hit.snippet),
              subtitle: Text(hit.ref.display),
              onTap: () => Navigator.of(context).pop(
                ChapterRef(hit.ref.bookNumber, hit.ref.chapter),
              ),
            ),
          if (parsed == null &&
              _hits.isEmpty &&
              _controller.text.trim().length >= 2)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Text('No results in this translation.'),
            ),
        ],
      ),
    );
  }
}
