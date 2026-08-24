import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/models/material_model.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/material_repository.dart';

final materialRepositoryProvider = Provider<MaterialRepository>((ref) {
  final httpClient = ref.watch(httpClientProvider);
  return MaterialRepository(httpClient: httpClient);
});

final materialsListProvider =
    FutureProvider.autoDispose<List<MaterialModel>>((ref) async {
  final repository = ref.watch(materialRepositoryProvider);
  return repository.fetchMaterials();
});
