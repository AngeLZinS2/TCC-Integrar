import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/models/onboarding_task_model.dart';
import '../../../shared/models/paginated_response.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/onboarding_tasks_repository.dart';

final onboardingTasksRepositoryProvider =
    Provider<OnboardingTasksRepository>((ref) {
  return OnboardingTasksRepository(httpClient: ref.watch(httpClientProvider));
});

/// Filtro da lista de tarefas.
///
/// Vive num provider para o botão de "só as minhas" e a mudança de status
/// compartilharem o mesmo estado — a lista recarrega sozinha ao mudar.
class TaskFilter {
  final String? status;
  final bool onlyMine;
  final bool onlyOverdue;
  final int? employeeId;

  const TaskFilter({
    this.status,
    this.onlyMine = false,
    this.onlyOverdue = false,
    this.employeeId,
  });

  TaskFilter copyWith({
    String? status,
    bool? onlyMine,
    bool? onlyOverdue,
    int? employeeId,
    bool clearStatus = false,
  }) {
    return TaskFilter(
      status: clearStatus ? null : (status ?? this.status),
      onlyMine: onlyMine ?? this.onlyMine,
      onlyOverdue: onlyOverdue ?? this.onlyOverdue,
      employeeId: employeeId ?? this.employeeId,
    );
  }

  @override
  bool operator ==(Object other) =>
      other is TaskFilter &&
      other.status == status &&
      other.onlyMine == onlyMine &&
      other.onlyOverdue == onlyOverdue &&
      other.employeeId == employeeId;

  @override
  int get hashCode => Object.hash(status, onlyMine, onlyOverdue, employeeId);
}

final taskFilterProvider = StateProvider<TaskFilter>((ref) => const TaskFilter());

final onboardingTasksProvider =
    FutureProvider.autoDispose<PaginatedResponse<OnboardingTaskModel>>((ref) {
  final filtro = ref.watch(taskFilterProvider);
  return ref.watch(onboardingTasksRepositoryProvider).getTasks(
        status: filtro.status,
        onlyMine: filtro.onlyMine,
        onlyOverdue: filtro.onlyOverdue,
        employeeId: filtro.employeeId,
      );
});

final onboardingTaskDetailProvider =
    FutureProvider.autoDispose.family<OnboardingTaskModel, int>((ref, id) {
  return ref.watch(onboardingTasksRepositoryProvider).getTask(id);
});

final myOnboardingProvider =
    FutureProvider.autoDispose<MyOnboarding>((ref) {
  return ref.watch(onboardingTasksRepositoryProvider).getMyOnboarding();
});

final employeeOnboardingProvider =
    FutureProvider.autoDispose.family<MyOnboarding, int>((ref, employeeId) {
  return ref
      .watch(onboardingTasksRepositoryProvider)
      .getEmployeeOnboarding(employeeId);
});

final onboardingTemplatesProvider = FutureProvider.autoDispose<
    PaginatedResponse<OnboardingTemplateModel>>((ref) {
  return ref.watch(onboardingTasksRepositoryProvider).getTemplates();
});
