import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/dashboard_repository.dart';
import '../models/collaborator_detail_model.dart';
import '../models/collaborator_row_model.dart';
import '../models/dashboard_overview_model.dart';

final dashboardRepositoryProvider = Provider<DashboardRepository>((ref) {
  final httpClient = ref.watch(httpClientProvider);
  return DashboardRepository(httpClient: httpClient);
});

final dashboardOverviewProvider = FutureProvider<DashboardOverviewModel>((ref) {
  final repository = ref.watch(dashboardRepositoryProvider);
  return repository.getOverview();
});

final collaboratorsListProvider = FutureProvider<List<CollaboratorRowModel>>((ref) {
  final repository = ref.watch(dashboardRepositoryProvider);
  return repository.getCollaborators();
});

final collaboratorDetailProvider =
    FutureProvider.family<CollaboratorDetailModel, int>((ref, id) {
  final repository = ref.watch(dashboardRepositoryProvider);
  return repository.getCollaboratorDetail(id);
});
