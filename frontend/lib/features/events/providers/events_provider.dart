import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../../../shared/models/event_model.dart';
import '../../../shared/models/paginated_response.dart';
import '../data/events_repository.dart';

final eventsRepositoryProvider = Provider<EventsRepository>((ref) {
  
  return EventsRepository(httpClient: ref.watch(httpClientProvider));
});

final eventsListProvider = FutureProvider.family<PaginatedResponse<EventModel>, int>((ref, page) {
  final repository = ref.watch(eventsRepositoryProvider);
  return repository.getEvents(page: page);
});

final birthdaysListProvider = FutureProvider<List<BirthdayModel>>((ref) {
  final repository = ref.watch(eventsRepositoryProvider);
  return repository.getBirthdays();
});
