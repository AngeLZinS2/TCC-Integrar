import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/directory_repository.dart';
import '../models/directory_entry_model.dart';

final directoryRepositoryProvider = Provider<DirectoryRepository>((ref) {
  final httpClient = ref.watch(httpClientProvider);
  return DirectoryRepository(httpClient: httpClient);
});

/// Diretório completo da empresa.
///
/// Sem paginação de propósito: a tela tem modo organograma, que precisa da
/// estrutura inteira para desenhar a hierarquia. Como a lista já vem toda,
/// busca e filtros acontecem no cliente — resposta instantânea e sem
/// round-trip a cada tecla. A API também aceita os mesmos filtros
/// (?search=&sector=&position=) para outros consumidores.
final directoryListProvider = FutureProvider<List<DirectoryEntryModel>>((ref) {
  final repository = ref.watch(directoryRepositoryProvider);
  return repository.getDirectory();
});
