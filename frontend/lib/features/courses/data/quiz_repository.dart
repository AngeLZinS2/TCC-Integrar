import 'package:dio/dio.dart';

import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/paginated_response.dart';
import '../../../shared/models/quiz_model.dart';

class QuizRepository {
  final HttpClient httpClient;

  QuizRepository({required this.httpClient});

  /// Busca a avaliação do treinamento.
  ///
  /// Devolve `null` no 404 — "este treinamento não tem avaliação" é um
  /// estado normal, não um erro para mostrar na tela.
  Future<QuizModel?> getQuiz(int courseId) async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.courseQuiz(courseId),
      );
      return QuizModel.fromJson(response.data);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  /// Abre uma tentativa e devolve (id da tentativa, avaliação).
  ///
  /// A tentativa é contada ao INICIAR: sem isso, bastaria fechar a tela ao
  /// ver uma pergunta difícil para recomeçar sem gastar tentativa.
  Future<({int attemptId, QuizModel quiz})> startAttempt(int courseId) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.quizAttempts(courseId),
      );
      return (
        attemptId: response.data['attempt']['id'] as int,
        quiz: QuizModel.fromJson(response.data['quiz']),
      );
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível iniciar a avaliação.'));
    }
  }

  Future<QuizAttempt> submit(
    int courseId,
    int attemptId,
    Map<int, List<int>> answers,
  ) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.quizSubmit(courseId, attemptId),
        data: {
          'answers': answers.map((k, v) => MapEntry(k.toString(), v)),
        },
      );
      return QuizAttempt.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível enviar as respostas.'));
    }
  }

  Future<PaginatedResponse<QuizAttempt>> getMyAttempts() async {
    final response = await httpClient.dio.get(ApiConstants.myQuizAttempts);
    return PaginatedResponse.fromJson(
      response.data,
      (json) => QuizAttempt.fromJson(json),
    );
  }

  String _mensagem(DioException e, String padrao) {
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) return detail;
    }
    return padrao;
  }
}
