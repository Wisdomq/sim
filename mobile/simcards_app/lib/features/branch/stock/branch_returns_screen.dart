import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

final _pendingReturnsProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(
    ApiConfig.returnRequests,
    queryParameters: {'status_filter': 'REQUESTED'},
  );
  return resp.data as List? ?? [];
});

class BranchReturnsScreen extends ConsumerWidget {
  const BranchReturnsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final returnsAsync = ref.watch(_pendingReturnsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Stock Returns')),
      body: returnsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (requests) {
          if (requests.isEmpty) {
            return const Center(child: Text('No pending return requests. All resolved!'));
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(_pendingReturnsProvider),
            child: ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: requests.length,
              itemBuilder: (context, i) {
                final r = requests[i] as Map<String, dynamic>;
                final id = r['id'];
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: const Icon(Icons.undo, color: Color(0xFFF57F17)),
                    title: Text('SIM ${r['serial_number'] ?? r['sim_card_id']}'),
                    subtitle: Text(
                      r['reason'] != null && r['reason'] != ''
                          ? '${r['reason']}\nRequested ${r['return_date']}'
                          : 'Requested ${r['return_date']}',
                    ),
                    trailing: FilledButton.tonal(
                      onPressed: () async {
                        try {
                          final client = ref.read(apiClientProvider);
                          await client.post('${ApiConfig.returnRequests}/$id/fulfill');
                          ref.invalidate(_pendingReturnsProvider);
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                  content: Text('SIM returned to branch stock')),
                            );
                          }
                        } catch (e) {
                          final data = (e as dynamic).response?.data;
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                  content:
                                      Text('Fulfill failed: ${data?['detail'] ?? e}')),
                            );
                          }
                        }
                      },
                      child: const Text('Fulfill'),
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}