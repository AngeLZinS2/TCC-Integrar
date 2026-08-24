import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../../../shared/models/announcement_model.dart';
import '../../../shared/models/paginated_response.dart';
import '../data/communications_repository.dart';

final communicationsRepositoryProvider = Provider<CommunicationsRepository>((ref) {
  
  return CommunicationsRepository(httpClient: ref.watch(httpClientProvider));
});

final communicationsListProvider = FutureProvider.family<PaginatedResponse<Announcement>, int>((ref, page) {
  final repository = ref.watch(communicationsRepositoryProvider);
  return repository.getAnnouncements(page: page);
});
