import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:drift/drift.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../auth/auth_notifier.dart';
import '../config/api_config.dart';
import '../db/database.dart';
import '../network/api_client.dart';
import '../network/connectivity.dart';

/// Key for the last-sync cursor stored in SharedPreferences.
const _kLastSyncedAt = 'last_synced_at';

/// Maximum times an outbox event is retried before being left for manual review.
const int maxSyncRetries = 5;

/// How often background auto-sync runs while the user is logged in.
const Duration _autoSyncInterval = Duration(minutes: 5);

/// Simple sync status for UI indicators
final syncStatusProvider = Provider<bool>((ref) {
  return !(ref.read(connectivityProvider).value ?? false);
});

final syncServiceProvider = Provider<SyncService>((ref) {
  final service = SyncService(
    db: ref.watch(appDatabaseProvider),
    client: ref.watch(apiClientProvider),
  );
  ref.onDispose(service.dispose);

  // Periodic background sync while an authenticated session is active.
  final timer = Timer.periodic(_autoSyncInterval, (_) {
    if (ref.read(authProvider) is AuthAuthenticated) {
      service.sync();
    }
  });
  ref.onDispose(timer.cancel);

  // Sync on connectivity regain.
  ref.listen(connectivityProvider, (_, next) {
    final online = next.value ?? false;
    if (online && ref.read(authProvider) is AuthAuthenticated) {
      service.sync();
    }
  });

  // Sync once right after login (auth settles into Authenticated).
  ref.listen(authProvider, (previous, next) {
    if (previous is! AuthAuthenticated && next is AuthAuthenticated) {
      service.sync();
    }
  });

  return service;
});

class SyncConflict {
  const SyncConflict({required this.clientUuid, required this.reason});
  final String clientUuid;
  final String reason;
}

class SyncService {
  SyncService({required this.db, required this.client});

  final AppDatabase db;
  final ApiClient client;

  /// Full sync cycle: push pending events, pull server changes.
  /// Returns list of conflicts that the caller should surface to the user.
  Future<List<SyncConflict>> sync() async {
    if (!await isOnline()) return [];

    final pendingItems = await db.getPendingSyncItems();
    // Cap retries: events past the limit are skipped and kept locally for review.
    final toPush = pendingItems
        .where((item) => item.retryCount < maxSyncRetries)
        .toList();
    if (toPush.isEmpty) {
      await _pullServerChanges(null);
      return [];
    }

    // Build events list (backend contract: event body + timestamp)
    final events = toPush.map((item) {
      final payload = jsonDecode(item.payload) as Map<String, dynamic>;
      return {...payload, 'timestamp': item.createdAt};
    }).toList();

    // Get last sync cursor
    final prefs = await SharedPreferences.getInstance();
    final lastSyncedAt = prefs.getString(_kLastSyncedAt);

    try {
      final resp = await client.post(
        ApiConfig.sync,
        data: {
          'events': events,
          if (lastSyncedAt != null) 'last_synced_at': lastSyncedAt,
        },
      );

      final data = resp.data as Map<String, dynamic>;
      final conflicts = <SyncConflict>[];
      final conflictedOutboxIds = <int>{};

      // Server-conflicted events: mark locally, drop from the outbox so they
      // are never re-pushed automatically.
      final serverConflicts = (data['conflicts'] as List?) ?? [];
      for (final raw in serverConflicts) {
        final c = raw as Map<String, dynamic>;
        final event = c['event'];
        String? uuid = c['client_event_id'] as String?;
        if (uuid == null && event is Map) {
          final nested = event['data'];
          if (nested is Map) uuid = nested['client_event_id'] as String?;
        }
        final reason = c['reason'] as String? ?? 'Conflict';
        if (uuid == null || uuid.isEmpty) continue;

        await db.markSaleEventConflict(uuid, reason);
        conflicts.add(SyncConflict(clientUuid: uuid, reason: reason));
        for (final item in toPush) {
          final payload = jsonDecode(item.payload) as Map<String, dynamic>;
          final itemUuid = payload['client_event_id'] as String?;
          if (itemUuid == uuid) conflictedOutboxIds.add(item.id);
        }
      }
      await db.deleteSyncItems(conflictedOutboxIds.toList());

      // Remaining pushed events were accepted — remove from outbox + mark synced.
      for (final item in toPush) {
        if (conflictedOutboxIds.contains(item.id)) continue;
        final payload = jsonDecode(item.payload) as Map<String, dynamic>;
        final uuid = payload['client_event_id'] as String?;
        await db.deleteSyncItem(item.id);
        if (uuid != null && uuid.isNotEmpty) {
          await db.markSaleEventSynced(uuid);
        }
      }

      // Pull server changes into the local mirror.
      await _pullServerChanges(data);

      // Update sync cursor
      final newCursor = data['new_sync_cursor'] as String?;
      if (newCursor != null) {
        await prefs.setString(_kLastSyncedAt, newCursor);
      }

      return conflicts;
    } catch (_) {
      // Network error — bump retry counts so items retry with a cap.
      for (final item in toPush) {
        await db.incrementRetryCount(item.id);
      }
      return [];
    }
  }

  Future<void> _pullServerChanges(Map<String, dynamic>? syncData) async {
    // If called standalone (no push), still pull server changes using the cursor.
    if (syncData == null) {
      final prefs = await SharedPreferences.getInstance();
      final lastSyncedAt = prefs.getString(_kLastSyncedAt);
      try {
        final resp = await client.post(
          ApiConfig.sync,
          data: {'events': <dynamic>[], if (lastSyncedAt != null) 'last_synced_at': lastSyncedAt},
        );
        syncData = resp.data as Map<String, dynamic>;
      } catch (_) {
        return;
      }
    }

    final serverChanges = (syncData['server_changes'] as List?) ?? [];
    for (final raw in serverChanges) {
      final sc = raw as Map<String, dynamic>;
      final data = sc['data'] as Map<String, dynamic>?;
      if (data == null) continue;
      final updatedAt = data['updated_at'] as String? ?? DateTime.now().toIso8601String();

      switch (sc['type']) {
        case 'sim_update':
          await db.upsertSimCard(LocalSimCardsCompanion(
            id: Value(data['id'] as int),
            dealerId: Value(data['dealer_id'] as int),
            serialNumber: Value(data['serial_number'] as String),
            status: Value(data['status'] as String),
            currentBranchId: Value(data['current_branch_id'] as int?),
            currentBaId: Value(data['current_ba_id'] as int?),
            expiryDate: Value(data['expiry_date'] as String?),
            updatedAt: Value(updatedAt),
          ));
        case 'ba_update':
          await db.upsertBa(LocalBrandAmbassadorsCompanion(
            id: Value(data['id'] as int),
            dealerId: Value(data['dealer_id'] as int),
            branchId: Value(data['branch_id'] as int),
            name: Value(data['name'] as String? ?? ''),
            email: Value(data['email'] as String? ?? ''),
            status: Value(data['status'] as String? ?? 'ACTIVE'),
            updatedAt: Value(updatedAt),
          ));
        case 'branch_update':
          await db.upsertBranch(LocalBranchesCompanion(
            id: Value(data['id'] as int),
            dealerId: Value(data['dealer_id'] as int),
            name: Value(data['name'] as String? ?? ''),
            type: Value(data['type'] as String? ?? 'SHOP'),
            idNumber: Value(data['id_number'] as String? ?? ''),
            photoUrl: Value(data['photo_url'] as String?),
            createdAt: Value(data['created_at'] as String? ?? updatedAt),
            updatedAt: Value(updatedAt),
          ));
        default:
          break; // sale_confirmed / stock_transfer are informational for now
      }
    }
  }

  /// Adds a sale event to the sync outbox.
  Future<void> enqueueSale({
    required String clientEventUuid,
    required String serialNumber,
    required String soldAt,
  }) async {
    final payload = jsonEncode({
      'type': 'sale',
      'data': {
        'client_event_id': clientEventUuid,
        'serial_number': serialNumber,
        'sold_at': soldAt,
      },
    });
    await db.insertPendingSyncItem(LocalPendingSyncItemsCompanion(
      eventType: const Value('SALE'),
      clientEventUuid: Value(clientEventUuid),
      payload: Value(payload),
      createdAt: Value(DateTime.now().toIso8601String()),
    ));
  }

  Future<int> getPendingCount() async {
    final items = await db.getPendingSyncItems();
    return items.length;
  }

  void dispose() {}
}