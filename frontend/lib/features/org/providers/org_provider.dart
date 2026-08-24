import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/org_repository.dart';
import '../models/org_models.dart';

final orgRepositoryProvider = Provider<OrgRepository>((ref) {
  return OrgRepository(httpClient: ref.watch(httpClientProvider));
});

/// Estado de uma lista paginada com busca.
///
/// Guarda os itens já carregados, a página atual e se ainda há mais — o
/// suficiente para "carregar mais" sem recarregar o que já está na tela.
class PagedState<T> {
  final List<T> items;
  final int count;
  final bool hasMore;
  final bool isLoadingMore;
  final String search;

  const PagedState({
    this.items = const [],
    this.count = 0,
    this.hasMore = false,
    this.isLoadingMore = false,
    this.search = '',
  });

  PagedState<T> copyWith({
    List<T>? items,
    int? count,
    bool? hasMore,
    bool? isLoadingMore,
    String? search,
  }) {
    return PagedState<T>(
      items: items ?? this.items,
      count: count ?? this.count,
      hasMore: hasMore ?? this.hasMore,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      search: search ?? this.search,
    );
  }
}

// ── Setores ─────────────────────────────────────────────────────────────────

class SectorsNotifier extends StateNotifier<AsyncValue<PagedState<SectorModel>>> {
  final OrgRepository _repository;
  int _page = 1;
  String _search = '';

  SectorsNotifier(this._repository) : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load({String? search}) async {
    if (search != null) _search = search;
    _page = 1;
    state = const AsyncValue.loading();
    try {
      final page = await _repository.fetchSectors(search: _search, page: 1);
      state = AsyncValue.data(
        PagedState(
          items: page.items,
          count: page.count,
          hasMore: page.hasMore,
          search: _search,
        ),
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
      final page = await _repository.fetchSectors(search: _search, page: _page + 1);
      _page += 1;
      state = AsyncValue.data(
        current.copyWith(
          items: [...current.items, ...page.items],
          hasMore: page.hasMore,
          isLoadingMore: false,
        ),
      );
    } catch (_) {
      // Mantém o que já está na tela: falhar o "carregar mais" não deve
      // apagar as páginas anteriores.
      state = AsyncValue.data(current.copyWith(isLoadingMore: false));
    }
  }
}

final sectorsProvider =
    StateNotifierProvider<SectorsNotifier, AsyncValue<PagedState<SectorModel>>>((ref) {
  return SectorsNotifier(ref.watch(orgRepositoryProvider));
});

final managerOptionsProvider = FutureProvider<List<ManagerOption>>((ref) {
  return ref.watch(orgRepositoryProvider).fetchManagerOptions();
});

// ── Cargos ──────────────────────────────────────────────────────────────────

class PositionsNotifier extends StateNotifier<AsyncValue<PagedState<PositionModel>>> {
  final OrgRepository _repository;
  int _page = 1;
  String _search = '';
  int? _sectorId;

  PositionsNotifier(this._repository) : super(const AsyncValue.loading()) {
    load();
  }

  int? get sectorFilter => _sectorId;

  Future<void> load({String? search, int? sectorId, bool clearSector = false}) async {
    if (search != null) _search = search;
    if (clearSector) {
      _sectorId = null;
    } else if (sectorId != null) {
      _sectorId = sectorId;
    }
    _page = 1;
    state = const AsyncValue.loading();
    try {
      final page = await _repository.fetchPositions(
        search: _search,
        sectorId: _sectorId,
        page: 1,
      );
      state = AsyncValue.data(
        PagedState(
          items: page.items,
          count: page.count,
          hasMore: page.hasMore,
          search: _search,
        ),
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
      final page = await _repository.fetchPositions(
        search: _search,
        sectorId: _sectorId,
        page: _page + 1,
      );
      _page += 1;
      state = AsyncValue.data(
        current.copyWith(
          items: [...current.items, ...page.items],
          hasMore: page.hasMore,
          isLoadingMore: false,
        ),
      );
    } catch (_) {
      state = AsyncValue.data(current.copyWith(isLoadingMore: false));
    }
  }
}

final positionsProvider =
    StateNotifierProvider<PositionsNotifier, AsyncValue<PagedState<PositionModel>>>((ref) {
  return PositionsNotifier(ref.watch(orgRepositoryProvider));
});
