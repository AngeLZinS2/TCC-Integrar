import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/material_model.dart';

class MaterialRepository {
  final HttpClient httpClient;

  MaterialRepository({required this.httpClient});

  Future<List<MaterialModel>> fetchMaterials() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.materials);
      if (response.statusCode == 200) {
        final dynamic data = response.data;
        List<dynamic> list;
        if (data is Map<String, dynamic> && data.containsKey('results')) {
          list = data['results'] as List<dynamic>;
        } else if (data is List<dynamic>) {
          list = data;
        } else {
          list = [];
        }

        return list
            .map((item) => MaterialModel.fromJson(item as Map<String, dynamic>))
            .toList();
      } else {
        throw Exception('Falha ao carregar materiais de integração.');
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro de conexão ao carregar materiais.';
      throw Exception(detail);
    }
  }

  Future<MaterialModel> createMaterial({
    required String title,
    required String fileUrl,
    int? sectorId,
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.materials,
        data: {
          'title': title,
          'file_url': fileUrl,
          'sector': sectorId,
        },
      );
      return MaterialModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      final data = e.response?.data;
      String detail = 'Erro ao cadastrar material.';
      if (data is Map && data.isNotEmpty) {
        final firstError = data.values.first;
        detail = firstError is List ? firstError.first.toString() : firstError.toString();
      }
      throw Exception(detail);
    }
  }
}
