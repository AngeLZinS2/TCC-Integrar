import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../models/collaborator_detail_model.dart';
import '../models/collaborator_row_model.dart';
import '../models/dashboard_overview_model.dart';

class DashboardRepository {
  final HttpClient httpClient;

  DashboardRepository({required this.httpClient});

  Future<DashboardOverviewModel> getOverview() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.dashboardOverview);
      return DashboardOverviewModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao carregar estatísticas do painel.';
      throw Exception(detail);
    }
  }

  Future<List<CollaboratorRowModel>> getCollaborators({String? sector, String? search}) async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.dashboardCollaborators,
        queryParameters: {
          if (sector != null && sector.isNotEmpty) 'sector': sector,
          if (search != null && search.isNotEmpty) 'search': search,
        },
      );
      final list = response.data as List<dynamic>;
      return list.map((e) => CollaboratorRowModel.fromJson(e as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao carregar colaboradores.';
      throw Exception(detail);
    }
  }

  Future<CollaboratorDetailModel> getCollaboratorDetail(int id) async {
    try {
      final response = await httpClient.dio.get(ApiConstants.dashboardCollaboratorDetail(id));
      return CollaboratorDetailModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao carregar detalhes do colaborador.';
      throw Exception(detail);
    }
  }

  Future<void> registerCollaborator({
    required String email,
    required String fullName,
    required String password,
    int? sectorId,
    int? positionId,
    DateTime? hireDate,
    bool isSectorLeader = false,
  }) async {
    try {
      await httpClient.dio.post(
        ApiConstants.register,
        data: {
          'email': email,
          'full_name': fullName,
          'role': 'colaborador',
          'password': password,
          'password_confirm': password,
          if (sectorId != null) 'sector': sectorId,
          if (positionId != null) 'position': positionId,
          if (hireDate != null) 'hire_date': hireDate.toIso8601String().split('T').first,
          'is_sector_leader': isSectorLeader,
        },
      );
    } on DioException catch (e) {
      final data = e.response?.data;
      String detail = 'Erro ao cadastrar colaborador.';
      if (data is Map && data.isNotEmpty) {
        final firstError = data.values.first;
        detail = firstError is List ? firstError.first.toString() : firstError.toString();
      }
      throw Exception(detail);
    }
  }

  Future<void> toggleColaboradorActive(int id) async {
    try {
      await httpClient.dio.post(ApiConstants.toggleColaboradorActive(id));
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao atualizar status do colaborador.';
      throw Exception(detail);
    }
  }

  Future<void> toggleSectorLeader(int id) async {
    try {
      await httpClient.dio.post(ApiConstants.toggleSectorLeader(id));
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao atualizar liderança de setor.';
      throw Exception(detail);
    }
  }

  Future<List<int>> exportCollaboratorsCsv() async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.dashboardCollaboratorsExport,
        options: Options(responseType: ResponseType.bytes),
      );
      return response.data as List<int>;
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao exportar colaboradores.';
      throw Exception(detail);
    }
  }
}
