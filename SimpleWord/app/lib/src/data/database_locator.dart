import 'dart:io';

import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Copies the bundled bible.sqlite asset into the app's writable directory
/// (SQLite cannot read directly from a Flutter asset) and returns its path.
/// The copy is refreshed when the bundled asset's size changes — cheap and
/// good enough while the schema is versioned by app release.
Future<String> ensureBibleDatabase() async {
  final dir = await getApplicationSupportDirectory();
  final target = File(p.join(dir.path, 'bible.sqlite'));

  final asset = await rootBundle.load('assets/bible.sqlite');
  if (!target.existsSync() || target.lengthSync() != asset.lengthInBytes) {
    await target.writeAsBytes(
      asset.buffer.asUint8List(asset.offsetInBytes, asset.lengthInBytes),
      flush: true,
    );
  }
  return target.path;
}
