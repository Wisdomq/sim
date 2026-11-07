import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:uuid/uuid.dart';

import '../../../core/auth/auth_notifier.dart';
import '../../../core/db/database.dart';
import '../../../core/sync/sync_service.dart';
import 'package:drift/drift.dart' show Value;

/// Possible results of scanning a barcode.
enum _ScanResult { success, notMine, alreadySold, error }

class ScanScreen extends ConsumerStatefulWidget {
  const ScanScreen({super.key});

  @override
  ConsumerState<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends ConsumerState<ScanScreen> {
  final MobileScannerController _controller = MobileScannerController();
  final _uuid = const Uuid();

  _ScanResult? _lastResult;
  String? _lastSerial;
  bool _processing = false;
  int _pendingCount = 0;

  @override
  void initState() {
    super.initState();
    _refreshPendingCount();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _refreshPendingCount() async {
    final sync = ref.read(syncServiceProvider);
    final count = await sync.getPendingCount();
    if (mounted) setState(() => _pendingCount = count);
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_processing) return;
    final barcodes = capture.barcodes;
    if (barcodes.isEmpty) return;
    final rawValue = barcodes.first.rawValue;
    if (rawValue == null || rawValue.isEmpty) return;

    setState(() {
      _processing = true;
      _lastSerial = rawValue;
      _lastResult = null;
    });

    await _controller.stop();

    try {
      final db = ref.read(appDatabaseProvider);
      final authState = ref.read(authProvider);
      final user = authState is AuthAuthenticated ? authState.user : null;

      if (user == null) {
        setState(() => _lastResult = _ScanResult.error);
        return;
      }

      // Validate against local store
      final sim = await db.getSimCardBySerial(rawValue);

      if (sim == null || sim.currentBaId != user.baId) {
        setState(() => _lastResult = _ScanResult.notMine);
        return;
      }

      if (sim.status == 'SOLD') {
        setState(() => _lastResult = _ScanResult.alreadySold);
        return;
      }

      if (sim.status != 'WITH_BA') {
        setState(() => _lastResult = _ScanResult.notMine);
        return;
      }

      // Write locally
      final clientUuid = _uuid.v4();
      final soldAt = DateTime.now().toUtc().toIso8601String();

      await db.insertSaleEvent(LocalSaleEventsCompanion(
        clientEventUuid: Value(clientUuid),
        simCardId: Value(sim.id),
        serialNumber: Value(rawValue),
        soldAt: Value(soldAt),
        createdAt: Value(soldAt),
      ));

      await db.updateSimCardStatus(sim.id, 'SOLD');

      // Enqueue for sync
      final sync = ref.read(syncServiceProvider);
      await sync.enqueueSale(
        clientEventUuid: clientUuid,
        serialNumber: rawValue,
        soldAt: soldAt,
      );

      // Trigger sync opportunistically (don't await — fire and forget)
      sync.sync().then((conflicts) {
        if (conflicts.isNotEmpty && mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Conflict: ${conflicts.first.reason}'),
              backgroundColor: Colors.orange,
            ),
          );
        }
        _refreshPendingCount();
      });

      setState(() => _lastResult = _ScanResult.success);
    } catch (_) {
      setState(() => _lastResult = _ScanResult.error);
    } finally {
      // Auto-reset after 1.5s
      await Future.delayed(const Duration(milliseconds: 1500));
      if (mounted) {
        setState(() {
          _processing = false;
          _lastResult = null;
        });
        await _refreshPendingCount();
        await _controller.start();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan & Sell'),
        actions: [
          if (_pendingCount > 0)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Badge(
                label: Text('$_pendingCount'),
                child: const Icon(Icons.cloud_upload_outlined),
              ),
            ),
        ],
      ),
      body: Stack(
        children: [
          // Camera viewfinder
          MobileScanner(
            controller: _controller,
            onDetect: _onDetect,
          ),

          // Overlay
          if (_lastResult != null)
            _ScanOverlay(
              result: _lastResult!,
              serial: _lastSerial,
            ),

          // Bottom guidance text
          if (_lastResult == null)
            Positioned(
              bottom: 48,
              left: 0,
              right: 0,
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 32),
                padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  'Point the camera at a SIM card barcode',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white, fontSize: 14),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ScanOverlay extends StatelessWidget {
  const _ScanOverlay({required this.result, this.serial});

  final _ScanResult result;
  final String? serial;

  @override
  Widget build(BuildContext context) {
    final (icon, message, color) = switch (result) {
      _ScanResult.success => (
          Icons.check_circle,
          'Sold!\n${serial ?? ''}',
          const Color(0xFF2E7D32),
        ),
      _ScanResult.notMine => (
          Icons.cancel,
          'SIM not assigned to you\n${serial ?? ''}',
          const Color(0xFFD32F2F),
        ),
      _ScanResult.alreadySold => (
          Icons.warning,
          'Already sold\n${serial ?? ''}',
          const Color(0xFFF57F17),
        ),
      _ScanResult.error => (
          Icons.error,
          'Error — try again',
          const Color(0xFFD32F2F),
        ),
    };

    return Container(
      color: color.withAlpha(230),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: Colors.white, size: 80),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
