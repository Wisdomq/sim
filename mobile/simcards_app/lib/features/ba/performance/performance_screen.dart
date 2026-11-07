import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/auth/auth_notifier.dart';
import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

final _performanceProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final authState = ref.watch(authProvider);
  if (authState is! AuthAuthenticated) return {};
  final user = authState.user;
  final client = ref.read(apiClientProvider);

  final today = DateTime.now();
  final weekStart = today.subtract(Duration(days: today.weekday - 1));
  final monthStart = DateTime(today.year, today.month, 1);

  final results = await Future.wait([
    // Daily performance
    client.get(ApiConfig.commissionPerformance, queryParameters: {
      'subject_type': 'BA',
      'subject_id': user.baId,
      'period_type': 'DAILY',
      'period_start': _dateStr(today),
      'period_end': _dateStr(today),
    }),
    // Weekly performance
    client.get(ApiConfig.commissionPerformance, queryParameters: {
      'subject_type': 'BA',
      'subject_id': user.baId,
      'period_type': 'WEEKLY',
      'period_start': _dateStr(weekStart),
      'period_end': _dateStr(today),
    }),
    // Monthly performance
    client.get(ApiConfig.commissionPerformance, queryParameters: {
      'subject_type': 'BA',
      'subject_id': user.baId,
      'period_type': 'MONTHLY',
      'period_start': _dateStr(monthStart),
      'period_end': _dateStr(today),
    }),
    // Commission earned
    client.get(ApiConfig.commissionEarned, queryParameters: {
      'from_date': monthStart.toIso8601String(),
    }),
    // BA daily target is computed per-branch (see GET /commission/ba-daily-target)
    client.get(ApiConfig.commissionBaDailyTarget, queryParameters: {
      'branch_id': user.branchId,
    }),
  ]);

  return {
    'daily': results[0].data,
    'weekly': results[1].data,
    'monthly': results[2].data,
    'commission': results[3].data,
    'target': results[4].data,
  };
});

String _dateStr(DateTime d) =>
    '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// Parses values the backend may serialize as `num` or as a numeric
/// `String` (Decimal fields such as percentage_achieved / total_commission).
double toDoubleOrZero(dynamic value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

class PerformanceScreen extends ConsumerWidget {
  const PerformanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(_performanceProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Performance'),
      ),
      body: data.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.wifi_off, size: 48, color: Colors.grey),
              const SizedBox(height: 12),
              Text('Could not load data', style: Theme.of(context).textTheme.bodyLarge),
              const SizedBox(height: 8),
              Text('$e', style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.invalidate(_performanceProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (d) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(_performanceProvider),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _SectionHeader('Performance'),
              _PerformanceTile(
                period: 'Today',
                data: d['daily'],
              ),
              _PerformanceTile(
                period: 'This Week',
                data: d['weekly'],
              ),
              _PerformanceTile(
                period: 'This Month',
                data: d['monthly'],
              ),
              const SizedBox(height: 16),
              _SectionHeader('Commission Earned (This Month)'),
              _CommissionCard(data: d['commission']),
              const SizedBox(height: 16),
              _DailyTargetCard(data: d['target']),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.title);
  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, top: 4),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: const Color(0xFF4CAF50),
            ),
      ),
    );
  }
}

class _PerformanceTile extends StatelessWidget {
  const _PerformanceTile({required this.period, this.data});
  final String period;
  final dynamic data;

  @override
  Widget build(BuildContext context) {
    final pct = toDoubleOrZero(data?['percentage_achieved']);
    final actual = toDoubleOrZero(data?['actual_sold_quantity']).toInt();
    final target = toDoubleOrZero(data?['target_quantity']).toInt();

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(period,
                style: Theme.of(context)
                    .textTheme
                    .titleSmall
                    ?.copyWith(color: Colors.grey[700])),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '$actual / $target SIMs',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                Text(
                  '${pct.toStringAsFixed(1)}%',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: pct >= 100
                            ? const Color(0xFF2E7D32)
                            : pct >= 70
                                ? const Color(0xFFF57F17)
                                : const Color(0xFFD32F2F),
                      ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: (pct / 100).clamp(0, 1),
              backgroundColor: Colors.grey[200],
              color: pct >= 100
                  ? const Color(0xFF2E7D32)
                  : pct >= 70
                      ? const Color(0xFFF57F17)
                      : const Color(0xFFD32F2F),
            ),
          ],
        ),
      ),
    );
  }
}

class _CommissionCard extends StatelessWidget {
  const _CommissionCard({this.data});
  final dynamic data;

  @override
  Widget build(BuildContext context) {
    dynamic rawTotal = data?['total_commission'];
    rawTotal ??= data?['commission_earned'];
    final total = toDoubleOrZero(rawTotal);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            const Icon(Icons.payments_outlined, size: 36, color: Color(0xFF4CAF50)),
            const SizedBox(width: 16),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Total earned', style: Theme.of(context).textTheme.bodyMedium),
                Text(
                  'KES ${total.toStringAsFixed(2)}',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _DailyTargetCard extends StatelessWidget {
  const _DailyTargetCard({this.data});
  final dynamic data;

  @override
  Widget build(BuildContext context) {
    final dailyTarget = toDoubleOrZero(data?['daily_target_per_ba']).toInt();
    final asOf = data?['as_of'] ?? '';

    return Card(
      child: ListTile(
        leading: const Icon(Icons.flag_outlined, color: Color(0xFFF57F17)),
        title: Text(
          'Daily target: $dailyTarget SIMs per BA',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        subtitle: Text('As of $asOf'),
      ),
    );
  }
}
