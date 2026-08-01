import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../app/settings.dart';
import '../../core/verse_ref.dart';
import '../../data/bible_repository.dart';
import '../picker/book_picker_screen.dart';
import '../search/search_screen.dart';

class ReaderScreen extends StatefulWidget {
  final BibleRepository repository;
  final Settings settings;

  const ReaderScreen({
    super.key,
    required this.repository,
    required this.settings,
  });

  @override
  State<ReaderScreen> createState() => _ReaderScreenState();
}

class _ReaderScreenState extends State<ReaderScreen> {
  late ChapterRef _chapter;
  final ScrollController _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    _chapter = widget.settings.lastChapter;
  }

  void _goTo(ChapterRef ref) {
    setState(() => _chapter = ref);
    widget.settings.lastChapter = ref;
    if (_scroll.hasClients) _scroll.jumpTo(0);
  }

  Future<void> _openPicker() async {
    final picked = await Navigator.of(context).push<ChapterRef>(
      MaterialPageRoute(builder: (_) => BookPickerScreen(initial: _chapter)),
    );
    if (picked != null) _goTo(picked);
  }

  Future<void> _openSearch() async {
    final picked = await Navigator.of(context).push<ChapterRef>(
      MaterialPageRoute(
        builder: (_) => SearchScreen(
          repository: widget.repository,
          translationCode: widget.settings.translationCode,
        ),
      ),
    );
    if (picked != null) _goTo(picked);
  }

  void _verseActions(Verse verse) {
    showModalBottomSheet<void>(
      context: context,
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: Text(
                verse.ref.display,
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            ListTile(
              leading: const Icon(Icons.copy),
              title: const Text('Copy'),
              onTap: () {
                Clipboard.setData(
                  ClipboardData(
                    text: '${verse.text} — ${verse.ref.display} '
                        '(${widget.settings.translationCode})',
                  ),
                );
                Navigator.of(sheetContext).pop();
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final settings = widget.settings;
    final verses = widget.repository.chapter(
      settings.translationCode,
      _chapter,
    );
    final theme = Theme.of(context);
    final bodyStyle = theme.textTheme.bodyLarge!.copyWith(
      fontSize: settings.fontSize,
      height: 1.6,
    );
    final numberStyle = bodyStyle.copyWith(
      fontSize: settings.fontSize * 0.6,
      color: theme.colorScheme.primary,
      fontFeatures: const [FontFeature.superscripts()],
    );

    return Scaffold(
      appBar: AppBar(
        title: TextButton(
          onPressed: _openPicker,
          child: Text(
            _chapter.display,
            style: theme.textTheme.titleLarge,
          ),
        ),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            tooltip: 'Search',
            onPressed: _openSearch,
          ),
          _SettingsMenu(settings: settings, repository: widget.repository),
        ],
      ),
      body: ListView(
        controller: _scroll,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        children: [
          Text.rich(
            TextSpan(
              children: [
                for (final v in verses) ...[
                  TextSpan(text: '${v.ref.verse} ', style: numberStyle),
                  TextSpan(
                    text: '${v.text}  ',
                    recognizer: null,
                  ),
                ],
              ],
            ),
            style: bodyStyle,
          ),
          const SizedBox(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (_chapter.previous != null)
                FilledButton.tonalIcon(
                  onPressed: () => _goTo(_chapter.previous!),
                  icon: const Icon(Icons.chevron_left),
                  label: Text(_chapter.previous!.display),
                )
              else
                const SizedBox.shrink(),
              if (_chapter.next != null)
                FilledButton.tonalIcon(
                  onPressed: () => _goTo(_chapter.next!),
                  icon: const Icon(Icons.chevron_right),
                  label: Text(_chapter.next!.display),
                  iconAlignment: IconAlignment.end,
                )
              else
                const SizedBox.shrink(),
            ],
          ),
          const SizedBox(height: 32),
        ],
      ),
      // Long-press actions need per-verse hit areas; the flowing-text view
      // uses a simple list fallback for now via the verse list below the
      // fold in a later iteration. Tap the verse number list instead:
      floatingActionButton: FloatingActionButton.small(
        tooltip: 'Verse actions',
        onPressed: () => _showVerseList(verses),
        child: const Icon(Icons.format_list_numbered),
      ),
    );
  }

  void _showVerseList(List<Verse> verses) {
    showModalBottomSheet<void>(
      context: context,
      builder: (_) => ListView.builder(
        itemCount: verses.length,
        itemBuilder: (_, i) => ListTile(
          dense: true,
          leading: Text('${verses[i].ref.verse}'),
          title: Text(
            verses[i].text,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          onTap: () {
            Navigator.of(context).pop();
            _verseActions(verses[i]);
          },
        ),
      ),
    );
  }
}

class _SettingsMenu extends StatelessWidget {
  final Settings settings;
  final BibleRepository repository;

  const _SettingsMenu({required this.settings, required this.repository});

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<void>(
      icon: const Icon(Icons.tune),
      tooltip: 'Reading settings',
      itemBuilder: (context) => [
        PopupMenuItem(
          enabled: false,
          child: StatefulBuilder(
            builder: (context, setLocal) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Text size'),
                Slider(
                  value: settings.fontStep.toDouble(),
                  min: 0,
                  max: 6,
                  divisions: 6,
                  onChanged: (v) {
                    settings.fontStep = v.round();
                    setLocal(() {});
                  },
                ),
                const Text('Theme'),
                Wrap(
                  spacing: 4,
                  children: [
                    for (final t in ReaderTheme.values)
                      ChoiceChip(
                        label: Text(t.name),
                        selected: settings.theme == t,
                        onSelected: (_) {
                          settings.theme = t;
                          setLocal(() {});
                        },
                      ),
                  ],
                ),
                const Text('Translation'),
                Wrap(
                  spacing: 4,
                  children: [
                    for (final t in repository.translations)
                      ChoiceChip(
                        label: Text(t.code),
                        selected: settings.translationCode == t.code,
                        onSelected: (_) {
                          settings.translationCode = t.code;
                          setLocal(() {});
                        },
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
