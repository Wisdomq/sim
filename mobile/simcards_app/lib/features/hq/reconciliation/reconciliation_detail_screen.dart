import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

const _statusOptions = <(String, String)>[
  ('All', ''),
  ('Matched', 'MATCHED'),
  ('Sold, not activated', 'SOLD_NOT_ACTIVATED'),
  ('Activated, not recorded', 'ACTIVATED_NOT_RECORDED_SOLD'),
];

class _DetailFilter {
  const _DetailFilter(this.importId, this.status);
  final int importId;
  final String? status;

  @override
  bool operator ==(Object other) =>
      other is _DetailFilter &&
      other.importId == importId &&
      other.status == status;

  @override
  int get hashCode => Object.hash(importId, status);
}

final _reconDetailProvider = FutureProvider.family<List<dynamic>, _DetailFilter>(
    (ref, filter) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(
    '${ApiConfig.reconciliationImports}/${filter.importId}/detail',
    queryParameters: {
      if (filter.status != null && filter.status!.isNotEmpty)
        'match_status': filter.status,
      'limit': 500,
    },
  );
  return resp.data as List? ?? [];
});

class ReconciliationDetailScreen extends ConsumerStatefulWidget {
  const ReconciliationDetailScreen({super.key, required this.importId});

  final int importId;

  @override
  ConsumerState<ReconciliationDetailScreen> createState() =>
      _ReconciliationDetailScreenState();
}

class _ReconciliationDetailScreenState
    extends ConsumerState<ReconciliationDetailScreen> {
  String? _statusFilter;

  @override
  Widget build(BuildContext context) {
    final detailAsync =
        ref.watch(_reconDetailProvider(_DetailFilter(widget.importId, _statusFilter)));

    return Scaffold(
      appBar: AppBar(title: const Text('Reconciliation Details')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
            child: SizedBox(
              height: 40,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _statusOptions.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, i) {
                  final (label, value) = _statusOptions[i];
                  return FilterChip(
                    label: Text(label),
                    selected: _statusFilter == value,
                    onSelected: (_) => setState(() => _statusFilter = value),
                  );
                },
              ),
            ),
          ),
          Expanded(
            child: detailAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Error: $e')),
              data: (lines) {
                if (lines.isEmpty) {
                  return const Center(child: Text('No detail lines found'));
                }

                return ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: lines.length,
                  separatorBuilder: (_, __) => const Divider(),
                  itemBuilder: (context, i) {
                    final line = lines[i] as Map<String, dynamic>;
                    final status = line['match_status'] ?? 'UNKNOWN';
                    final topUpDate = line['top_up_date'] ?? 'N/A';
                    final topUpAmt = line['top_up_amount'] ?? 0;
                    final isFraud = line['fraud_flagged'] == true;

                    Color chipColor = switch (status) {
                      'MATCHED' => Colors.green,
                      'SOLD_NOT_ACTIVATED' => Colors.orange,
                      'ACTIVATED_NOT_RECORDED_SOLD' => Colors.purple,
                      _ => Colors.grey,
                    };

                    return ListTile(
                      title: Text(
                          'SIM: ${line['serial_number'] ?? line['sim_card_id'] ?? 'Unmatched'}'),
                      subtitle: Text(
                          'Top-up: $topUpDate (KES $topUpAmt)${isFraud ? ' [FRAUD FLAGGED]' : ''}'
                          '${line['fraud_reason'] != null ? '\n${line['fraud_reason']}' : ''}'),
                      trailing: Chip(
                        label: Text(status,
                            style:
                                const TextStyle(color: Colors.white, fontSize: 10)),
                        backgroundColor: chipColor,
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}