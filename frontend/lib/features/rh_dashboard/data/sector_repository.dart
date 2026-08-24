import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../models/sector_model.dart';

class SectorRepository {
  final HttpClient httpClient;

  SectorRepository({required this.httpClient});

  List<dynamic> _extractList(dynamic data) {
    if (data is Map<String, dynamic> && data.containsKey('results')) {
      return data['results'] as List<dynamic>;
    }
    if (data is List<dynamic>) return data;
    return [];
  }

  Future<List<SectorModel>> getSectors() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.sectors);
      return _extractList(response.data)
          .map((e) => SectorModel.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao carregar setores.';
      throw Exception(detail);
    }
  }

  Future<List<PositionModel>> getPositions({int? sectorId}) async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.positions,
        queryParameters: sectorId != null ? {'sector': sectorId} : null,
      );
      return _extractList(response.data)
          .map((e) => PositionModel.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao carregar cargos.';
      throw Exception(detail);
    }
  }
}
