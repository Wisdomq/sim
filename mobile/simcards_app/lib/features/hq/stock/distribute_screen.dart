import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

final _branchesProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(ApiConfig.branches);
  return resp.data as List? ?? [];
});

class DistributeScreen extends ConsumerStatefulWidget {
  const DistributeScreen({super.key});

  @override
  ConsumerState<DistributeScreen> createState() => _DistributeScreenState();
}

class _DistributeScreenState extends ConsumerState<DistributeScreen> {
  int? _selectedBranchId;
  final _quantityCtrl = TextEditingController(text: '100');
  bool _isSubmitting = false;
  String? _statusMessage;

  @override
  void dispose() {
    _quantityCtrl.dispose();
    super.dispose();
  }

  Future<void> _distribute() async {
    if (_selectedBranchId == null) {
      setState(() => _statusMessage = 'Please select a branch');
      return;
    }
    final qty = int.tryParse(_quantityCtrl.text.trim());
    if (qty == null || qty <= 0) {
      setState(() => _statusMessage = 'Enter a valid quantity');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _statusMessage = null;
    });

    try {
      final client = ref.read(apiClientProvider);
      final resp = await client.post(
        ApiConfig.distribute,
        data: {
          'branch_id': _selectedBranchId,
          'quantity': qty,
        },
      );

      final list = resp.data as List? ?? [];
      setState(() {
        _statusMessage = 'Successfully distributed ${list.length} SIM cards to branch!';
      });
    } catch (e) {
      final data = (e as dynamic).response?.data;
      setState(() {
        _statusMessage = 'Error: ${data?['detail'] ?? e.toString()}';
      });
    } finally {
      setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final branchesAsync = ref.watch(_branchesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Distribute Stock')),
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
                    Text('Transfer Stock HQ → Branch',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 16),
                    branchesAsync.when(
                      loading: () => const CircularProgressIndicator(),
                      error: (e, _) => Text('Failed to load branches: $e'),
                      data: (branches) => DropdownButtonFormField<int>(
                        initialValue: _selectedBranchId,
                        decoration: const InputDecoration(labelText: 'Target Branch'),
                        items: branches.map((b) {
                          final item = b as Map<String, dynamic>;
                          return DropdownMenuItem<int>(
                            value: item['id'] as int,
                            child: Text(item['name'] as String? ?? 'Branch ${item['id']}'),
                          );
                        }).toList(),
                        onChanged: (v) => setState(() => _selectedBranchId = v),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _quantityCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Quantity to Distribute',
                        prefixIcon: Icon(Icons.numbers),
                      ),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: _isSubmitting ? null : _distribute,
                      child: _isSubmitting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Text('Distribute'),
                    ),
                  ],
                ),
              ),
            ),
            if (_statusMessage != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: _statusMessage!.startsWith('Error')
                      ? Colors.red[50]
                      : Colors.green[50],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _statusMessage!,
                  style: TextStyle(
                    color: _statusMessage!.startsWith('Error')
                        ? Colors.red[900]
                        : Colors.green[900],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
