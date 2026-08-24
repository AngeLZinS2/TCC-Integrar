import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../../org/models/org_models.dart' show Paginated;
import '../../org/providers/org_provider.dart' show PagedState;
import '../data/audit_repository.dart';
import '../models/audit_log_model.dart';

final auditRepositoryProvider = Provider<AuditRepository>((ref) {
  return AuditRepository(httpClient: ref.watch(httpClientProvider));
});

final auditActionsProvider = FutureProvider<List<AuditFilterOption>>((ref) {
  return ref.watch(auditRepositoryProvider).fetchActions();
});

class AuditNotifier extends StateNotifier<AsyncValue<PagedState<AuditLogModel>>> {
  final AuditRepository _repository;
  int _page = 1;
  String? _action;
  DateTime? _dateFrom;
  DateTime? _dateTo;

  AuditNotifier(this._repository) : super(const AsyncValue.loading()) {
    load();
  }

  String? get actionFilter => _action;
  DateTime? get dateFrom => _dateFrom;
  DateTime? get dateTo => _dateTo;

  Future<void> load({
    String? action,
    DateTime? dateFrom,
    DateTime? dateTo,
    bool clearFilters = false,
  }) async {
    if (clearFilters) {
      _action = null;
      _dateFrom = null;
      _dateTo = null;
    } else {
      if (action != null) _action = action.isEmpty ? null : action;
      if (dateFrom != null) _dateFrom = dateFrom;
      if (dateTo != null) _dateTo = dateTo;
    }
    _page = 1;
    state = const AsyncValue.loading();
    try {
      final result = await _fetch(1);
      state = AsyncValue.data(
        PagedState(items: result.items, count: result.count, hasMore: result.hasMore),
      );
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || !current.hasMore || current.isLoadingMore) return;

    state = AsyncValue.data(current.copyWith(isLoadingMore: true));
    try {
      final result = await _fetch(_page + 1);
      _page += 1;
      state = AsyncValue.data(
        current.copyWith(
          items: [...current.items, ...result.items],
          hasMore: result.hasMore,
          isLoadingMore: false,
        ),
      );
    } catch (_) {
      state = AsyncValue.data(current.copyWith(isLoadingMore: false));
    }
  }

  Future<Paginated<AuditLogModel>> _fetch(int page) {
    return _repository.fetchLogs(
      action: _action,
      dateFrom: _dateFrom,
      dateTo: _dateTo,
      page: page,
    );
  }
}

final auditProvider =
    StateNotifierProvider<AuditNotifier, AsyncValue<PagedState<AuditLogModel>>>((ref) {
  return AuditNotifier(ref.watch(auditRepositoryProvider));
});
