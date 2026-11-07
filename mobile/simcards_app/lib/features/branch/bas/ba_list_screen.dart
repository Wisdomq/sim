import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';
import '../../../core/routing/router.dart';

final _basProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.read(apiClientProvider);
  final resp = await client.get(ApiConfig.brandAmbassadors);
  return resp.data as List;
});

class BaListScreen extends ConsumerWidget {
  const BaListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bas = ref.watch(_basProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Brand Ambassadors'),
      ),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.person_add),
        label: const Text('Add BA'),
        onPressed: () async {
          await context.push(AppRoutes.branchCreateBa);
          ref.invalidate(_basProvider);
        },
      ),
      body: bas.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (list) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(_basProvider),
          child: list.isEmpty
              ? const Center(child: Text('No Brand Ambassadors yet'))
              : ListView.builder(
                  itemCount: list.length,
                  itemBuilder: (context, i) {
                    final ba = list[i] as Map<String, dynamic>;
                    return ListTile(
                      leading: CircleAvatar(
                        backgroundColor: const Color(0xFF4CAF50),
                        child: Text(
                          (ba['name'] as String? ?? '?')[0].toUpperCase(),
                          style: const TextStyle(color: Colors.white),
                        ),
                      ),
                      title: Text(ba['name'] as String? ?? ''),
                      subtitle: Text(ba['phone_msisdn'] as String? ?? ''),
                      trailing: Chip(
                        label: Text(ba['status'] as String? ?? ''),
                        backgroundColor: (ba['status'] as String?) == 'ACTIVE'
                            ? const Color(0xFFC8E6C9)
                            : Colors.grey[200],
                      ),
                      onTap: () => context.push(
                        AppRoutes.branchBaDetail.replaceFirst(
                          ':baId',
                          ba['id'].toString(),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ),
    );
  }
}
