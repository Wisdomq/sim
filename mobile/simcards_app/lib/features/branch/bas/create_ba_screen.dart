import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

class CreateBaScreen extends ConsumerStatefulWidget {
  const CreateBaScreen({super.key});

  @override
  ConsumerState<CreateBaScreen> createState() => _CreateBaScreenState();
}

class _CreateBaScreenState extends ConsumerState<CreateBaScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _idNumberCtrl = TextEditingController();
  String? _photoUrl;
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    _phoneCtrl.dispose();
    _idNumberCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickPhoto() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 80,
      maxWidth: 800,
    );
    if (image == null) return;

    // For now store local path as placeholder URL.
    // In production this would upload to /uploads/photos and get back a URL.
    setState(() => _photoUrl = 'file://${image.path}');
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_photoUrl == null) {
      setState(() => _errorMessage = 'A current photo is required (AC-9)');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final client = ref.read(apiClientProvider);
      await client.post(
        ApiConfig.brandAmbassadors,
        data: {
          'name': _nameCtrl.text.trim(),
          'email': _emailCtrl.text.trim(),
          'password': _passwordCtrl.text,
          'phone_msisdn': _phoneCtrl.text.trim(),
          'id_number': _idNumberCtrl.text.trim(),
          'photo_url': _photoUrl,
        },
      );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      final data = (e as dynamic).response?.data;
      setState(() {
        _errorMessage = data?['detail']?.toString() ?? 'Failed to create BA';
        _isSubmitting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add Brand Ambassador')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Photo
              GestureDetector(
                onTap: _pickPhoto,
                child: Container(
                  height: 120,
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.grey),
                    borderRadius: BorderRadius.circular(8),
                    color: Colors.grey[100],
                  ),
                  child: _photoUrl != null
                      ? const Icon(Icons.check_circle, color: Color(0xFF4CAF50), size: 48)
                      : const Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.camera_alt, size: 40, color: Colors.grey),
                            SizedBox(height: 8),
                            Text('Tap to take ID photo *'),
                          ],
                        ),
                ),
              ),
              const SizedBox(height: 16),
              _field(_nameCtrl, 'Full Name', required: true),
              _field(_emailCtrl, 'Email', keyboardType: TextInputType.emailAddress, required: true),
              _field(_passwordCtrl, 'Password', obscure: true, required: true),
              _field(_phoneCtrl, 'Phone (MSISDN)', keyboardType: TextInputType.phone),
              _field(_idNumberCtrl, 'ID Number *', required: true),

              if (_errorMessage != null) ...[
                const SizedBox(height: 8),
                Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: _isSubmitting ? null : _submit,
                child: _isSubmitting
                    ? const SizedBox(
                        height: 20, width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Create Brand Ambassador'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _field(
    TextEditingController ctrl,
    String label, {
    TextInputType? keyboardType,
    bool obscure = false,
    bool required = false,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextFormField(
        controller: ctrl,
        keyboardType: keyboardType,
        obscureText: obscure,
        decoration: InputDecoration(labelText: label),
        validator: required
            ? (v) => (v == null || v.trim().isEmpty) ? '$label is required' : null
            : null,
      ),
    );
  }
}
