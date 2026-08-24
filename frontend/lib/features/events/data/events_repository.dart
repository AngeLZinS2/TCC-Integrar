import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/event_model.dart';
import '../../../shared/models/paginated_response.dart';

class EventsRepository {
  final HttpClient httpClient;

  EventsRepository({required this.httpClient});

  Future<PaginatedResponse<EventModel>> getEvents({int page = 1}) async {
    final response = await httpClient.dio.get(
      ApiConstants.events,
      queryParameters: {'page': page},
    );
    return PaginatedResponse.fromJson(
      response.data,
      (json) => EventModel.fromJson(json),
    );
  }

  Future<List<BirthdayModel>> getBirthdays() async {
    final response = await httpClient.dio.get(ApiConstants.birthdays);
    final results = response.data['results'] as List;
    return results.map((e) => BirthdayModel.fromJson(e)).toList();
  }

  Future<EventModel> createEvent({
    required String title,
    required String description,
    required String date,
  }) async {
    final response = await httpClient.dio.post(
      ApiConstants.events,
      data: {
        'title': title,
        'description': description,
        'date': date,
      },
    );
    return EventModel.fromJson(response.data);
  }
}
