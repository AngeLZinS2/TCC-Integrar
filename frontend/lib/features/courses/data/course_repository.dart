import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/course_model.dart';

class CourseRepository {
  final HttpClient httpClient;

  CourseRepository({required this.httpClient});

  Future<List<CourseModel>> fetchCourses() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.courses);

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
            .map((item) => CourseModel.fromJson(item as Map<String, dynamic>))
            .toList();
      } else {
        throw Exception('Falha ao carregar trilha de treinamentos.');
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro de conexão ao carregar treinamentos.';
      throw Exception(detail);
    }
  }

  Future<CourseModel> fetchCourseDetail(int courseId) async {
    try {
      final response = await httpClient.dio.get('${ApiConstants.courses}$courseId/');
      if (response.statusCode == 200) {
        return CourseModel.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw Exception('Falha ao carregar detalhes do treinamento.');
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao buscar treinamento.';
      throw Exception(detail);
    }
  }

  Future<CourseModel> createCourse({
    required String title,
    String description = '',
    int? sectorId,
    int? positionId,
    String? deadline,
    int? prerequisiteId,
    int order = 0,
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.courses,
        data: {
          'title': title,
          'description': description,
          'sector': sectorId,
          'position': positionId,
          'deadline': deadline,
          'prerequisite': prerequisiteId,
          'order': order,
        },
      );
      return CourseModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      final data = e.response?.data;
      String detail = 'Erro ao cadastrar treinamento.';
      if (data is Map && data.isNotEmpty) {
        final firstError = data.values.first;
        detail = firstError is List ? firstError.first.toString() : firstError.toString();
      }
      throw Exception(detail);
    }
  }

  Future<UserCourseProgress> updateProgress({
    required int courseId,
    required String status,
  }) async {
    try {
      final response = await httpClient.dio.patch(
        '${ApiConstants.courses}$courseId/progress/',
        data: {'status': status},
      );

      if (response.statusCode == 200) {
        return UserCourseProgress.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw Exception('Falha ao atualizar progresso do treinamento.');
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro ao atualizar progresso.';
      throw Exception(detail);
    }
  }
}
