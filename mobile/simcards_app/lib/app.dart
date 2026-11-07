import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/routing/router.dart';
import 'core/sync/sync_service.dart';
import 'core/theme/app_theme.dart';

class SimCardsApp extends ConsumerWidget {
  const SimCardsApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    // Keep the background sync controller (periodic + connectivity triggers)
    // alive for the whole app session.
    ref.watch(syncServiceProvider);
    final isOffline = ref.watch(syncStatusProvider);

    return MaterialApp.router(
      title: 'SimCards',
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      routerConfig: router,
      debugShowCheckedModeBanner: false,
      builder: (context, child) {
        return ConnectivityOverlay(
          isOffline: isOffline,
          child: child ?? const SizedBox.shrink(),
        );
      },
    );
  }
}

class ConnectivityOverlay extends StatelessWidget {
  const ConnectivityOverlay({
    super.key,
    required this.isOffline,
    required this.child,
  });

  final bool isOffline;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        child,
        if (isOffline)
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: _OfflineBanner(),
          ),
      ],
    );
  }
}

class _OfflineBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.orange,
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.wifi_off, size: 16, color: Colors.white),
          const SizedBox(width: 8),
          Text(
            'Offline Mode - Data will sync when connection is restored',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w500,
                ),
          ),
        ],
      ),
    );
  }
}
