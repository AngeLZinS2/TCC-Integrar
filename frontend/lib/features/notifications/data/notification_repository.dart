import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/notification_model.dart';

class NotificationRepository {
  final HttpClient httpClient;

  NotificationRepository({required this.httpClient});

  Future<List<NotificationModel>> fetchNotifications() async {
    try {
      final response = await httpClient.dio.get(ApiConstants.notifications);
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
            .map((item) => NotificationModel.fromJson(item as Map<String, dynamic>))
            .toList();
      } else {
        throw Exception('Falha ao carregar notificações.');
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Erro de conexão ao carregar notificações.';
      throw Exception(detail);
    }
  }

  Future<void> markAsRead(int notificationId) async {
    try {
      await httpClient.dio.post('${ApiConstants.notifications}$notificationId/read/');
    } catch (_) {}
  }

  Future<void> markAllAsRead() async {
    try {
      await httpClient.dio.post('${ApiConstants.notifications}mark-all-read/');
    } catch (_) {}
  }
}
