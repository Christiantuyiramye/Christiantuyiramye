import 'package:flutter/material.dart';

import 'settings.dart';

/// The four reader themes from the brief: Light, Sepia, Dark, Black (OLED).
ThemeData themeFor(ReaderTheme theme) {
  switch (theme) {
    case ReaderTheme.light:
      return _base(
        brightness: Brightness.light,
        background: const Color(0xFFFFFFFF),
        surface: const Color(0xFFF6F6F6),
        text: const Color(0xFF1A1A1A),
      );
    case ReaderTheme.sepia:
      return _base(
        brightness: Brightness.light,
        background: const Color(0xFFF6EFDF),
        surface: const Color(0xFFEFE5CF),
        text: const Color(0xFF3D3427),
      );
    case ReaderTheme.dark:
      return _base(
        brightness: Brightness.dark,
        background: const Color(0xFF20242A),
        surface: const Color(0xFF2A2F37),
        text: const Color(0xFFE4E6EA),
      );
    case ReaderTheme.black:
      return _base(
        brightness: Brightness.dark,
        background: const Color(0xFF000000),
        surface: const Color(0xFF101010),
        text: const Color(0xFFDDDDDD),
      );
  }
}

ThemeData _base({
  required Brightness brightness,
  required Color background,
  required Color surface,
  required Color text,
}) {
  final scheme = ColorScheme.fromSeed(
    seedColor: const Color(0xFF3D6B54), // calm green: quiet, not gamified
    brightness: brightness,
    surface: background,
  );
  return ThemeData(
    colorScheme: scheme,
    scaffoldBackgroundColor: background,
    cardColor: surface,
    appBarTheme: AppBarTheme(
      backgroundColor: background,
      foregroundColor: text,
      elevation: 0,
      scrolledUnderElevation: 0.5,
    ),
    textTheme: Typography.material2021(platform: TargetPlatform.android)
        .englishLike
        .apply(bodyColor: text, displayColor: text),
    useMaterial3: true,
  );
}
