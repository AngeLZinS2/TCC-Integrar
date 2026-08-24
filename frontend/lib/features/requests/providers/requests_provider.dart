import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../../../shared/models/hr_request_model.dart';
import '../../../shared/models/paginated_response.dart';
import '../data/requests_repository.dart';

final requestsRepositoryProvider = Provider<RequestsRepository>((ref) {
  
  return RequestsRepository(httpClient: ref.watch(httpClientProvider));
});

final requestsListProvider = FutureProvider.family<PaginatedResponse<HRRequest>, Map<String, dynamic>>((ref, filters) {
  final repository = ref.watch(requestsRepositoryProvider);
  final page = filters['page'] as int? ?? 1;
  final status = filters['status'] as String?;
  final category = filters['category'] as String?;
  return repository.getRequests(page: page, status: status, category: category);
});

final requestDetailProvider = FutureProvider.family<HRRequest, int>((ref, id) {
  final repository = ref.watch(requestsRepositoryProvider);
  return repository.getRequestDetail(id);
});
