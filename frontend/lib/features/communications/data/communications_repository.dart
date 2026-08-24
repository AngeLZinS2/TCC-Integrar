import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/announcement_model.dart';
import '../../../shared/models/paginated_response.dart';

class CommunicationsRepository {
  final HttpClient httpClient;

  CommunicationsRepository({required this.httpClient});

  Future<PaginatedResponse<Announcement>> getAnnouncements({int page = 1}) async {
    final response = await httpClient.dio.get(
      ApiConstants.communications,
      queryParameters: {'page': page},
    );
    return PaginatedResponse.fromJson(
      response.data,
      (json) => Announcement.fromJson(json),
    );
  }

  Future<Announcement> createAnnouncement({
    required String title,
    required String content,
    required bool isUrgent,
    List<int> targetSectors = const [],
    List<int> targetPositions = const [],
  }) async {
    final response = await httpClient.dio.post(
      ApiConstants.communications,
      data: {
        'title': title,
        'content': content,
        'is_urgent': isUrgent,
        'target_sectors': targetSectors,
        'target_positions': targetPositions,
      },
    );
    return Announcement.fromJson(response.data);
  }

  Future<void> markAsRead(int id) async {
    await httpClient.dio.post(ApiConstants.communicationRead(id));
  }
}
