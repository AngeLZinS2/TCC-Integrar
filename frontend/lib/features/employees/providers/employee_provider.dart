import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../../org/models/org_models.dart' show ManagerOption;
import '../data/employee_repository.dart';
import '../models/employee_model.dart';

final employeeRepositoryProvider = Provider<EmployeeRepository>((ref) {
  return EmployeeRepository(httpClient: ref.watch(httpClientProvider));
});

final employeeDetailProvider =
    FutureProvider.family<EmployeeModel, int>((ref, id) {
  return ref.watch(employeeRepositoryProvider).fetchEmployee(id);
});

final employeeRolesProvider = FutureProvider<List<RoleOption>>((ref) {
  return ref.watch(employeeRepositoryProvider).fetchRoles();
});

final employeeManagerOptionsProvider = FutureProvider<List<ManagerOption>>((ref) {
  return ref.watch(employeeRepositoryProvider).fetchManagerOptions();
});
