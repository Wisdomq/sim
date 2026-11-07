import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

class StockIntakeScreen extends ConsumerStatefulWidget {
  const StockIntakeScreen({super.key});

  @override
  ConsumerState<StockIntakeScreen> createState() => _StockIntakeScreenState();
}

class _StockIntakeScreenState extends ConsumerState<StockIntakeScreen> {
  final _barcodeCtrl = TextEditingController();
  final _firstSerialCtrl = TextEditingController();
  int _quantity = 100;
  bool _isSubmitting = false;
  String? _statusMessage;
  bool _isScanning = false;

  @override
  void dispose() {
    _barcodeCtrl.dispose();
    _firstSerialCtrl.dispose();
    super.dispose();
  }

  Future<void> _submitPickListPdf() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
      allowMultiple: false,
    );
    final path = result?.files.single.path;
    if (path == null) return;

    setState(() {
      _isSubmitting = true;
      _statusMessage = null;
    });

    try {
      final client = ref.read(apiClientProvider);
      final form = FormData.fromMap({
        'file': await MultipartFile.fromFile(path, filename: 'pick-list.pdf'),
      });
      final resp = await client.postMultipart(ApiConfig.intakePickListPdf, form);
      final data = resp.data as Map<String, dynamic>;
      setState(() {
        _statusMessage = 'Pick-list uploaded — processing task '
            '${data['task_id']}. SIMs will appear once parsed.';
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

  Future<void> _submitBoxIntake() async {
    if (_barcodeCtrl.text.trim().isEmpty) {
      setState(() => _statusMessage = 'Box barcode is required');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _statusMessage = null;
    });

    try {
      final client = ref.read(apiClientProvider);
      final resp = await client.post(
        ApiConfig.intakeBoxScan,
        data: {
          'box_barcode': _barcodeCtrl.text.trim(),
          if (_firstSerialCtrl.text.trim().isNotEmpty)
            'first_serial': _firstSerialCtrl.text.trim(),
          'quantity': _quantity,
        },
      );

      final data = resp.data as Map<String, dynamic>;
      setState(() {
        _statusMessage =
            'Successfully ingested ${data['inserted_count']} SIMs! (Duplicates: ${data['duplicate_count']})';
        _barcodeCtrl.clear();
        _firstSerialCtrl.clear();
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
    return Scaffold(
      appBar: AppBar(title: const Text('HQ Stock Intake')),
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
                    Text('Upload Pick-List PDF',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text(
                      'Upload the Safaricom pick-list PDF and bulk-ingest SIMs from it.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 12),
                    ElevatedButton.icon(
                      icon: const Icon(Icons.picture_as_pdf_outlined),
                      label: _isSubmitting
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white),
                            )
                          : const Text('Upload Pick-List PDF'),
                      onPressed: _isSubmitting ? null : _submitPickListPdf,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('Scan Box Barcode (100 SIM Pack)',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    if (_isScanning)
                      SizedBox(
                        height: 200,
                        child: MobileScanner(
                          onDetect: (capture) {
                            final barcode = capture.barcodes.firstOrNull?.rawValue;
                            if (barcode != null && barcode.isNotEmpty) {
                              setState(() {
                                _barcodeCtrl.text = barcode;
                                _isScanning = false;
                              });
                            }
                          },
                        ),
                      )
                    else
                      ElevatedButton.icon(
                        icon: const Icon(Icons.qr_code_scanner),
                        label: const Text('Open Scanner'),
                        onPressed: () => setState(() => _isScanning = true),
                      ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _barcodeCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Box Barcode',
                        prefixIcon: Icon(Icons.inventory),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _firstSerialCtrl,
                      decoration: const InputDecoration(
                        labelText: 'First Serial Number (Optional for range)',
                        prefixIcon: Icon(Icons.numbers),
                      ),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      initialValue: _quantity,
                      decoration: const InputDecoration(labelText: 'Pack Quantity'),
                      items: const [
                        DropdownMenuItem(value: 100, child: Text('100 SIMs')),
                        DropdownMenuItem(value: 50, child: Text('50 SIMs')),
                        DropdownMenuItem(value: 20, child: Text('20 SIMs')),
                      ],
                      onChanged: (v) => setState(() => _quantity = v ?? 100),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: _isSubmitting ? null : _submitBoxIntake,
                      child: _isSubmitting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Text('Intake Pack'),
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
