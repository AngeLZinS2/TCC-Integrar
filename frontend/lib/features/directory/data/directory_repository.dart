import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../models/directory_entry_model.dart';

class DirectoryRepository {
  final HttpClient httpClient;

  DirectoryRepository({required this.httpClient});

  Future<List<DirectoryEntryModel>> getDirectory({
    String? search,
    int? sectorId,
    int? positionId,
  }) async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.directory,
        queryParameters: {
          if (search != null && search.isNotEmpty) 'search': search,
          if (sectorId != null) 'sector': sectorId,
          if (positionId != null) 'position': positionId,
        },
      );
      final list = response.data as List<dynamic>;
      return list.map((e) => DirectoryEntryModel.fromJson(e as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao carregar diretório de colegas.';
      throw Exception(detail);
    }
  }
}
