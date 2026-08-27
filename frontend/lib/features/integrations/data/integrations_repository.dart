import 'package:dio/dio.dart';

import '../../../core/constants/api_constants.dart';
import '../../../core/network/http_client.dart';
import '../../../shared/models/integration_model.dart';

class IntegrationsRepository {
  final HttpClient httpClient;

  IntegrationsRepository({required this.httpClient});

  Future<List<OpcaoBanco>> getBancos() async {
    final response = await httpClient.dio.get(ApiConstants.integrationDatabases);
    return (response.data as List<dynamic>)
        .map((e) => OpcaoBanco.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<ConexaoExterna> getConexao() async {
    final response = await httpClient.dio.get(ApiConstants.integrationConnection);
    return ConexaoExterna.fromJson(response.data);
  }

  /// Salva a conexão.
  ///
  /// `senha` vazia mantém a que já está guardada — é o que o formulário
  /// manda quando o administrador não quer trocá-la.
  Future<ConexaoExterna> salvarConexao({
    required String tipo,
    required String host,
    int? porta,
    required String banco,
    String schema = '',
    required String usuario,
    String senha = '',
    bool usarSsl = false,
    int timeoutSegundos = 10,
    bool isActive = true,
  }) async {
    try {
      final response = await httpClient.dio.put(
        ApiConstants.integrationConnection,
        data: {
          'tipo': tipo,
          'host': host,
          if (porta != null) 'porta': porta,
          'banco': banco,
          'schema': schema,
          'usuario': usuario,
          'senha': senha,
          'usar_ssl': usarSsl,
          'timeout_segundos': timeoutSegundos,
          'is_active': isActive,
        },
      );
      return ConexaoExterna.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível salvar a conexão.'));
    }
  }

  /// Testa a conexão.
  ///
  /// Falha NÃO é exceção aqui: "não conectou" é a resposta esperada de um
  /// teste, e a tela precisa do motivo para mostrar. Só erro de transporte
  /// vira exceção.
  Future<ResultadoDoTeste> testarConexao() async {
    try {
      final response =
          await httpClient.dio.post(ApiConstants.integrationConnectionTest);
      return ResultadoDoTeste.fromJson(response.data);
    } on DioException catch (e) {
      final dados = e.response?.data;
      if (dados is Map<String, dynamic>) {
        return ResultadoDoTeste.fromJson(dados);
      }
      return const ResultadoDoTeste(
        ok: false,
        mensagem: 'Não foi possível falar com o servidor.',
      );
    }
  }

  Future<void> removerConexao() async {
    await httpClient.dio.delete(ApiConstants.integrationConnection);
  }

  Future<List<TabelaExterna>> getTabelas() async {
    try {
      final response =
          await httpClient.dio.get(ApiConstants.integrationDiscovery);
      return (response.data['tabelas'] as List<dynamic>)
          .map((e) => TabelaExterna.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível ler as tabelas.'));
    }
  }

  Future<List<ColunaExterna>> getColunas(String tabela) async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.integrationDiscovery,
        queryParameters: {'tabela': tabela},
      );
      return (response.data['colunas'] as List<dynamic>)
          .map((e) => ColunaExterna.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível ler as colunas.'));
    }
  }

  /// Uma amostra das primeiras linhas — o que o administrador confere
  /// antes de mapear campo nenhum.
  Future<AmostraDaTabela> getAmostra(String tabela, {int limite = 10}) async {
    try {
      final response = await httpClient.dio.get(
        ApiConstants.integrationPreview,
        queryParameters: {'tabela': tabela, 'limite': limite},
      );
      return AmostraDaTabela.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível ler os dados.'));
    }
  }

  Future<List<EntidadeMapeavel>> getCamposDisponiveis() async {
    final response = await httpClient.dio.get(ApiConstants.integrationFields);
    return (response.data['entidades'] as List<dynamic>)
        .map((e) => EntidadeMapeavel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<Mapeamento>> getMapeamentos() async {
    final response = await httpClient.dio.get(ApiConstants.integrationMappings);
    return (response.data['mapeamentos'] as List<dynamic>)
        .map((e) => Mapeamento.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Grava o mapeamento de uma entidade.
  ///
  /// O servidor confere tabela e colunas contra o banco de verdade — se
  /// não existirem lá, nada é gravado, e a mensagem diz o que faltou.
  Future<Mapeamento> salvarMapeamento({
    required String entidade,
    required String tabela,
    required Map<String, String> campos,
  }) async {
    try {
      final response = await httpClient.dio.put(
        ApiConstants.integrationMapping(entidade),
        data: {'tabela': tabela, 'campos': campos},
      );
      return Mapeamento.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception(_mensagem(e, 'Não foi possível salvar o mapeamento.'));
    }
  }

  /// Executa uma consulta escrita pelo administrador.
  ///
  /// Recusa NÃO é exceção: "a trava bloqueou" e "o banco recusou" são
  /// respostas esperadas de um console de consulta, e a tela precisa do
  /// motivo para mostrar.
  Future<ResultadoDaConsulta> executarConsulta(
    String sql, {
    int limite = 50,
  }) async {
    try {
      final response = await httpClient.dio.post(
        ApiConstants.integrationQuery,
        data: {'sql': sql, 'limite': limite},
      );
      return ResultadoDaConsulta.fromJson(response.data);
    } on DioException catch (e) {
      final dados = e.response?.data;
      if (dados is Map<String, dynamic>) {
        return ResultadoDaConsulta.falha(
          dados['detail']?.toString() ?? 'Não foi possível executar.',
          bloqueada: dados['bloqueada'] == true,
        );
      }
      return ResultadoDaConsulta.falha('Não foi possível falar com o servidor.');
    }
  }

  /// O backend traduz o erro do driver em frase legível — é essa mensagem
  /// que interessa, não o texto cru, que traz host e usuário.
  String _mensagem(DioException e, String padrao) {
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) return detail;
      for (final valor in data.values) {
        if (valor is List && valor.isNotEmpty) return valor.first.toString();
        if (valor is String && valor.isNotEmpty) return valor;
      }
    }
    return padrao;
  }
}
