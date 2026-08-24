import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../org/models/org_models.dart' show ManagerOption, Paginated;
import '../models/employee_model.dart';

class EmployeeRepository {
  final HttpClient httpClient;

  EmployeeRepository({required this.httpClient});

  String _errorFrom(DioException e, String fallback) {
    final data = e.response?.data;
    if (data is Map && data.isNotEmpty) {
      final first = data.values.first;
      return first is List ? first.first.toString() : first.toString();
    }
    return fallback;
  }

  Future<Paginated<EmployeeModel>> fetchEmployees({
    String? search,
    int? sectorId,
    bool? isActive,
    int page = 1,
  }) async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.employees,
        queryParameters: {
          'page': page,
          if (search != null && search.isNotEmpty) 'search': search,
          if (sectorId != null) 'sector': sectorId,
          if (isActive != null) 'is_active': isActive.toString(),
        },
      );
      return Paginated.fromJson(
        response.data as Map<String, dynamic>,
        EmployeeModel.fromJson,
      );
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar colaboradores.'));
    }
  }

  Future<EmployeeModel> fetchEmployee(int id) async {
    try {
      final response = await httpClient.dio.get(ApiConstants.employeeDetail(id));
      return EmployeeModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar o colaborador.'));
    }
  }

  /// Atualiza o cadastro. Só envia o que mudou — assim um campo que a tela
  /// não exibe nunca é sobrescrito sem querer.
  Future<EmployeeModel> updateEmployee(
    int id, {
    String? fullName,
    String? phone,
    String? registrationNumber,
    String? role,
    int? sectorId,
    int? positionId,
    int? managerId,
    bool clearSector = false,
    bool clearPosition = false,
    bool clearManager = false,
    DateTime? hireDate,
    bool? isSectorLeader,
  }) async {
    try {
      final response = await httpClient.dio.patch(
        ApiConstants.employeeDetail(id),
        data: {
          if (fullName != null) 'full_name': fullName,
          if (phone != null) 'phone': phone,
          if (registrationNumber != null) 'registration_number': registrationNumber,
          if (role != null) 'role': role,
          // `null` é valor válido (remover vínculo), por isso o sinal explícito.
          if (sectorId != null || clearSector) 'sector': sectorId,
          if (positionId != null || clearPosition) 'position': positionId,
          if (managerId != null || clearManager) 'manager': managerId,
          if (hireDate != null) 'hire_date': hireDate.toIso8601String().split('T').first,
          if (isSectorLeader != null) 'is_sector_leader': isSectorLeader,
        },
      );
      return EmployeeModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao atualizar o colaborador.'));
    }
  }

  Future<EmployeeModel> toggleActive(int id) async {
    try {
      final response = await httpClient.dio.post(ApiConstants.employeeToggleActive(id));
      return EmployeeModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao alterar o status do colaborador.'));
    }
  }

  Future<List<RoleOption>> fetchRoles() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.employeeRoles);
      final list = response.data as List<dynamic>;
      return list.map((e) => RoleOption.fromJson(e as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar papéis.'));
    }
  }

  Future<List<ManagerOption>> fetchManagerOptions() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.employeeManagerOptions);
      final list = response.data as List<dynamic>;
      return list.map((e) => ManagerOption.fromJson(e as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar gestores.'));
    }
  }
}
