import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

/// Opens a dialog that lets the branch quick-assign a quantity of its
/// unassigned (WITH_BRANCH) pool stock to a chosen Brand Ambassador.
///
/// Returns true when an assignment was performed.
Future<bool> showAssignToBaDialog(BuildContext context, WidgetRef ref) async {
  final client = ref.read(apiClientProvider);

  final List<Map> pool;
  final List<Map> bas;
  try {
    final poolResp = await client.get(
      ApiConfig.simCards,
      queryParameters: {'status_filter': 'WITH_BRANCH'},
    );
    final basResp = await client.get(ApiConfig.brandAmbassadors);
    pool = (poolResp.data as List).cast<Map>();
    bas = (basResp.data as List).cast<Map>();
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load stock/ambassadors: ${_detail(e)}')),
      );
    }
    return false;
  }

  if (!context.mounted) return false;

  if (pool.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('No unassigned branch pool stock available.')),
    );
    return false;
  }
  if (bas.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('No Brand Ambassadors yet. Add a BA first.')),
    );
    return false;
  }

  final serials = pool.map((s) => s['serial_number'] as String).toList();
  final qtyCtrl = TextEditingController(text: '1');
  int? targetBaId = bas.first['id'] as int?;
  var performed = false;

  await showDialog<void>(
    context: context,
    builder: (dialogCtx) => StatefulBuilder(
      builder: (dialogCtx, setState) => AlertDialog(
        title: const Text('Assign Stock to BA'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DropdownButtonFormField<int>(
                initialValue: targetBaId,
                decoration: const InputDecoration(labelText: 'Brand Ambassador'),
                items: bas.map((b) {
                  return DropdownMenuItem<int>(
                    value: b['id'] as int,
                    child: Text(b['name'] as String? ?? 'BA ${b['id']}'),
                  );
                }).toList(),
                onChanged: (v) => setState(() => targetBaId = v),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: qtyCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Quantity',
                  border: OutlineInputBorder(),
                ),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: 8),
              Text(
                'Will assign the first ${_effectiveQty(qtyCtrl.text, serials.length)} '
                'of ${serials.length} pool serial(s), oldest first.',
                style: Theme.of(dialogCtx).textTheme.bodySmall,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogCtx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => _submit(
              dialogCtx,
              client,
              targetBaId,
              qtyCtrl.text,
              serials,
              onSuccess: () {
                performed = true;
                Navigator.pop(dialogCtx);
              },
            ),
            child: const Text('Assign'),
          ),
        ],
      ),
    ),
  );

  return performed;
}

int _effectiveQty(String raw, int poolSize) {
  final qty = int.tryParse(raw.trim()) ?? 0;
  if (qty <= 0) return 0;
  return qty < poolSize ? qty : poolSize;
}

String _detail(Object error) {
  final data = (error as dynamic).response?.data;
  return data?['detail']?.toString() ?? error.toString();
}

Future<void> _submit(
  BuildContext dialogCtx,
  ApiClient client,
  int? targetBaId,
  String qtyText,
  List<String> serials, {
  required VoidCallback onSuccess,
}) async {
  final qty = _effectiveQty(qtyText, serials.length);
  if (targetBaId == null || qty == 0) return;

  try {
    await client.post(
      ApiConfig.assignToBa,
      data: {'ba_id': targetBaId, 'serial_numbers': serials.take(qty).toList()},
    );
    if (dialogCtx.mounted) onSuccess();
  } catch (e) {
    if (dialogCtx.mounted) {
      ScaffoldMessenger.of(dialogCtx).showSnackBar(
        SnackBar(content: Text('Assign failed: ${_detail(e)}')),
      );
    }
  }
}