/// Uma página de resultados da API paginada do DRF.
///
/// Vive em `shared/` porque é usada por praticamente toda feature que
/// lista algo — antes morava dentro de `features/org/`, o que obrigava
/// módulos sem relação nenhuma a importar de lá.
class PaginatedResponse<T> {
  final List<T> items;
  final int count;
  final bool hasMore;

  const PaginatedResponse({
    required this.items,
    required this.count,
    required this.hasMore,
  });

  /// Compatibilidade com o nome usado pelas telas da P2.
  List<T> get results => items;

  bool get isEmpty => items.isEmpty;

  factory PaginatedResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>) parse,
  ) {
    final results = json['results'] as List<dynamic>? ?? const [];
    return PaginatedResponse(
      items: results.map((e) => parse(e as Map<String, dynamic>)).toList(),
      count: json['count'] as int? ?? results.length,
      hasMore: json['next'] != null,
    );
  }

  static PaginatedResponse<T> empty<T>() =>
      PaginatedResponse<T>(items: const [], count: 0, hasMore: false);
}

/// Nome antigo, mantido para não quebrar os módulos da P1.
typedef Paginated<T> = PaginatedResponse<T>;
