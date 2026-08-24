import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../org/models/org_models.dart' show Paginated;
import '../models/audit_log_model.dart';

class AuditRepository {
  final HttpClient httpClient;

  AuditRepository({required this.httpClient});

  String _errorFrom(DioException e, String fallback) {
    final data = e.response?.data;
    if (data is Map && data.isNotEmpty) {
      final first = data.values.first;
      return first is List ? first.first.toString() : first.toString();
    }
    return fallback;
  }

  Future<Paginated<AuditLogModel>> fetchLogs({
    String? action,
    String? resourceType,
    DateTime? dateFrom,
    DateTime? dateTo,
    int page = 1,
  }) async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.audit,
        queryParameters: {
          'page': page,
          if (action != null && action.isNotEmpty) 'action': action,
          if (resourceType != null && resourceType.isNotEmpty) 'resource_type': resourceType,
          if (dateFrom != null) 'date_from': dateFrom.toIso8601String().split('T').first,
          if (dateTo != null) 'date_to': dateTo.toIso8601String().split('T').first,
        },
      );
      return Paginated.fromJson(
        response.data as Map<String, dynamic>,
        AuditLogModel.fromJson,
      );
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar o histórico de atividades.'));
    }
  }

  Future<List<AuditFilterOption>> fetchActions() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.auditFilters);
      final list = (response.data as Map<String, dynamic>)['actions'] as List<dynamic>;
      return list.map((e) => AuditFilterOption.fromJson(e as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      throw Exception(_errorFrom(e, 'Erro ao carregar os filtros.'));
    }
  }
}
