import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/models/checklist_model.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/checklist_repository.dart';

final checklistRepositoryProvider = Provider<ChecklistRepository>((ref) {
  final httpClient = ref.watch(httpClientProvider);
  return ChecklistRepository(httpClient: httpClient);
});

class ChecklistNotifier extends StateNotifier<AsyncValue<List<ChecklistItemModel>>> {
  final ChecklistRepository _repository;

  ChecklistNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadChecklist();
  }

  Future<void> loadChecklist() async {
    state = const AsyncValue.loading();
    try {
      final items = await _repository.fetchChecklist();
      state = AsyncValue.data(items);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> toggleItem(int itemId) async {
    final currentList = state.value;
    if (currentList == null) return;

    final targetItem = currentList.firstWhere((i) => i.id == itemId);
    final nextState = !targetItem.isCompleted;

    // Atualização otimista imediata na UI
    state = AsyncValue.data(
      currentList.map((i) {
        if (i.id == itemId) {
          return i.copyWith(
            isCompleted: nextState,
            completedAt: nextState ? DateTime.now() : null,
          );
        }
        return i;
      }).toList(),
    );

    try {
      final result = await _repository.toggleItem(itemId, completed: nextState);
      if (result != nextState) {
        // Reverte se a resposta do servidor for diferente
        state = AsyncValue.data(
          currentList.map((i) {
            if (i.id == itemId) {
              return i.copyWith(isCompleted: result);
            }
            return i;
          }).toList(),
        );
      }
    } catch (e) {
      // Reverte em caso de erro
      state = AsyncValue.data(currentList);
    }
  }
}

final checklistProvider =
    StateNotifierProvider<ChecklistNotifier, AsyncValue<List<ChecklistItemModel>>>((ref) {
  final repository = ref.watch(checklistRepositoryProvider);
  return ChecklistNotifier(repository);
});
