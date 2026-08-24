import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../models/org_models.dart';

/// Acesso à estrutura organizacional da própria empresa.
///
/// O tenant nunca é informado pelo app: o backend resolve a empresa a
/// partir do usuário autenticado.
class OrgRepository {
  final HttpClient httpClient;

  OrgRepository({required this.httpClient});

  String _errorFrom(DioException e, String fallback) {
    final data = e.response?.data;
    if (data is Map && data.isNotEmpty) {
      final first = data.values.first;
      return first is List ? first.first.toString() : first.toString();
    }
    return fallback;
  }

  // ── Setores ─────────────────────────────────────────────────────────────

  Future<Paginated<SectorModel>> fetchSectors({
    String? search,
    int page = 1,
  }) async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.sectors,
        queryParameters: {
          'page': page,
          if (search != null && search.isNotEmpty) 'search': search,
        },
      );
      return Paginated.fromJson(
        response.data as Map<String, dynamic>,
        SectorModel.fromJson,
      );
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar setores.'));
    }
  }

  Future<SectorModel> createSector({
    required String name,
    String description = '',
    int? managerId,
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.sectors,
        data: {'name': name, 'description': description, 'manager': managerId},
      );
      return SectorModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao criar setor.'));
    }
  }

  Future<SectorModel> updateSector(
    int id, {
    String? name,
    String? description,
    int? managerId,
    bool clearManager = false,
    bool? isActive,
  }) async {
    try {
      final response = await httpClient.dio.patch(
        '${ApiConstants.sectors}$id/',
        data: {
          if (name != null) 'name': name,
          if (description != null) 'description': description,
          // `null` é um valor válido aqui (remover gestor), então precisa de
          // um sinal explícito para diferenciar de "não mexer no campo".
          if (managerId != null || clearManager) 'manager': managerId,
          if (isActive != null) 'is_active': isActive,
        },
      );
      return SectorModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao atualizar setor.'));
    }
  }

  Future<void> deleteSector(int id) async {
    try {
      await httpClient.dio.delete('${ApiConstants.sectors}$id/');
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao excluir setor.'));
    }
  }

  Future<List<ManagerOption>> fetchManagerOptions() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.sectorManagerOptions);
      final list = response.data as List<dynamic>;
      return list.map((e) => ManagerOption.fromJson(e as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar gestores.'));
    }
  }

  // ── Cargos ──────────────────────────────────────────────────────────────

  Future<Paginated<PositionModel>> fetchPositions({
    int? sectorId,
    String? search,
    int page = 1,
  }) async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.positions,
        queryParameters: {
          'page': page,
          if (sectorId != null) 'sector': sectorId,
          if (search != null && search.isNotEmpty) 'search': search,
        },
      );
      return Paginated.fromJson(
        response.data as Map<String, dynamic>,
        PositionModel.fromJson,
      );
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar cargos.'));
    }
  }

  Future<PositionModel> createPosition({
    required String name,
    required int sectorId,
    String description = '',
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.positions,
        data: {'name': name, 'sector': sectorId, 'description': description},
      );
      return PositionModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao criar cargo.'));
    }
  }

  Future<PositionModel> updatePosition(
    int id, {
    String? name,
    String? description,
    int? sectorId,
    bool? isActive,
  }) async {
    try {
      final response = await httpClient.dio.patch(
        '${ApiConstants.positions}$id/',
        data: {
          if (name != null) 'name': name,
          if (description != null) 'description': description,
          if (sectorId != null) 'sector': sectorId,
          if (isActive != null) 'is_active': isActive,
        },
      );
      return PositionModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao atualizar cargo.'));
    }
  }

  Future<void> deletePosition(int id) async {
    try {
      await httpClient.dio.delete('${ApiConstants.positions}$id/');
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao excluir cargo.'));
    }
  }
}
