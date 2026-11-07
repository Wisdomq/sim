import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';
import 'assign_to_ba_dialog.dart';

final _branchStockProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(ApiConfig.simCards);
  final list = resp.data as List? ?? [];

  int inBranch = 0;
  int withBa = 0;
  int sold = 0;
  int returned = 0;

  for (final item in list) {
    final status = (item as Map)['status'] as String?;
    if (status == 'WITH_BRANCH') inBranch++;
    if (status == 'WITH_BA') withBa++;
    if (status == 'SOLD') sold++;
    if (status == 'RETURNED_TO_BRANCH' || status == 'RETURNED_TO_HQ') returned++;
  }

  return {
    'total': list.length,
    'in_branch': inBranch,
    'with_ba': withBa,
    'sold': sold,
    'returned': returned,
    'sims': list,
  };
});

class BranchStockScreen extends ConsumerWidget {
  const BranchStockScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stockAsync = ref.watch(_branchStockProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Branch Stock')),
      body: stockAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (data) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(_branchStockProvider),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Stock Summary', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _StatItem(label: 'Branch Pool', value: data['in_branch']),
                          _StatItem(label: 'With BA', value: data['with_ba']),
                          _StatItem(label: 'Sold', value: data['sold']),
                          _StatItem(label: 'Returned', value: data['returned']),
                        ],
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        icon: const Icon(Icons.add_circle_outline),
                        label: const Text('Assign stock to a BA'),
                        onPressed: () async {
                          final ok = await showAssignToBaDialog(context, ref);
                          if (ok) ref.invalidate(_branchStockProvider);
                        },
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text('SIM Inventory (${data['total']})',
                  style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 8),
              ...((data['sims'] as List).take(50).map((sim) {
                final s = sim as Map<String, dynamic>;
                return ListTile(
                  dense: true,
                  leading: const Icon(Icons.sim_card),
                  title: Text(s['serial_number'] ?? ''),
                  subtitle: Text('Status: ${s['status']}'),
                );
              })),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  const _StatItem({required this.label, required this.value});
  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text('$value',
            style: Theme.of(context)
                .textTheme
                .titleLarge
                ?.copyWith(fontWeight: FontWeight.bold, color: const Color(0xFF4CAF50))),
        const SizedBox(height: 4),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
