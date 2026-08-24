import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/checklist_model.dart';

class ChecklistRepository {
  final HttpClient httpClient;

  ChecklistRepository({required this.httpClient});

  Future<List<ChecklistItemModel>> fetchChecklist() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.checklist);
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
            .map((item) => ChecklistItemModel.fromJson(item as Map<String, dynamic>))
            .toList();
      } else {
        throw Exception('Falha ao carregar checklist de integração.');
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro de conexão ao carregar checklist.';
      throw Exception(detail);
    }
  }

  Future<bool> toggleItem(int itemId, {bool? completed}) async {
    try {
      final response = await httpClient.dio.post(
        '${ApiConstants.checklist}$itemId/toggle/',
        data: completed != null ? {'completed': completed} : {},
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        return data['completed'] as bool? ?? false;
      }
      return false;
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao atualizar item do checklist.';
      throw Exception(detail);
    }
  }
}
