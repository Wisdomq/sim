import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

final _branchesProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(ApiConfig.branches);
  return resp.data as List? ?? [];
});

final _requestsProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(
    ApiConfig.returnRequests,
    queryParameters: {'status_filter': 'REQUESTED'},
  );
  return resp.data as List? ?? [];
});

class ReturnRequestScreen extends ConsumerStatefulWidget {
  const ReturnRequestScreen({super.key});

  @override
  ConsumerState<ReturnRequestScreen> createState() => _ReturnRequestScreenState();
}

class _ReturnRequestScreenState extends ConsumerState<ReturnRequestScreen> {
  final _serialsCtrl = TextEditingController();
  final _reasonCtrl = TextEditingController();
  int? _selectedBranchId;
  bool _isSubmitting = false;
  String? _message;

  @override
  void dispose() {
    _serialsCtrl.dispose();
    _reasonCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_selectedBranchId == null) {
      setState(() => _message = 'Select a branch');
      return;
    }
    final serials = _serialsCtrl.text
        .split('\n')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();
    if (serials.isEmpty) {
      setState(() => _message = 'Enter at least one serial number');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _message = null;
    });
    try {
      final client = ref.read(apiClientProvider);
      final resp = await client.post(
        ApiConfig.returnRequests,
        data: {
          'branch_id': _selectedBranchId,
          'serial_numbers': serials,
          'reason': _reasonCtrl.text.trim().isEmpty ? null : _reasonCtrl.text.trim(),
        },
      );
      final created = (resp.data as List?)?.length ?? 0;
      setState(() {
        _message = 'Return request created for $created SIMs.';
        _serialsCtrl.clear();
        _reasonCtrl.clear();
      });
      ref.invalidate(_requestsProvider);
    } catch (e) {
      final data = (e as dynamic).response?.data;
      setState(() => _message = 'Error: ${data?['detail'] ?? e}');
    } finally {
      setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final branchesAsync = ref.watch(_branchesProvider);
    final requestsAsync = ref.watch(_requestsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Stock Return Requests')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('Request branch to return stock',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    branchesAsync.when(
                      loading: () => const CircularProgressIndicator(),
                      error: (e, _) => Text('Failed to load branches: $e'),
                      data: (branches) => DropdownButtonFormField<int>(
                        initialValue: _selectedBranchId,
                        decoration: const InputDecoration(labelText: 'Branch'),
                        items: branches.map((b) {
                          final m = b as Map<String, dynamic>;
                          return DropdownMenuItem<int>(
                            value: m['id'] as int,
                            child: Text(m['name'] as String? ?? 'Branch ${m['id']}'),
                          );
                        }).toList(),
                        onChanged: (v) => setState(() => _selectedBranchId = v),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _serialsCtrl,
                      maxLines: 4,
                      decoration: const InputDecoration(
                        labelText: 'Serial numbers (one per line)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _reasonCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Reason (optional)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: _isSubmitting ? null : _submit,
                      child: _isSubmitting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white),
                            )
                          : const Text('Create Request'),
                    ),
                    if (_message != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        _message!,
                        style: TextStyle(
                          color: _message!.startsWith('Error')
                              ? Colors.red[800]
                              : Colors.green[800],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text('Pending Requests', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            requestsAsync.when(
              loading: () => const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (e, _) => Text('Error: $e'),
              data: (requests) => requests.isEmpty
                    ? Padding(
                        padding: const EdgeInsets.all(16),
                        child: Text('No pending return requests',
                            style: TextStyle(color: Colors.grey[600])),
                      )
                    : Column(
                        children: requests.map((r) {
                          final m = r as Map<String, dynamic>;
                          return ListTile(
                            dense: true,
                            leading:
                                const Icon(Icons.undo, color: Color(0xFFF57F17)),
                            title: Text('SIM ${m['serial_number'] ?? m['sim_card_id']}'),
                            subtitle: Text(
                              'Branch ${m['branch_id']}${m['reason'] != null ? ' · ${m['reason']}' : ''}',
                            ),
                          );
                        }).toList(),
                      ),
            ),
          ],
        ),
      ),
    );
  }
}