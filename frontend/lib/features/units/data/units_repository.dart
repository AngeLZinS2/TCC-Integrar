import 'package:dio/dio.dart';

import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/paginated_response.dart';
import '../../../shared/models/unit_model.dart';

class UnitsRepository {
  final HttpClient httpClient;

  UnitsRepository({required this.httpClient});

  Future<PaginatedResponse<UnitModel>> getUnits({int page = 1}) async {
    final response = await httpClient.dio.get(
      ApiConstants.units,
      queryParameters: {'page': page},
    );
    return PaginatedResponse.fromJson(
      response.data,
      (json) => UnitModel.fromJson(json),
    );
  }

  Future<UnitModel> createUnit({
    required String name,
    String code = '',
    String address = '',
    String city = '',
    String state = '',
    int? managerId,
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.units,
        data: {
          'name': name,
          'code': code,
          'address': address,
          'city': city,
          'state': state,
          if (managerId != null) 'manager': managerId,
        },
      );
      return UnitModel.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível salvar a unidade.'));
    }
  }

  Future<UnitModel> updateUnit(int id, Map<String, dynamic> dados) async {
    try {
      final response = await httpClient.dio.patch(
        ApiConstants.unitDetail(id),
        data: dados,
      );
      return UnitModel.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível atualizar a unidade.'));
    }
  }

  Future<void> deleteUnit(int id) async {
    await httpClient.dio.delete(ApiConstants.unitDetail(id));
  }

  /// Erros de nome/código duplicado vêm por campo, não em `detail` — é essa
  /// mensagem que o formulário precisa mostrar.
  String _mensagem(DioException e, String padrao) {
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) return detail;
      for (final valor in data.values) {
        if (valor is List && valor.isNotEmpty) return valor.first.toString();
        if (valor is String && valor.isNotEmpty) return valor;
      }
    }
    return padrao;
  }
}
