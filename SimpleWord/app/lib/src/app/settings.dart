import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/verse_ref.dart';

enum ReaderTheme { light, sepia, dark, black }

/// User preferences + "continue reading" position.
/// Backed by SharedPreferences; a fuller user-data store arrives with the
/// habit engine phase.
class Settings extends ChangeNotifier {
  static const _keyTheme = 'theme';
  static const _keyFontStep = 'fontStep';
  static const _keyTranslation = 'translation';
  static const _keyLastBook = 'lastBook';
  static const _keyLastChapter = 'lastChapter';

  final SharedPreferences _prefs;

  Settings(this._prefs);

  static Future<Settings> load() async =>
      Settings(await SharedPreferences.getInstance());

  ReaderTheme get theme =>
      ReaderTheme.values[_prefs.getInt(_keyTheme) ?? ReaderTheme.light.index];

  set theme(ReaderTheme value) {
    _prefs.setInt(_keyTheme, value.index);
    notifyListeners();
  }

  /// 0..6 — seven font-size steps per the brief.
  int get fontStep => _prefs.getInt(_keyFontStep) ?? 2;

  set fontStep(int value) {
    _prefs.setInt(_keyFontStep, value.clamp(0, 6));
    notifyListeners();
  }

  double get fontSize => 15.0 + 2.0 * fontStep;

  String get translationCode => _prefs.getString(_keyTranslation) ?? 'BBE';

  set translationCode(String value) {
    _prefs.setString(_keyTranslation, value);
    notifyListeners();
  }

  /// Land in John 1 on first launch, per the brief's onboarding target.
  ChapterRef get lastChapter => ChapterRef(
        _prefs.getInt(_keyLastBook) ?? 43,
        _prefs.getInt(_keyLastChapter) ?? 1,
      );

  set lastChapter(ChapterRef ref) {
    _prefs.setInt(_keyLastBook, ref.bookNumber);
    _prefs.setInt(_keyLastChapter, ref.chapter);
    // No notify: saving the reading position must not rebuild the reader.
  }
}
