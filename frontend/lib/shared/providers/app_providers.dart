import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/http_client.dart';
import '../services/storage_service.dart';
import '../../features/auth/data/auth_repository.dart';

final storageServiceProvider = Provider<StorageService>((ref) {
  return StorageService();
});

final httpClientProvider = Provider<HttpClient>((ref) {
  final storageService = ref.watch(storageServiceProvider);
  return HttpClient(storageService: storageService);
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final httpClient = ref.watch(httpClientProvider);
  final storageService = ref.watch(storageServiceProvider);
  return AuthRepository(httpClient: httpClient, storageService: storageService);
});
