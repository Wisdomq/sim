import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/auth/auth_notifier.dart';
import '../../../core/db/database.dart';

final baStockProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final authState = ref.watch(authProvider);
  if (authState is! AuthAuthenticated) {
    return {'assigned': <LocalSimCard>[], 'sold': <LocalSimCard>[]};
  }
  final baId = authState.user.baId;
  if (baId == null) {
    return {'assigned': <LocalSimCard>[], 'sold': <LocalSimCard>[]};
  }
  final db = ref.read(appDatabaseProvider);
  final sims = await db.getSimCardsForBa(baId);
  final assigned = sims.where((s) => s.status == 'WITH_BA').toList();
  final sold = sims.where((s) => s.status == 'SOLD').toList();
  return {
    'assigned': assigned,
    'sold': sold,
  };
});

class BaStockScreen extends ConsumerWidget {
  const BaStockScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stock = ref.watch(baStockProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('My Stock')),
      body: stock.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (d) {
          final assigned = d['assigned'] as List<LocalSimCard>;
          final sold = d['sold'] as List<LocalSimCard>;

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(baStockProvider),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _Stat(label: 'Assigned', value: assigned.length,
                            color: const Color(0xFF1976D2)),
                        _Stat(label: 'Sold', value: sold.length,
                            color: const Color(0xFF2E7D32)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                _sectionTitle(context, 'Assigned to me (${assigned.length})'),
                if (assigned.isEmpty)
                  const _EmptyHint('No SIMs assigned to you yet.')
                else
                  ...assigned.map((s) => _SimTile(s: s, sold: false)),
                const SizedBox(height: 16),
                _sectionTitle(context, 'Sold (${sold.length})'),
                if (sold.isEmpty)
                  const _EmptyHint('No sales recorded yet.')
                else
                  ...sold.map((s) => _SimTile(s: s, sold: true)),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _sectionTitle(BuildContext context, String text) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(
          text,
          style: Theme.of(context).textTheme.titleSmall,
        ),
      );
}

class _SimTile extends StatelessWidget {
  const _SimTile({required this.s, required this.sold});
  final LocalSimCard s;
  final bool sold;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      leading: Icon(
        sold ? Icons.check_circle_outline : Icons.sim_card,
        size: 20,
        color: sold ? const Color(0xFF2E7D32) : null,
      ),
      title: Text(s.serialNumber),
      subtitle: Text('Expires ${s.expiryDate ?? '—'}'),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value, required this.color});
  final String label;
  final int value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text('$value',
            style: Theme.of(context)
                .textTheme
                .titleLarge
                ?.copyWith(fontWeight: FontWeight.bold, color: color)),
        const SizedBox(height: 4),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

class _EmptyHint extends StatelessWidget {
  const _EmptyHint(this.message);
  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 4, bottom: 12),
      child: Text(message, style: Theme.of(context).textTheme.bodySmall),
    );
  }
}