import 'package:dio/dio.dart';

import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/onboarding_task_model.dart';
import '../../../shared/models/paginated_response.dart';

class OnboardingTasksRepository {
  final HttpClient httpClient;

  OnboardingTasksRepository({required this.httpClient});

  Future<PaginatedResponse<OnboardingTaskModel>> getTasks({
    int page = 1,
    String? status,
    int? employeeId,
    bool onlyMine = false,
    bool onlyOverdue = false,
  }) async {
    final response = await httpClient.dio.get(
      ApiConstants.onboardingTasks,
      queryParameters: {
        'page': page,
        if (status != null) 'status': status,
        if (employeeId != null) 'employee': employeeId,
        if (onlyMine) 'mine': 'true',
        if (onlyOverdue) 'overdue': 'true',
      },
    );
    return PaginatedResponse.fromJson(
      response.data,
      (json) => OnboardingTaskModel.fromJson(json),
    );
  }

  Future<OnboardingTaskModel> getTask(int id) async {
    final response = await httpClient.dio.get(
      ApiConstants.onboardingTaskDetail(id),
    );
    return OnboardingTaskModel.fromJson(response.data);
  }

  Future<MyOnboarding> getMyOnboarding() async {
    final response = await httpClient.dio.get(ApiConstants.onboardingMy);
    return MyOnboarding.fromJson(response.data);
  }

  Future<MyOnboarding> getEmployeeOnboarding(int employeeId) async {
    final response = await httpClient.dio.get(
      ApiConstants.onboardingEmployee(employeeId),
    );
    return MyOnboarding.fromJson(response.data);
  }

  /// Muda o status de uma tarefa.
  ///
  /// O backend responde 403 quando quem pediu não é o responsável — a
  /// mensagem dele é a que o usuário deve ver, e não um texto genérico.
  Future<OnboardingTaskModel> changeStatus(int id, String status) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.onboardingTaskStatus(id),
        data: {'status': status},
      );
      return OnboardingTaskModel.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível atualizar a tarefa.'));
    }
  }

  Future<List<TaskComment>> getComments(int taskId) async {
    final response = await httpClient.dio.get(
      ApiConstants.onboardingTaskComments(taskId),
    );
    return (response.data as List<dynamic>)
        .map((e) => TaskComment.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<TaskComment> addComment(
    int taskId,
    String message, {
    bool isInternal = false,
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.onboardingTaskComments(taskId),
        data: {'message': message, 'is_internal': isInternal},
      );
      return TaskComment.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível enviar o comentário.'));
    }
  }

  Future<OnboardingTaskModel> createTask({
    required String title,
    required int employeeId,
    String description = '',
    int? assignedToId,
    String? dueDate,
    String priority = 'normal',
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.onboardingTasks,
        data: {
          'title': title,
          'description': description,
          'employee': employeeId,
          if (assignedToId != null) 'assigned_to': assignedToId,
          if (dueDate != null) 'due_date': dueDate,
          'priority': priority,
        },
      );
      return OnboardingTaskModel.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível criar a tarefa.'));
    }
  }

  Future<void> deleteTask(int id) async {
    await httpClient.dio.delete(ApiConstants.onboardingTaskDetail(id));
  }

  // ── Templates ─────────────────────────────────────────────────────────

  Future<PaginatedResponse<OnboardingTemplateModel>> getTemplates({
    int page = 1,
  }) async {
    final response = await httpClient.dio.get(
      ApiConstants.onboardingTemplates,
      queryParameters: {'page': page},
    );
    return PaginatedResponse.fromJson(
      response.data,
      (json) => OnboardingTemplateModel.fromJson(json),
    );
  }

  Future<OnboardingTemplateModel> createTemplate({
    required String name,
    String description = '',
    int? sectorId,
    int? positionId,
    bool applyAutomatically = true,
    required List<TemplateTaskModel> tasks,
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.onboardingTemplates,
        data: {
          'name': name,
          'description': description,
          if (sectorId != null) 'sector': sectorId,
          if (positionId != null) 'position': positionId,
          'apply_automatically': applyAutomatically,
          'tasks': tasks.map((t) => t.toJson()).toList(),
        },
      );
      return OnboardingTemplateModel.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível salvar o roteiro.'));
    }
  }

  Future<void> deleteTemplate(int id) async {
    await httpClient.dio.delete(ApiConstants.onboardingTemplateDetail(id));
  }

  /// Aplica um roteiro a alguém que já está cadastrado.
  ///
  /// Devolve quantas tarefas nasceram: zero significa que a pessoa já tinha
  /// esse roteiro, e a tela precisa dizer isso em vez de "pronto!".
  Future<int> applyTemplate(int templateId, int employeeId) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.onboardingTemplateApply(templateId),
        data: {'employee': employeeId},
      );
      return response.data['created'] as int? ?? 0;
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível aplicar o roteiro.'));
    }
  }

  /// Extrai a mensagem que o backend mandou, se houver.
  ///
  /// O backend explica o motivo real ("Você não é o responsável por esta
  /// tarefa"); trocar isso por um texto genérico esconderia do usuário a
  /// única informação útil.
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
