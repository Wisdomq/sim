import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';
import '../stock/assign_to_ba_dialog.dart';

final _baDetailProvider =
    FutureProvider.family<Map<String, dynamic>, int>((ref, baId) async {
  final client = ref.read(apiClientProvider);

  final results = await Future.wait([
    client.get('${ApiConfig.brandAmbassadors}/$baId'),
    client.get(ApiConfig.brandAmbassadors),
    client.get(ApiConfig.simCards, queryParameters: {'ba_id': baId, 'status_filter': 'WITH_BA'}),
    client.get(ApiConfig.simCards, queryParameters: {'ba_id': baId, 'status_filter': 'SOLD'}),
  ]);

  return {
    'ba': results[0].data,
    'bas': results[1].data,
    'assigned': results[2].data,
    'sold': results[3].data,
  };
});

class BaDetailScreen extends ConsumerWidget {
  const BaDetailScreen({super.key, required this.baId});

  final int baId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(_baDetailProvider(baId));

    return Scaffold(
      appBar: AppBar(title: const Text('BA Detail')),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (d) {
          final ba = d['ba'] as Map<String, dynamic>? ?? {};
          final bas = (d['bas'] as List?) ?? [];
          final assigned = (d['assigned'] as List?) ?? [];
          final sold = (d['sold'] as List?) ?? [];

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(_baDetailProvider(baId)),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // BA Info card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(ba['name'] as String? ?? '',
                            style: Theme.of(context).textTheme.titleLarge),
                        Text('ID: ${ba['id_number'] ?? ''}',
                            style: Theme.of(context).textTheme.bodyMedium),
                        Text('Phone: ${ba['phone_msisdn'] ?? ''}',
                            style: Theme.of(context).textTheme.bodyMedium),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            _CountChip(
                              label: 'Assigned',
                              count: assigned.length,
                              color: const Color(0xFF1976D2),
                            ),
                            const SizedBox(width: 8),
                            _CountChip(
                              label: 'Sold',
                              count: sold.length,
                              color: const Color(0xFF2E7D32),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // Actions
                OutlinedButton.icon(
                  icon: const Icon(Icons.add_circle_outline),
                  label: const Text('Assign stock to a BA'),
                  onPressed: () => _assignStock(context, ref),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        icon: const Icon(Icons.swap_horiz),
                        label: const Text('Reassign SIMs'),
                        onPressed: () => _showReassignDialog(
                          context,
                          ref,
                          ba,
                          bas,
                          assigned,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        icon: const Icon(Icons.undo),
                        label: const Text('Return SIMs'),
                        onPressed: () => _showReturnDialog(context, ref, assigned),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Assigned SIMs list
                Text('Assigned SIMs (${assigned.length})',
                    style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                if (assigned.isEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4, bottom: 8),
                    child: Text('No SIMs currently assigned.',
                        style: Theme.of(context).textTheme.bodySmall),
                  )
                else ...[
                  ...assigned.take(20).map((sim) {
                    final s = sim as Map<String, dynamic>;
                    return ListTile(
                      dense: true,
                      leading: const Icon(Icons.sim_card, size: 20),
                      title: Text(s['serial_number'] as String? ?? ''),
                    );
                  }),
                  if (assigned.length > 20)
                    Text('...and ${assigned.length - 20} more',
                        style: Theme.of(context).textTheme.bodySmall),
                ],
                const SizedBox(height: 16),

                // Sold SIMs list
                Text('Sold SIMs (${sold.length})',
                    style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                if (sold.isEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4, bottom: 8),
                    child: Text('No sales recorded yet.',
                        style: Theme.of(context).textTheme.bodySmall),
                  )
                else
                  ...sold.take(20).map((sim) {
                    final s = sim as Map<String, dynamic>;
                    return ListTile(
                      dense: true,
                      leading: const Icon(Icons.check_circle_outline,
                          size: 20, color: Color(0xFF2E7D32)),
                      title: Text(s['serial_number'] as String? ?? ''),
                    );
                  }),
              ],
            ),
          );
        },
      ),
    );
  }

  Future<void> _assignStock(BuildContext context, WidgetRef ref) async {
    final ok = await showAssignToBaDialog(context, ref);
    if (ok) ref.invalidate(_baDetailProvider(baId));
  }

  Future<void> _showReassignDialog(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> ba,
    List bas,
    List assigned,
  ) async {
    final available = bas
        .whereType<Map>()
        .where((b) => b['id'] != ba['id'])
        .toList();

    if (available.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No other BAs available to reassign to.')),
      );
      return;
    }

    final serialsCtrl = TextEditingController(
      text: assigned.map((s) => (s as Map)['serial_number'] as String).join('\n'),
    );
    int? targetBaId = available.first['id'] as int?;

    await showDialog<void>(
      context: context,
      builder: (dialogCtx) => StatefulBuilder(
        builder: (dialogCtx, setState) => AlertDialog(
          title: const Text('Reassign SIMs'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DropdownButtonFormField<int>(
                  initialValue: targetBaId,
                  decoration: const InputDecoration(labelText: 'Target BA'),
                  items: available.map((b) {
                    return DropdownMenuItem<int>(
                      value: b['id'] as int,
                      child: Text(b['name'] as String? ?? 'BA ${b['id']}'),
                    );
                  }).toList(),
                  onChanged: (v) => setState(() => targetBaId = v),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: serialsCtrl,
                  maxLines: 5,
                  decoration: const InputDecoration(
                    labelText: 'Serial numbers (one per line)',
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogCtx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                final serials = serialsCtrl.text
                    .split('\n')
                    .map((s) => s.trim())
                    .where((s) => s.isNotEmpty)
                    .toList();
                if (targetBaId == null || serials.isEmpty) return;

                try {
                  final client = ref.read(apiClientProvider);
                  await client.post(
                    ApiConfig.assignToBa,
                    data: {'ba_id': targetBaId, 'serial_numbers': serials},
                  );
                  if (dialogCtx.mounted) Navigator.pop(dialogCtx);
                  ref.invalidate(_baDetailProvider(baId));
                } catch (e) {
                  final data = (e as dynamic).response?.data;
                  if (dialogCtx.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Reassign failed: ${data?['detail'] ?? e}')),
                    );
                  }
                }
              },
              child: const Text('Reassign'),
            ),
          ],
        ),
      ),
    );
  }

  void _showReturnDialog(
      BuildContext context, WidgetRef ref, List assigned) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Return SIMs to Branch'),
        content: Text('Return all ${assigned.length} assigned SIMs back to branch?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              final serials =
                  assigned.map((s) => (s as Map)['serial_number'] as String).toList();
              final client = ref.read(apiClientProvider);
              await client.post(ApiConfig.returnToBranch, data: {
                'serial_numbers': serials,
                'reason': 'Branch return',
              });
              if (context.mounted) Navigator.pop(context);
              ref.invalidate(_baDetailProvider(baId));
            },
            child: const Text('Return'),
          ),
        ],
      ),
    );
  }
}

class _CountChip extends StatelessWidget {
  const _CountChip({required this.label, required this.count, required this.color});
  final String label;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text('$label: $count',
          style: const TextStyle(color: Colors.white, fontSize: 12)),
      backgroundColor: color,
    );
  }
}