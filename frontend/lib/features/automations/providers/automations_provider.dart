import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/models/automation_model.dart';
import '../../../shared/models/paginated_response.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/automations_repository.dart';

final automationsRepositoryProvider = Provider<AutomationsRepository>((ref) {
  return AutomationsRepository(httpClient: ref.watch(httpClientProvider));
});

final automationRulesProvider =
    FutureProvider.autoDispose<PaginatedResponse<AutomationRule>>((ref) {
  return ref.watch(automationsRepositoryProvider).getRules();
});

/// O catálogo muda pouco; `keepAlive` evita rebuscar a cada abertura do
/// formulário.
final automationCatalogProvider = FutureProvider<AutomationCatalog>((ref) {
  return ref.watch(automationsRepositoryProvider).getCatalog();
});

final automationRunsProvider =
    FutureProvider.autoDispose.family<List<AutomationRun>, int>((ref, ruleId) {
  return ref.watch(automationsRepositoryProvider).getRuns(ruleId);
});
