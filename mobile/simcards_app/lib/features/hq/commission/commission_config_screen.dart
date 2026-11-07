import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

final _rulesProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(ApiConfig.commissionRules);
  return resp.data as List? ?? [];
});

final _targetsProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(ApiConfig.commissionTargets);
  return resp.data as List? ?? [];
});

class CommissionConfigScreen extends ConsumerStatefulWidget {
  const CommissionConfigScreen({super.key});

  @override
  ConsumerState<CommissionConfigScreen> createState() => _CommissionConfigScreenState();
}

class _CommissionConfigScreenState extends ConsumerState<CommissionConfigScreen> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Commission Configuration'),
          bottom: TabBar(
            onTap: (i) => setState(() => _tab = i),
            tabs: [
              Tab(text: 'Rules'),
              Tab(text: 'Targets'),
            ],
          ),
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: () async {
            await (_tab == 0
                ? _showCreateRuleDialog()
                : _showCreateTargetDialog());
            ref.invalidate(_tab == 0 ? _rulesProvider : _targetsProvider);
          },
          icon: Icon(_tab == 0 ? Icons.add : Icons.flag_outlined),
          label: Text(_tab == 0 ? 'New Rule' : 'New Target'),
        ),
        body: TabBarView(
          children: [
            _RuleList(onCreate: () {}),
            _TargetList(onCreate: () {}),
          ],
        ),
      ),
    );
  }

  Future<void> _showCreateRuleDialog() async {
    final nameCtrl = TextEditingController();
    final amountCtrl = TextEditingController();
    late DateTime from = DateTime.now();
    DateTime? to;

    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          title: const Text('Create Commission Rule'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(labelText: 'Rule name'),
                ),
                TextField(
                  controller: amountCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Amount per SIM (KES)'),
                ),
                const SizedBox(height: 8),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Effective from'),
                  subtitle: Text('$from'.replaceAll('UTC', '')),
                  trailing: const Icon(Icons.calendar_today, size: 18),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: ctx,
                      initialDate: from,
                      firstDate: DateTime(2020),
                      lastDate: DateTime(2030),
                    );
                    if (picked != null) setState(() => from = picked);
                  },
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Effective until (optional)'),
                  subtitle: Text(to == null ? 'Open-ended' : '$to'.replaceAll('UTC', '')),
                  trailing: const Icon(Icons.calendar_today, size: 18),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: ctx,
                      initialDate: to ?? from,
                      firstDate: DateTime(2020),
                      lastDate: DateTime(2030),
                    );
                    if (picked != null) setState(() => to = picked);
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                final amount = double.tryParse(amountCtrl.text.trim());
                if (nameCtrl.text.trim().isEmpty || amount == null || amount <= 0) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    const SnackBar(content: Text('Enter a name and a positive amount.')),
                  );
                  return;
                }
                try {
                  final client = ref.read(apiClientProvider);
                  await client.post(ApiConfig.commissionRules, data: {
                    'name': nameCtrl.text.trim(),
                    'amount_per_sim': amountCtrl.text.trim(),
                    'effective_from': from.toUtc().toIso8601String(),
                    if (to != null) 'effective_to': to!.toUtc().toIso8601String(),
                  });
                  if (ctx.mounted) Navigator.pop(ctx);
                } catch (e) {
                  final data = (e as dynamic).response?.data;
                  if (ctx.mounted) {
                    ScaffoldMessenger.of(ctx).showSnackBar(
                      SnackBar(content: Text('Failed: ${data?['detail'] ?? e}')),
                    );
                  }
                }
              },
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showCreateTargetDialog() async {
    final quantityCtrl = TextEditingController();
    int? branchId;
    String periodType = 'DAILY';
    late DateTime from = DateTime.now();
    List branches = [];

    try {
      final client = ref.read(apiClientProvider);
      final resp = await client.get(ApiConfig.branches);
      branches = resp.data as List? ?? [];
      branchId = branches.isNotEmpty ? (branches.first as Map)['id'] as int : null;
    } catch (_) {}

    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          title: const Text('Create Branch Target'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (branches.isNotEmpty)
                  DropdownButtonFormField<int>(
                    initialValue: branchId,
                    decoration: const InputDecoration(labelText: 'Branch'),
                    items: branches.map((b) {
                      final m = b as Map;
                      return DropdownMenuItem<int>(
                        value: m['id'] as int,
                        child: Text(m['name'] as String? ?? 'Branch ${m['id']}'),
                      );
                    }).toList(),
                    onChanged: (v) => setState(() => branchId = v),
                  )
                else
                  const Text('No branches available',
                      style: TextStyle(color: Colors.grey)),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  initialValue: periodType,
                  decoration: const InputDecoration(labelText: 'Period'),
                  items: const [
                    DropdownMenuItem(value: 'DAILY', child: Text('Daily')),
                    DropdownMenuItem(value: 'WEEKLY', child: Text('Weekly')),
                    DropdownMenuItem(value: 'MONTHLY', child: Text('Monthly')),
                  ],
                  onChanged: (v) => setState(() => periodType = v ?? 'DAILY'),
                ),
                TextField(
                  controller: quantityCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Quantity target'),
                ),
                const SizedBox(height: 8),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Effective from'),
                  subtitle: Text('$from'.replaceAll('UTC', '')),
                  trailing: const Icon(Icons.calendar_today, size: 18),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: ctx,
                      initialDate: from,
                      firstDate: DateTime(2020),
                      lastDate: DateTime(2030),
                    );
                    if (picked != null) setState(() => from = picked);
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                final qty = int.tryParse(quantityCtrl.text.trim());
                if (branchId == null || qty == null || qty <= 0) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    const SnackBar(content: Text('Pick a branch and a valid quantity.')),
                  );
                  return;
                }
                try {
                  final client = ref.read(apiClientProvider);
                  await client.post(ApiConfig.commissionTargets, data: {
                    'branch_id': branchId,
                    'period_type': periodType,
                    'quantity': qty,
                    'effective_from': from.toUtc().toIso8601String(),
                  });
                  if (ctx.mounted) Navigator.pop(ctx);
                } catch (e) {
                  final data = (e as dynamic).response?.data;
                  if (ctx.mounted) {
                    ScaffoldMessenger.of(ctx).showSnackBar(
                      SnackBar(content: Text('Failed: ${data?['detail'] ?? e}')),
                    );
                  }
                }
              },
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );
  }
}

class _RuleList extends ConsumerWidget {
  const _RuleList({required this.onCreate});
  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rules = ref.watch(_rulesProvider);
    return rules.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
      data: (list) => list.isEmpty
          ? const Center(child: Text('No commission rules yet'))
          : RefreshIndicator(
              onRefresh: () async => ref.invalidate(_rulesProvider),
              child: ListView.builder(
                padding: const EdgeInsets.only(bottom: 88),
                itemCount: list.length,
                itemBuilder: (_, i) {
                  final r = list[i] as Map<String, dynamic>;
                  return ListTile(
                    leading: const Icon(Icons.local_atm, color: Color(0xFF4CAF50)),
                    title: Text(r['name'] as String? ?? ''),
                    subtitle: Text(
                      'KES ${r['amount_per_sim']} · from ${r['effective_from']}'
                      '${r['effective_to'] != null ? ' to ${r['effective_to']}' : ' (open)'}',
                    ),
                  );
                },
              ),
            ),
    );
  }
}

class _TargetList extends ConsumerWidget {
  const _TargetList({required this.onCreate});
  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final targets = ref.watch(_targetsProvider);
    return targets.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
      data: (list) => list.isEmpty
          ? const Center(child: Text('No targets created yet'))
          : RefreshIndicator(
              onRefresh: () async => ref.invalidate(_targetsProvider),
              child: ListView.builder(
                padding: const EdgeInsets.only(bottom: 88),
                itemCount: list.length,
                itemBuilder: (_, i) {
                  final t = list[i] as Map<String, dynamic>;
                  return ListTile(
                    leading: const Icon(Icons.flag_outlined, color: Color(0xFF1976D2)),
                    title: Text(
                        'Branch ${t['branch_id']} · ${t['period_type']} · ${t['quantity']} SIMs'),
                    subtitle:
                        Text('From ${t['effective_from']} ${t['effective_to'] != null ? 'to ${t['effective_to']}' : ''}'),
                  );
                },
              ),
            ),
    );
  }
}