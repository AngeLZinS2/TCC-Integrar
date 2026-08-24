import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/models/paginated_response.dart';
import '../../../shared/models/unit_model.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/units_repository.dart';

final unitsRepositoryProvider = Provider<UnitsRepository>((ref) {
  return UnitsRepository(httpClient: ref.watch(httpClientProvider));
});

final unitsListProvider =
    FutureProvider.autoDispose<PaginatedResponse<UnitModel>>((ref) {
  return ref.watch(unitsRepositoryProvider).getUnits();
});
