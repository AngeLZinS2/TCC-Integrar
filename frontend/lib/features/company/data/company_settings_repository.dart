import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../models/company_settings_model.dart';

/// Dados e configuração da PRÓPRIA empresa.
///
/// Nenhum método recebe id de empresa: o backend resolve o tenant pelo
/// usuário autenticado, então não há parâmetro para manipular.
class CompanySettingsRepository {
  final HttpClient httpClient;

  CompanySettingsRepository({required this.httpClient});

  String _errorFrom(DioException e, String fallback) {
    final data = e.response?.data;
    if (data is Map && data.isNotEmpty) {
      final first = data.values.first;
      return first is List ? first.first.toString() : first.toString();
    }
    return fallback;
  }

  Future<CompanySettingsModel> fetch() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.myCompany);
      return CompanySettingsModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar os dados da empresa.'));
    }
  }

  Future<CompanySettingsModel> update({
    String? name,
    String? legalName,
    String? cnpj,
    String? description,
    String? phone,
    String? email,
    String? address,
    String? logoUrl,
  }) async {
    try {
      final response = await httpClient.dio.patch(
        ApiConstants.myCompany,
        data: {
          if (name != null) 'name': name,
          if (legalName != null) 'legal_name': legalName,
          if (cnpj != null) 'cnpj': cnpj,
          if (description != null) 'description': description,
          if (phone != null) 'phone': phone,
          if (email != null) 'email': email,
          if (address != null) 'address': address,
          if (logoUrl != null) 'logo_url': logoUrl,
        },
      );
      return CompanySettingsModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao salvar os dados da empresa.'));
    }
  }

  Future<SetupChecklist> fetchSetupChecklist() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.myCompanySetup);
      return SetupChecklist.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar o progresso da configuração.'));
    }
  }
}
