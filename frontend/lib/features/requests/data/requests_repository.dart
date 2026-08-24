import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/hr_request_model.dart';
import '../../../shared/models/paginated_response.dart';

class RequestsRepository {
  final HttpClient httpClient;

  RequestsRepository({required this.httpClient});

  Future<PaginatedResponse<HRRequest>> getRequests({
    int page = 1,
    String? status,
    String? category,
  }) async {
    final queryParameters = <String, dynamic>{'page': page};
    if (status != null && status.isNotEmpty) queryParameters['status'] = status;
    if (category != null && category.isNotEmpty) queryParameters['category'] = category;

    final response = await httpClient.dio.get(
      ApiConstants.requests,
      queryParameters: queryParameters,
    );

    return PaginatedResponse.fromJson(
      response.data,
      (json) => HRRequest.fromJson(json),
    );
  }

  Future<HRRequest> getRequestDetail(int id) async {
    final response = await httpClient.dio.get(ApiConstants.requestDetail(id));
    return HRRequest.fromJson(response.data);
  }

  Future<HRRequest> createRequest({
    required String category,
    required String subject,
    required String description,
    required String priority,
  }) async {
    final response = await httpClient.dio.post(
      ApiConstants.requests,
      data: {
        'category': category,
        'subject': subject,
        'description': description,
        'priority': priority,
      },
    );
    return HRRequest.fromJson(response.data);
  }

  Future<HRRequest> updateStatus(int id, String status) async {
    final response = await httpClient.dio.patch(
      ApiConstants.requestStatus(id),
      data: {'status': status},
    );
    return HRRequest.fromJson(response.data);
  }

  Future<RequestComment> addComment(int id, String text) async {
    final response = await httpClient.dio.post(
      ApiConstants.requestComments(id),
      data: {'text': text},
    );
    return RequestComment.fromJson(response.data);
  }
}
