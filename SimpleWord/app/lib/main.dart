import 'package:flutter/material.dart';

import 'src/app/settings.dart';
import 'src/app/theme.dart';
import 'src/data/bible_repository.dart';
import 'src/data/database_locator.dart';
import 'src/features/reader/reader_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final dbPath = await ensureBibleDatabase();
  final repository = BibleRepository.open(dbPath);
  final settings = await Settings.load();
  runApp(SimpleWordApp(repository: repository, settings: settings));
}

class SimpleWordApp extends StatelessWidget {
  final BibleRepository repository;
  final Settings settings;

  const SimpleWordApp({
    super.key,
    required this.repository,
    required this.settings,
  });

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: settings,
      builder: (context, _) => MaterialApp(
        title: 'Simple Word',
        theme: themeFor(settings.theme),
        home: ReaderScreen(repository: repository, settings: settings),
      ),
    );
  }
}
