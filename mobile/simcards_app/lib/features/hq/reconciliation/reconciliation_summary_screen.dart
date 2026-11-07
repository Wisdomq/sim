import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';
import '../../../core/routing/router.dart';

final _reconSummaryProvider =
    FutureProvider.family<Map<String, dynamic>, int>((ref, importId) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get('${ApiConfig.reconciliationImports}/$importId');
  return resp.data as Map<String, dynamic>;
});

class ReconciliationSummaryScreen extends ConsumerWidget {
  const ReconciliationSummaryScreen({super.key, required this.importId});

  final int importId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summaryAsync = ref.watch(_reconSummaryProvider(importId));

    return Scaffold(
      appBar: AppBar(title: const Text('Reconciliation Summary')),
      body: summaryAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (data) {
          final headline = data['result'] ?? data;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Headline Summary (FR-REC-02 / AC-4)',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _Metric(
                            label: 'Confirmed Activated',
                            val: '${headline['total_confirmed_activated_by_safaricom'] ?? 0}',
                            color: Colors.green,
                          ),
                          _Metric(
                            label: 'Commission',
                            val: 'KES ${headline['total_cumulative_commission'] ?? 0}',
                            color: Colors.blue,
                          ),
                          _Metric(
                            label: 'Fraud Flagged',
                            val: '${headline['total_fraud_flagged'] ?? 0}',
                            color: Colors.red,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Mismatches (FR-REC-05)',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 12),
                      ListTile(
                        leading: const Icon(Icons.warning_amber, color: Colors.orange),
                        title: const Text('Sold in app, not activated in Safaricom'),
                        trailing: Text(
                          '${headline['unmatched_sold_not_in_safaricom_count'] ?? 0}',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ),
                      ListTile(
                        leading: const Icon(Icons.help_outline, color: Colors.purple),
                        title: const Text('In Safaricom, not recorded as sold in app'),
                        trailing: Text(
                          '${headline['unmatched_in_safaricom_not_sold_in_app_count'] ?? 0}',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                icon: const Icon(Icons.list_alt),
                label: const Text('View Line Detail (Drill-Down)'),
                onPressed: () => context.push(
                  AppRoutes.hqReconciliationDetail.replaceFirst(
                    ':importId',
                    importId.toString(),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.val, required this.color});
  final String label;
  final String val;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(val,
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(color: color, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        Text(label, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
