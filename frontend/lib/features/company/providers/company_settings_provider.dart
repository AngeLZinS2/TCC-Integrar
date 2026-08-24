import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/company_settings_repository.dart';
import '../models/company_settings_model.dart';

final companySettingsRepositoryProvider = Provider<CompanySettingsRepository>((ref) {
  return CompanySettingsRepository(httpClient: ref.watch(httpClientProvider));
});

final myCompanyProvider = FutureProvider<CompanySettingsModel>((ref) {
  return ref.watch(companySettingsRepositoryProvider).fetch();
});

final setupChecklistProvider = FutureProvider<SetupChecklist>((ref) {
  return ref.watch(companySettingsRepositoryProvider).fetchSetupChecklist();
});
