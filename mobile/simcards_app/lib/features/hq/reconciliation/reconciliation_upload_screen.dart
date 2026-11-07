import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';
import '../../../core/routing/router.dart';

final _importsProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(ApiConfig.reconciliationImports);
  return resp.data as List? ?? [];
});

class ReconciliationUploadScreen extends ConsumerStatefulWidget {
  const ReconciliationUploadScreen({super.key});

  @override
  ConsumerState<ReconciliationUploadScreen> createState() =>
      _ReconciliationUploadScreenState();
}

class _ReconciliationUploadScreenState
    extends ConsumerState<ReconciliationUploadScreen> {
  String? _fileName;
  DateTime? _reportDate;
  bool _isUploading = false;
  String? _message;

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['xlsx'],
      allowMultiple: false,
    );
    if (result == null || result.files.isEmpty) return;
    setState(() {
      _fileName = result.files.single.name;
      _message = null;
    });
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2031),
    );
    if (picked != null) setState(() => _reportDate = picked);
  }

  Future<void> _upload() async {
    final path = await _pickedPath();
    if (path == null) {
      setState(() => _message = 'Choose a .xlsx Safaricom report first');
      return;
    }
    if (_reportDate == null) {
      setState(() => _message = 'Pick the report date');
      return;
    }

    setState(() {
      _isUploading = true;
      _message = null;
    });
    try {
      final client = ref.read(apiClientProvider);
      final form = FormData.fromMap({
        'file': await MultipartFile.fromFile(path, filename: _fileName),
        'report_date':
            '${_reportDate!.year}-${_reportDate!.month.toString().padLeft(2, '0')}-${_reportDate!.day.toString().padLeft(2, '0')}',
      });
      final resp = await client.postMultipart(ApiConfig.reconciliationImports, form);
      final data = resp.data as Map<String, dynamic>;
      setState(() {
        _message =
            'Upload accepted (import #${data['import_id']}). Reconciliation is running — refresh shortly.';
        _fileName = null;
        _reportDate = null;
      });
      ref.invalidate(_importsProvider);
    } catch (e) {
      final data = (e as dynamic).response?.data;
      setState(() => _message = 'Error: ${data?['detail'] ?? e}');
    } finally {
      setState(() => _isUploading = false);
    }
  }

  Future<String?> _pickedPath() async {
    // Remember the selected file path so we don't re-pick on submit.
    if (_lastPath != null) return _lastPath;
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['xlsx'],
      allowMultiple: false,
    );
    if (result == null || result.files.isEmpty) return null;
    _lastPath = result.files.single.path;
    setState(() {
      _fileName ??= result.files.single.name;
    });
    return _lastPath;
  }

  String? _lastPath;

  @override
  Widget build(BuildContext context) {
    final importsAsync = ref.watch(_importsProvider);

    String dateLabel() {
      final d = _reportDate;
      if (d == null) return 'Select report date';
      return '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Reconciliation')),
      body: importsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (imports) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(_importsProvider),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text('Safaricom Line-Connection Report',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      const Text(
                        'Upload daily .xlsx line-connection reports from Safaricom to run automated reconciliation against sales in the field.',
                        style: TextStyle(color: Colors.grey),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              icon: const Icon(Icons.attach_file),
                              label: Text(_fileName ?? 'Upload .xlsx'),
                              onPressed: _pickFile,
                            ),
                          ),
                          const SizedBox(width: 8),
                          OutlinedButton.icon(
                            icon: const Icon(Icons.event),
                            label: Text(dateLabel()),
                            onPressed: _pickDate,
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ElevatedButton.icon(
                        icon: const Icon(Icons.cloud_upload_outlined),
                        label: _isUploading
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: Colors.white),
                              )
                            : const Text('Run Reconciliation'),
                        onPressed: _isUploading ? null : _upload,
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
              Text('Recent Imports', style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 8),
              if (imports.isEmpty)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text('No reports uploaded yet'),
                  ),
                )
              else
                ...imports.map((item) {
                  final map = item as Map<String, dynamic>;
                  final id = map['id'];
                  final date = map['report_date'] ?? '';
                  final status = map['status'] ?? '';
                  return ListTile(
                    leading: const Icon(Icons.description_outlined),
                    title: Text('Report: $date'),
                    subtitle: Text('Status: $status · ${map['row_count'] ?? 0} rows'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push(
                      AppRoutes.hqReconciliationSummary.replaceFirst(
                        ':importId',
                        id.toString(),
                      ),
                    ),
                  );
                }),
            ],
          ),
        ),
      ),
    );
  }
}