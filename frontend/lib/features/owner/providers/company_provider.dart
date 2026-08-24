import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../../rh_dashboard/models/dashboard_overview_model.dart';
import '../data/company_repository.dart';
import '../models/company_model.dart';

final companyRepositoryProvider = Provider<CompanyRepository>((ref) {
  final httpClient = ref.watch(httpClientProvider);
  return CompanyRepository(httpClient: httpClient);
});

class CompaniesListNotifier extends StateNotifier<AsyncValue<List<CompanyModel>>> {
  final CompanyRepository _repository;

  CompaniesListNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadCompanies();
  }

  Future<void> loadCompanies() async {
    state = const AsyncValue.loading();
    try {
      final companies = await _repository.getCompanies();
      state = AsyncValue.data(companies);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> createCompany({
    required String name,
    required String adminEmail,
    required String adminFullName,
    required String adminPassword,
  }) async {
    await _repository.createCompany(
      name: name,
      adminEmail: adminEmail,
      adminFullName: adminFullName,
      adminPassword: adminPassword,
    );
    await loadCompanies();
  }

  Future<void> toggleActive(int id) async {
    final current = state.value;
    if (current == null) return;
    try {
      final updated = await _repository.toggleActive(id);
      state = AsyncValue.data([
        for (final company in current) company.id == id ? updated : company,
      ]);
    } catch (_) {}
  }
}

final companiesListProvider =
    StateNotifierProvider<CompaniesListNotifier, AsyncValue<List<CompanyModel>>>((ref) {
  final repository = ref.watch(companyRepositoryProvider);
  return CompaniesListNotifier(repository);
});

final companyDashboardProvider = FutureProvider.family<DashboardOverviewModel, int>((ref, id) {
  final repository = ref.watch(companyRepositoryProvider);
  return repository.getCompanyDashboard(id);
});

// Não existe provider de colaboradores por empresa: o dono da plataforma
// administra o tenant, não as pessoas dentro dele. A listagem nominal vive
// em rh_dashboard, restrita ao RH da própria empresa.
