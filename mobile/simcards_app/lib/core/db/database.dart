import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart' show visibleForTesting;

part 'database.g.dart';

// ---------------------------------------------------------------------------
// Tables
// ---------------------------------------------------------------------------

/// Local mirror of SimCard — only own assignments for BA; branch pool for Branch.
class LocalSimCards extends Table {
  IntColumn get id => integer()();
  IntColumn get dealerId => integer()();
  TextColumn get serialNumber => text()();
  TextColumn get status => text()(); // SimStatus enum value
  IntColumn get currentBranchId => integer().nullable()();
  IntColumn get currentBaId => integer().nullable()();
  TextColumn get expiryDate => text().nullable()(); // ISO date string
  TextColumn get updatedAt => text()(); // ISO datetime string

  @override
  Set<Column> get primaryKey => {id};
}

/// Locally created sale events — written offline, pushed on sync.
class LocalSaleEvents extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get clientEventUuid => text().unique()();
  IntColumn get simCardId => integer()();
  TextColumn get serialNumber => text()();
  TextColumn get soldAt => text()(); // ISO datetime
  BoolColumn get pendingSync => boolean().withDefault(const Constant(true))();
  BoolColumn get hasConflict => boolean().withDefault(const Constant(false))();
  TextColumn get conflictReason => text().nullable()();
  TextColumn get createdAt => text()(); // ISO datetime
}

/// Local mirror of BrandAmbassador — used by Branch and HQ roles.
class LocalBrandAmbassadors extends Table {
  IntColumn get id => integer()();
  IntColumn get dealerId => integer()();
  IntColumn get branchId => integer()();
  TextColumn get name => text()();
  TextColumn get email => text()();
  TextColumn get status => text()();
  IntColumn get soldCount => integer().withDefault(const Constant(0))();
  IntColumn get unsoldCount => integer().withDefault(const Constant(0))();
  TextColumn get updatedAt => text().withDefault(const Constant(''))();

  @override
  Set<Column> get primaryKey => {id};
}

/// Local mirror of Branch — used for branch lookup on HQ and Branch roles.
class LocalBranches extends Table {
  IntColumn get id => integer()();
  IntColumn get dealerId => integer()();
  TextColumn get name => text()();
  TextColumn get type => text()();
  TextColumn get idNumber => text()();
  TextColumn get photoUrl => text().nullable()();
  TextColumn get createdAt => text()();
  TextColumn get updatedAt => text().withDefault(const Constant(''))();

  @override
  Set<Column> get primaryKey => {id};
}

/// Generic sync outbox — one row per pending server event.
class LocalPendingSyncItems extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get eventType => text()(); // 'SALE'
  TextColumn get clientEventUuid => text().unique()();
  TextColumn get payload => text()(); // JSON string
  TextColumn get createdAt => text()();
  IntColumn get retryCount => integer().withDefault(const Constant(0))();
}

// ---------------------------------------------------------------------------
// Database
// ---------------------------------------------------------------------------

@DriftDatabase(
  tables: [
    LocalSimCards,
    LocalSaleEvents,
    LocalBrandAmbassadors,
    LocalBranches,
    LocalPendingSyncItems,
  ],
)
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @visibleForTesting
  AppDatabase.forTesting(super.executor);

  @override
  int get schemaVersion => 2;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (m) => m.createAll(),
        onUpgrade: (m, from, to) async {
          if (from < 2) {
            await m.createTable(localBranches);
            await m.addColumn(localBrandAmbassadors, localBrandAmbassadors.updatedAt);
          }
        },
      );

  static QueryExecutor _openConnection() {
    return driftDatabase(name: 'simcards_local');
  }

  // ── SimCard DAOs ─────────────────────────────────────────────────────────

  Future<List<LocalSimCard>> getSimCardsForBa(int baId) =>
      (select(localSimCards)..where((t) => t.currentBaId.equals(baId))).get();

  Future<List<LocalSimCard>> getSimCardsForBranch(int branchId) =>
      (select(localSimCards)..where((t) => t.currentBranchId.equals(branchId))).get();

  Future<LocalSimCard?> getSimCardBySerial(String serial) =>
      (select(localSimCards)..where((t) => t.serialNumber.equals(serial)))
          .getSingleOrNull();

  Future<void> upsertSimCard(LocalSimCardsCompanion card) =>
      into(localSimCards).insertOnConflictUpdate(card);

  Future<void> updateSimCardStatus(int id, String newStatus) =>
      (update(localSimCards)..where((t) => t.id.equals(id)))
          .write(LocalSimCardsCompanion(status: Value(newStatus)));

  // ── SaleEvent DAOs ───────────────────────────────────────────────────────

  Future<LocalSaleEvent> insertSaleEvent(LocalSaleEventsCompanion event) =>
      into(localSaleEvents).insertReturning(event);

  Future<bool> saleEventExists(String clientUuid) async {
    final row = await (select(localSaleEvents)
          ..where((t) => t.clientEventUuid.equals(clientUuid)))
        .getSingleOrNull();
    return row != null;
  }

  Future<List<LocalSaleEvent>> getPendingSaleEvents() =>
      (select(localSaleEvents)
            ..where((t) => t.pendingSync.equals(true))
            ..orderBy([(t) => OrderingTerm.asc(t.createdAt)]))
          .get();

  Future<void> markSaleEventSynced(String clientUuid) =>
      (update(localSaleEvents)
            ..where((t) => t.clientEventUuid.equals(clientUuid)))
          .write(const LocalSaleEventsCompanion(pendingSync: Value(false)));

  Future<void> markSaleEventConflict(String clientUuid, String reason) =>
      (update(localSaleEvents)
            ..where((t) => t.clientEventUuid.equals(clientUuid)))
          .write(LocalSaleEventsCompanion(
            pendingSync: const Value(false),
            hasConflict: const Value(true),
            conflictReason: Value(reason),
          ));

  // ── BA DAOs ──────────────────────────────────────────────────────────────

  Future<void> upsertBa(LocalBrandAmbassadorsCompanion ba) =>
      into(localBrandAmbassadors).insertOnConflictUpdate(ba);

  Future<List<LocalBrandAmbassador>> getBas(int branchId) =>
      (select(localBrandAmbassadors)
            ..where((t) => t.branchId.equals(branchId)))
          .get();

  // ── Branch DAOs ──────────────────────────────────────────────────────────

  Future<void> upsertBranch(LocalBranchesCompanion branch) =>
      into(localBranches).insertOnConflictUpdate(branch);

  Future<List<LocalBranche>> getBranches() => select(localBranches).get();

  // ── Pending Sync Item DAOs ───────────────────────────────────────────────

  Future<void> insertPendingSyncItem(LocalPendingSyncItemsCompanion item) =>
      into(localPendingSyncItems).insert(item);

  Future<List<LocalPendingSyncItem>> getPendingSyncItems() =>
      (select(localPendingSyncItems)
            ..orderBy([(t) => OrderingTerm.asc(t.createdAt)]))
          .get();

  Future<void> deleteSyncItem(int id) =>
      (delete(localPendingSyncItems)..where((t) => t.id.equals(id))).go();

  Future<void> deleteSyncItems(List<int> ids) async {
    if (ids.isEmpty) return;
    await (delete(localPendingSyncItems)..where((t) => t.id.isIn(ids))).go();
  }

  Future<void> incrementRetryCount(int id) async {
    final current = await (select(localPendingSyncItems)
          ..where((t) => t.id.equals(id)))
        .getSingle();
    await (update(localPendingSyncItems)..where((t) => t.id.equals(id))).write(
      LocalPendingSyncItemsCompanion(
        retryCount: Value(current.retryCount + 1),
      ),
    );
  }
}

/// Riverpod provider — injected at startup in main.dart.
final appDatabaseProvider = Provider<AppDatabase>(
  (_) => throw UnimplementedError('Override in ProviderScope'),
);