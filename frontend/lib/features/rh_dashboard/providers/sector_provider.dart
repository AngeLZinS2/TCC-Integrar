import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/sector_repository.dart';
import '../models/sector_model.dart';

final sectorRepositoryProvider = Provider<SectorRepository>((ref) {
  final httpClient = ref.watch(httpClientProvider);
  return SectorRepository(httpClient: httpClient);
});

final sectorsListProvider = FutureProvider<List<SectorModel>>((ref) {
  final repository = ref.watch(sectorRepositoryProvider);
  return repository.getSectors();
});

final positionsBySectorProvider = FutureProvider.family<List<PositionModel>, int>((ref, sectorId) {
  final repository = ref.watch(sectorRepositoryProvider);
  return repository.getPositions(sectorId: sectorId);
});
