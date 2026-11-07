import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_notifier.dart';
import '../../core/config/api_config.dart';
import '../../core/db/database.dart';
import '../../core/network/api_client.dart';
import '../../core/routing/router.dart';

class BaHomeScreen extends ConsumerStatefulWidget {
  const BaHomeScreen({super.key});

  @override
  ConsumerState<BaHomeScreen> createState() => _BaHomeScreenState();
}

class _BaHomeScreenState extends ConsumerState<BaHomeScreen> {
  int _assigned = 0;
  int _sold = 0;
  Map<String, dynamic>? _dailyPerformance;
  Map<String, dynamic>? _commissionData;
  bool _isLoadingPerformance = false;

  @override
  void initState() {
    super.initState();
    _loadStock();
    _loadPerformance();
  }

  Future<void> _loadStock() async {
    final auth = ref.read(authProvider);
    if (auth is! AuthAuthenticated) return;
    final baId = auth.user.baId;
    if (baId == null) return;

    final db = ref.read(appDatabaseProvider);
    final sims = await db.getSimCardsForBa(baId);
    if (!mounted) return;
    setState(() {
      _assigned = sims.where((s) => s.status == 'WITH_BA').length;
      _sold = sims.where((s) => s.status == 'SOLD').length;
    });
  }

  Future<void> _loadPerformance() async {
    final auth = ref.read(authProvider);
    if (auth is! AuthAuthenticated) return;
    final user = auth.user;
    if (user.baId == null) return;

    setState(() => _isLoadingPerformance = true);
    try {
      final client = ref.read(apiClientProvider);
      final today = DateTime.now();

      // Fetch daily performance
      final dailyResp = await client.get(
        ApiConfig.commissionPerformance,
        queryParameters: {
          'subject_type': 'BA',
          'subject_id': user.baId,
          'period_type': 'DAILY',
          'period_start': _dateStr(today),
          'period_end': _dateStr(today),
        },
      );

      // Fetch commission for this month
      final monthStart = DateTime(today.year, today.month, 1);
      final commissionResp = await client.get(
        ApiConfig.commissionEarned,
        queryParameters: {
          'from_date': monthStart.toIso8601String(),
        },
      );

      if (mounted) {
        setState(() {
          _dailyPerformance = dailyResp.data;
          _commissionData = commissionResp.data;
          _isLoadingPerformance = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoadingPerformance = false);
      }
    }
  }

  String _dateStr(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  double _toDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '') ?? 0;
  }

  Future<void> _push(BuildContext context, String route) async {
    await context.push(route);
    _loadStock();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SimCards — BA'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(authProvider.notifier).logout(),
            tooltip: 'Sign out',
          ),
        ],
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Daily Progress Card
              _DailyProgressCard(
                performance: _dailyPerformance,
                isLoading: _isLoadingPerformance,
                onRefresh: _loadPerformance,
              ),
              const SizedBox(height: 16),
              _HomeCard(
                icon: Icons.sim_card,
                label: 'My Stock',
                subtitle: '$_assigned assigned · $_sold sold',
                color: const Color(0xFFF57F17),
                onTap: () => _push(context, AppRoutes.baStock),
              ),
              const SizedBox(height: 16),
              _HomeCard(
                icon: Icons.qr_code_scanner,
                label: 'Scan & Sell',
                color: const Color(0xFF4CAF50),
                onTap: () => _push(context, AppRoutes.baScan),
              ),
              const SizedBox(height: 16),
              _HomeCard(
                icon: Icons.bar_chart,
                label: 'My Performance',
                subtitle: _getCommissionSubtitle(),
                color: const Color(0xFF1976D2),
                onTap: () => _push(context, AppRoutes.baPerformance),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _getCommissionSubtitle() {
    if (_commissionData == null) return 'View detailed performance';
    final total = _toDouble(_commissionData?['total_commission'] ?? _commissionData?['commission_earned']);
    return 'KES ${total.toStringAsFixed(2)} this month';
  }
}

class _HomeCard extends StatelessWidget {
  const _HomeCard({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
    this.subtitle,
  });

  final IconData icon;
  final String label;
  final String? subtitle;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 24),
          child: Row(
            children: [
              Icon(icon, size: 40, color: color),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: Theme.of(context)
                          .textTheme
                          .titleLarge
                          ?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    if (subtitle != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        subtitle!,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.grey[600],
                            ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DailyProgressCard extends StatelessWidget {
  const _DailyProgressCard({
    required this.performance,
    required this.isLoading,
    required this.onRefresh,
  });

  final Map<String, dynamic>? performance;
  final bool isLoading;
  final VoidCallback onRefresh;

  double _toDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '') ?? 0;
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Center(
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: const Color(0xFF4CAF50),
            ),
          ),
        ),
      );
    }

    if (performance == null) {
      return Card(
        child: InkWell(
          onTap: onRefresh,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Icon(Icons.refresh, size: 32, color: Colors.grey[400]),
                const SizedBox(height: 8),
                Text(
                  'Tap to load today\'s progress',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.grey[600],
                      ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final actual = _toDouble(performance!['actual_sold_quantity']).toInt();
    final target = _toDouble(performance!['target_quantity']).toInt();
    final percentage = _toDouble(performance!['percentage_achieved']);
    final progressColor = percentage >= 100
        ? const Color(0xFF2E7D32) // Green
        : percentage >= 70
            ? const Color(0xFFF57F17) // Orange
            : const Color(0xFFD32F2F); // Red

    return Card(
      child: InkWell(
        onTap: () => onRefresh(),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Today\'s Progress',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: const Color(0xFF4CAF50),
                        ),
                  ),
                  Text(
                    '${percentage.toStringAsFixed(1)}%',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: progressColor,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '$actual / $target SIMs',
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                  Text(
                    target > 0 ? '${target - actual} remaining' : 'No target set',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: target > 0 ? (percentage / 100).clamp(0.0, 1.0) : 0.0,
                  backgroundColor: Colors.grey[200],
                  color: progressColor,
                  minHeight: 8,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}