import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/db/database.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Initialise Drift database (also registers sqlite3 on Android)
  final db = AppDatabase();
  runApp(
    ProviderScope(
      overrides: [appDatabaseProvider.overrideWithValue(db)],
      child: const SimCardsApp(),
    ),
  );
}
