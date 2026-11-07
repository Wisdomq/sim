import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

final _flagsProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(ApiConfig.flags);
  return resp.data as List? ?? [];
});

final _notificationsProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(ApiConfig.flagsNotifications);
  return resp.data as List? ?? [];
});

class FlagsScreen extends ConsumerStatefulWidget {
  const FlagsScreen({super.key});

  @override
  ConsumerState<FlagsScreen> createState() => _FlagsScreenState();
}

class _FlagsScreenState extends ConsumerState<FlagsScreen> {
  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Inactivity Flags (FR-HQ-15)'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Flags'),
              Tab(text: 'Notifications'),
            ],
          ),
        ),
        body: const TabBarView(
          children: [
            _FlagsTab(),
            _NotificationsTab(),
          ],
        ),
      ),
    );
  }
}

class _FlagsTab extends ConsumerWidget {
  const _FlagsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final flagsAsync = ref.watch(_flagsProvider);

    return flagsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
      data: (flags) {
        if (flags.isEmpty) {
          return const Center(child: Text('No inactive accounts flagged. All active!'));
        }

        return RefreshIndicator(
          onRefresh: () async => ref.invalidate(_flagsProvider),
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: flags.length,
            itemBuilder: (context, i) {
              final flag = flags[i] as Map<String, dynamic>;
              final id = flag['id'];
              final role = flag['role'] ?? 'USER';
              final flaggedAt = flag['flagged_at'] ?? '';
              final isResolved = flag['resolved_at'] != null;

              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: Icon(
                    isResolved ? Icons.check_circle_outline : Icons.flag_outlined,
                    color: isResolved ? Colors.green : Colors.red,
                  ),
                  title: Text('$role account flagged (3+ days inactive)'),
                  subtitle: Text(
                      'Flagged: $flaggedAt\nStatus: ${isResolved ? "Resolved" : "Open"}'),
                  trailing: !isResolved
                      ? Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            TextButton(
                              onPressed: () async {
                                final client = ref.read(apiClientProvider);
                                await client.post('/flags/$id/acknowledge');
                                ref.invalidate(_flagsProvider);
                              },
                              child: const Text('Acknowledge'),
                            ),
                            TextButton(
                              onPressed: () async {
                                final client = ref.read(apiClientProvider);
                                await client.post('/flags/$id/resolve');
                                ref.invalidate(_flagsProvider);
                              },
                              child: const Text('Resolve'),
                            ),
                          ],
                        )
                      : null,
                ),
              );
            },
          ),
        );
      },
    );
  }
}

class _NotificationsTab extends ConsumerWidget {
  const _NotificationsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(_notificationsProvider);

    return notificationsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
      data: (notifications) {
        if (notifications.isEmpty) {
          return const Center(child: Text('No notifications yet'));
        }

        return RefreshIndicator(
          onRefresh: () async => ref.invalidate(_notificationsProvider),
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: notifications.length,
            itemBuilder: (context, i) {
              final n = notifications[i] as Map<String, dynamic>;
              final id = n['id'];
              final isRead = n['is_read'] == true;
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: Icon(
                    Icons.notifications_outlined,
                    color: isRead ? Colors.grey : const Color(0xFF4CAF50),
                  ),
                  title: Text(n['title'] as String? ?? ''),
                  subtitle: Text(n['body'] as String? ?? ''),
                  trailing: isRead
                      ? const Text('Read', style: TextStyle(color: Colors.grey))
                      : TextButton(
                          onPressed: () async {
                            final client = ref.read(apiClientProvider);
                            await client
                                .post('${ApiConfig.notificationRead}/$id/read');
                            ref.invalidate(_notificationsProvider);
                          },
                          child: const Text('Mark read'),
                        ),
                ),
              );
            },
          ),
        );
      },
    );
  }
}