import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_notifier.dart';
import '../../core/config/api_config.dart';
import '../../core/network/api_client.dart';
import '../../core/routing/router.dart';

final _branchSummaryProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  try {
    final auth = ref.read(authProvider);
    if (auth is! AuthAuthenticated) return {};
    
    final client = ref.read(apiClientProvider);
    final now = DateTime.now();
    final weekStart = now.subtract(Duration(days: now.weekday - 1));

    // Fetch weekly report for branch summary
    final resp = await client.post(
      ApiConfig.reports,
      data: {
        'period_type': 'WEEKLY',
        'period_start': '${weekStart.year}-${weekStart.month.toString().padLeft(2, '0')}-${weekStart.day.toString().padLeft(2, '0')}',
        'period_end': '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}',
      },
    );

    final data = resp.data as Map<String, dynamic>;
    final branches = (data['branch_reports'] as List?) ?? [];
    
    // Find the current user's branch
    final myBranch = branches.firstWhere(
      (b) => (b as Map<String, dynamic>)['branch_id'] == auth.user.branchId,
      orElse: () => branches.isNotEmpty ? branches.first as Map<String, dynamic> : {},
    );

    final bas = (myBranch['ba_summaries'] as List?) ?? [];

    return {
      'total_sales': myBranch['total_sales_count'] ?? 0,
      'total_commission': myBranch['total_commission_owed'] ?? 0,
      'performance': myBranch['performance_percentage'] ?? 0,
      'ba_count': bas.length,
    };
  } catch (e) {
    return {};
  }
});

class BranchHomeScreen extends ConsumerWidget {
  const BranchHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final summaryAsync = ref.watch(_branchSummaryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('SimCards — Branch'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(_branchSummaryProvider),
            tooltip: 'Refresh data',
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(authProvider.notifier).logout(),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Summary Cards
            summaryAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => _ErrorCard(
                message: 'Failed to load data',
                onRetry: () => ref.invalidate(_branchSummaryProvider),
              ),
              data: (summary) => _BranchSummaryCards(summary: summary),
            ),
            const SizedBox(height: 16),
            // Menu Grid
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              children: [
                _GridCard(
                  icon: Icons.people_outlined,
                  label: 'Brand Ambassadors',
                  onTap: () => context.push(AppRoutes.branchBas),
                ),
                _GridCard(
                  icon: Icons.inventory_2_outlined,
                  label: 'Stock',
                  onTap: () => context.push(AppRoutes.branchStock),
                ),
                _GridCard(
                  icon: Icons.undo,
                  label: 'Stock Returns',
                  onTap: () => context.push(AppRoutes.branchReturns),
                ),
                _GridCard(
                  icon: Icons.bar_chart,
                  label: 'Reports',
                  onTap: () => context.push(AppRoutes.branchReports),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _BranchSummaryCards extends StatelessWidget {
  const _BranchSummaryCards({required this.summary});

  final Map<String, dynamic> summary;

  double _toDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '') ?? 0;
  }

  @override
  Widget build(BuildContext context) {
    final sales = summary['total_sales'] ?? 0;
    final commission = _toDouble(summary['total_commission']);
    final performance = _toDouble(summary['performance']);
    final baCount = summary['ba_count'] ?? 0;

    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _SummaryCard(
                label: 'Weekly Sales',
                value: '$sales',
                icon: Icons.shopping_cart_outlined,
                color: const Color(0xFF4CAF50),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _SummaryCard(
                label: 'Commission',
                value: 'KES ${commission.toStringAsFixed(0)}',
                icon: Icons.payments_outlined,
                color: const Color(0xFF2196F3),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _SummaryCard(
                label: 'Performance',
                value: '${performance.toStringAsFixed(1)}%',
                icon: Icons.trending_up,
                color: performance >= 100
                    ? const Color(0xFF2E7D32)
                    : performance >= 70
                        ? const Color(0xFFF57F17)
                        : const Color(0xFFD32F2F),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _SummaryCard(
                label: 'Active BAs',
                value: '$baCount',
                icon: Icons.people_outline,
                color: const Color(0xFF9C27B0),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 24, color: color),
            const SizedBox(height: 8),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 4),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(Icons.error_outline, size: 32, color: Colors.red.shade700),
            const SizedBox(height: 8),
            Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.red.shade900,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: onRetry,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red.shade700,
                foregroundColor: Colors.white,
              ),
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

class _GridCard extends StatelessWidget {
  const _GridCard({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 40, color: const Color(0xFF4CAF50)),
              const SizedBox(height: 10),
              Text(
                label,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleSmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
