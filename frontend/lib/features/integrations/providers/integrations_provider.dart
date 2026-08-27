import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/models/integration_model.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/integrations_repository.dart';

final integrationsRepositoryProvider = Provider<IntegrationsRepository>((ref) {
  return IntegrationsRepository(httpClient: ref.watch(httpClientProvider));
});

final conexaoProvider = FutureProvider.autoDispose<ConexaoExterna>((ref) {
  return ref.watch(integrationsRepositoryProvider).getConexao();
});

/// A lista de bancos muda pouco; sem `autoDispose` para não rebuscar a cada
/// abertura do formulário.
final bancosSuportadosProvider = FutureProvider<List<OpcaoBanco>>((ref) {
  return ref.watch(integrationsRepositoryProvider).getBancos();
});

final tabelasProvider =
    FutureProvider.autoDispose<List<TabelaExterna>>((ref) {
  return ref.watch(integrationsRepositoryProvider).getTabelas();
});

final colunasProvider =
    FutureProvider.autoDispose.family<List<ColunaExterna>, String>((ref, tabela) {
  return ref.watch(integrationsRepositoryProvider).getColunas(tabela);
});

final amostraProvider =
    FutureProvider.autoDispose.family<AmostraDaTabela, String>((ref, tabela) {
  return ref.watch(integrationsRepositoryProvider).getAmostra(tabela);
});

final camposDisponiveisProvider =
    FutureProvider<List<EntidadeMapeavel>>((ref) {
  return ref.watch(integrationsRepositoryProvider).getCamposDisponiveis();
});

final mapeamentosProvider =
    FutureProvider.autoDispose<List<Mapeamento>>((ref) {
  return ref.watch(integrationsRepositoryProvider).getMapeamentos();
});
