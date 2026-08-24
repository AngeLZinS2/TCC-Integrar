import 'package:dio/dio.dart';

import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/automation_model.dart';
import '../../../shared/models/paginated_response.dart';

class AutomationsRepository {
  final HttpClient httpClient;

  AutomationsRepository({required this.httpClient});

  Future<PaginatedResponse<AutomationRule>> getRules({int page = 1}) async {
    final response = await httpClient.dio.get(
      ApiConstants.automationRules,
      queryParameters: {'page': page},
    );
    return PaginatedResponse.fromJson(
      response.data,
      (json) => AutomationRule.fromJson(json),
    );
  }

  Future<AutomationCatalog> getCatalog() async {
    final response = await httpClient.dio.get(ApiConstants.automationCatalog);
    return AutomationCatalog.fromJson(response.data);
  }

  Future<List<AutomationRun>> getRuns(int ruleId) async {
    final response = await httpClient.dio.get(
      ApiConstants.automationRuleRuns(ruleId),
    );
    return (response.data as List<dynamic>)
        .map((e) => AutomationRun.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<AutomationRule> createRule({
    required String name,
    required String triggerEvent,
    String description = '',
    List<AutomationCondition> conditions = const [],
    required List<AutomationAction> actions,
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.automationRules,
        data: {
          'name': name,
          'description': description,
          'trigger_event': triggerEvent,
          'conditions': conditions.map((c) => c.toJson()).toList(),
          'actions': actions.map((a) => a.toJson()).toList(),
        },
      );
      return AutomationRule.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível salvar a automação.'));
    }
  }

  Future<AutomationRule> toggleActive(int id, bool isActive) async {
    try {
      final response = await httpClient.dio.patch(
        ApiConstants.automationRuleDetail(id),
        data: {'is_active': isActive},
      );
      return AutomationRule.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível alterar a automação.'));
    }
  }

  Future<void> deleteRule(int id) async {
    await httpClient.dio.delete(ApiConstants.automationRuleDetail(id));
  }

  /// A validação do backend recusa `config` com campo não previsto e
  /// referência a outra empresa — a mensagem dele diz qual foi o problema.
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
