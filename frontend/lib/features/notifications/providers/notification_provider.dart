import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/models/notification_model.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/notification_repository.dart';

final notificationRepositoryProvider = Provider<NotificationRepository>((ref) {
  final httpClient = ref.watch(httpClientProvider);
  return NotificationRepository(httpClient: httpClient);
});

class NotificationNotifier extends StateNotifier<AsyncValue<List<NotificationModel>>> {
  final NotificationRepository _repository;

  NotificationNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadNotifications();
  }

  Future<void> loadNotifications() async {
    state = const AsyncValue.loading();
    try {
      final items = await _repository.fetchNotifications();
      state = AsyncValue.data(items);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> markAsRead(int id) async {
    final currentList = state.value;
    if (currentList == null) return;

    state = AsyncValue.data(
      currentList.map((n) {
        if (n.id == id) {
          return n.copyWith(isRead: true);
        }
        return n;
      }).toList(),
    );

    await _repository.markAsRead(id);
  }

  Future<void> markAllAsRead() async {
    final currentList = state.value;
    if (currentList == null) return;

    state = AsyncValue.data(
      currentList.map((n) => n.copyWith(isRead: true)).toList(),
    );

    await _repository.markAllAsRead();
  }
}

final notificationsProvider =
    StateNotifierProvider<NotificationNotifier, AsyncValue<List<NotificationModel>>>((ref) {
  final repository = ref.watch(notificationRepositoryProvider);
  return NotificationNotifier(repository);
});

final unreadNotificationsCountProvider = Provider<int>((ref) {
  final notificationsAsync = ref.watch(notificationsProvider);
  return notificationsAsync.maybeWhen(
    data: (list) => list.where((n) => !n.isRead).length,
    orElse: () => 0,
  );
});
