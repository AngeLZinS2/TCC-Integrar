import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../rh_dashboard/models/dashboard_overview_model.dart';
import '../models/company_model.dart';

class CompanyRepository {
  final HttpClient httpClient;

  CompanyRepository({required this.httpClient});

  Future<List<CompanyModel>> getCompanies() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.companies);
      final list = response.data as List<dynamic>;
      return list.map((e) => CompanyModel.fromJson(e as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao carregar empresas.';
      throw Exception(detail);
    }
  }

  Future<CompanyModel> createCompany({
    required String name,
    required String adminEmail,
    required String adminFullName,
    required String adminPassword,
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.companies,
        data: {
          'name': name,
          'admin_email': adminEmail,
          'admin_full_name': adminFullName,
          'admin_password': adminPassword,
        },
      );
      return CompanyModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      final data = e.response?.data;
      String detail = 'Erro ao cadastrar empresa.';
      if (data is Map) {
        final firstError = data.values.first;
        detail = firstError is List ? firstError.first.toString() : firstError.toString();
      }
      throw Exception(detail);
    }
  }

  Future<CompanyModel> toggleActive(int id) async {
    try {
      final response = await httpClient.dio.post(ApiConstants.companyToggleActive(id));
      return CompanyModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao atualizar empresa.';
      throw Exception(detail);
    }
  }

  Future<DashboardOverviewModel> getCompanyDashboard(int id) async {
    try {
      final response = await httpClient.dio.get(ApiConstants.companyDashboard(id));
      return DashboardOverviewModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao carregar estatísticas da empresa.';
      throw Exception(detail);
    }
  }

  Future<List<int>> exportCompaniesCsv() async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.companiesExport,
        options: Options(responseType: ResponseType.bytes),
      );
      return response.data as List<int>;
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao exportar empresas.';
      throw Exception(detail);
    }
  }
}
