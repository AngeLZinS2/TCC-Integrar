import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../../../shared/models/document_model.dart';
import '../../../shared/models/paginated_response.dart';
import '../data/documents_repository.dart';

final documentsRepositoryProvider = Provider<DocumentsRepository>((ref) {
  
  return DocumentsRepository(httpClient: ref.watch(httpClientProvider));
});

final documentsListProvider = FutureProvider.family<PaginatedResponse<DocumentModel>, int>((ref, page) {
  final repository = ref.watch(documentsRepositoryProvider);
  return repository.getDocuments(page: page);
});
