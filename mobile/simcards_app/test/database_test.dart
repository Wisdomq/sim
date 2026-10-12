import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:simcards_app/core/db/database.dart';

void main() {
  group('AppDatabase', () {
    late AppDatabase db;

    setUp(() => db = AppDatabase.forTesting(NativeDatabase.memory()));
    tearDown(() => db.close());

    test('schema is version 2 with Branch and BA mirror tables', () async {
      expect(db.schemaVersion, 2);

      await db.upsertBranch(LocalBranchesCompanion(
        id: const Value(1),
        dealerId: const Value(1),
        name: const Value('Nairobi'),
        type: const Value('BRANCH'),
        idNumber: const Value('BR-001'),
        createdAt: Value(DateTime.now().toIso8601String()),
        updatedAt: const Value('2026-01-01T00:00:00Z'),
      ));

      final branches = await db.getBranches();
      expect(branches, hasLength(1));
      expect(branches.first.name, 'Nairobi');

      await db.upsertBa(LocalBrandAmbassadorsCompanion(
        id: const Value(1),
        dealerId: const Value(1),
        branchId: const Value(1),
        name: const Value('Demo BA'),
        email: const Value('ba@example.com'),
        status: const Value('ACTIVE'),
        soldCount: const Value(0),
        unsoldCount: const Value(0),
        updatedAt: const Value('2026-01-01T00:00:00Z'),
      ));
      expect(await db.getBas(1), hasLength(1));
    });

    test('sale events are queued, conflict-marked, and never reprocessed', () async {
      final inserted = await db.insertSaleEvent(LocalSaleEventsCompanion.insert(
        clientEventUuid: 'evt-1',
        simCardId: 1,
        serialNumber: 'SER-1',
        soldAt: DateTime.now().toIso8601String(),
        createdAt: DateTime.now().toIso8601String(),
      ));
      expect(inserted.pendingSync, isTrue);

      expect((await db.getPendingSaleEvents()).where((e) => e.pendingSync), hasLength(1));

      await db.markSaleEventConflict('evt-1', 'SIM already sold elsewhere');
      final conflicted = await db.saleEventExists('evt-1');
      expect(conflicted, isTrue);
      final pending = await db.getPendingSaleEvents();
      expect(pending.where((e) => e.pendingSync), isEmpty,
          reason: 'conflicted events must leave the pending queue (no re-push)');
    });

    test('sync outbox is FIFO ordered and retry count increments', () async {
      await db.insertPendingSyncItem(LocalPendingSyncItemsCompanion.insert(
        eventType: 'SALE',
        clientEventUuid: 'u-1',
        payload: '{"type":"sale","data":{}}',
        createdAt: '2026-01-01T00:00:00Z',
      ));
      await db.insertPendingSyncItem(LocalPendingSyncItemsCompanion.insert(
        eventType: 'SALE',
        clientEventUuid: 'u-2',
        payload: '{"type":"sale","data":{}}',
        createdAt: '2026-01-01T00:01:00Z',
      ));

      final items = await db.getPendingSyncItems();
      expect(items, hasLength(2));
      expect([items[0].clientEventUuid, items[1].clientEventUuid], ['u-1', 'u-2']);

      await db.incrementRetryCount(items[0].id);
      final after = await db.getPendingSyncItems();
      expect(after.first.retryCount, 1);

      await db.deleteSyncItems([items[0].id, items[1].id]);
      expect(await db.getPendingSyncItems(), isEmpty);
    });
  });
}