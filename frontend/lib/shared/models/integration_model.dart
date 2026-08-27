// Conexão com o banco de origem da empresa (P4).
//
// Repare no que NÃO existe aqui: nenhum campo de senha para leitura. Ela é
// `write_only` no servidor, e o que chega é `temSenha` — o suficiente para
// o formulário dizer "senha já cadastrada" sem devolver o valor a quem
// estiver olhando a tela junto.

class OpcaoBanco {
  final String valor;
  final String rotulo;

  const OpcaoBanco({required this.valor, required this.rotulo});

  factory OpcaoBanco.fromJson(Map<String, dynamic> json) => OpcaoBanco(
        valor: json['value'] ?? '',
        rotulo: json['label'] ?? '',
      );
}

class ConexaoExterna {
  final bool configurada;
  final int? id;
  final String tipo;
  final String tipoDisplay;
  final String host;
  final int? porta;
  final String banco;
  final String schema;
  final String usuario;
  final bool temSenha;
  final bool usarSsl;
  final int timeoutSegundos;
  final bool isActive;
  final String status;
  final String statusDisplay;
  final String? ultimoTesteEm;
  final String ultimoErro;

  const ConexaoExterna({
    this.configurada = false,
    this.id,
    this.tipo = 'postgresql',
    this.tipoDisplay = '',
    this.host = '',
    this.porta,
    this.banco = '',
    this.schema = '',
    this.usuario = '',
    this.temSenha = false,
    this.usarSsl = false,
    this.timeoutSegundos = 10,
    this.isActive = true,
    this.status = 'untested',
    this.statusDisplay = '',
    this.ultimoTesteEm,
    this.ultimoErro = '',
  });

  bool get conectando => status == 'ok';
  bool get comFalha => status == 'failed';

  factory ConexaoExterna.fromJson(Map<String, dynamic> json) {
    return ConexaoExterna(
      configurada: json['configurada'] ?? false,
      id: json['id'],
      tipo: json['tipo'] ?? 'postgresql',
      tipoDisplay: json['tipo_display'] ?? '',
      host: json['host'] ?? '',
      porta: json['porta'],
      banco: json['banco'] ?? '',
      schema: json['schema'] ?? '',
      usuario: json['usuario'] ?? '',
      temSenha: json['tem_senha'] ?? false,
      usarSsl: json['usar_ssl'] ?? false,
      timeoutSegundos: json['timeout_segundos'] ?? 10,
      isActive: json['is_active'] ?? true,
      status: json['status'] ?? 'untested',
      statusDisplay: json['status_display'] ?? '',
      ultimoTesteEm: json['ultimo_teste_em'],
      ultimoErro: json['ultimo_erro'] ?? '',
    );
  }
}

class ResultadoDoTeste {
  final bool ok;
  final String mensagem;
  final int tabelasEncontradas;

  const ResultadoDoTeste({
    required this.ok,
    required this.mensagem,
    this.tabelasEncontradas = 0,
  });

  factory ResultadoDoTeste.fromJson(Map<String, dynamic> json) =>
      ResultadoDoTeste(
        ok: json['ok'] ?? false,
        mensagem: json['detail'] ?? '',
        tabelasEncontradas: json['tabelas_encontradas'] ?? 0,
      );
}

class TabelaExterna {
  final String nome;
  final String schema;
  final String nomeCompleto;

  const TabelaExterna({
    required this.nome,
    this.schema = '',
    required this.nomeCompleto,
  });

  factory TabelaExterna.fromJson(Map<String, dynamic> json) => TabelaExterna(
        nome: json['nome'] ?? '',
        schema: json['schema'] ?? '',
        nomeCompleto: json['nome_completo'] ?? json['nome'] ?? '',
      );
}

class ColunaExterna {
  final String nome;
  final String tipo;
  final bool aceitaNulo;
  final bool eChave;

  const ColunaExterna({
    required this.nome,
    required this.tipo,
    this.aceitaNulo = true,
    this.eChave = false,
  });

  factory ColunaExterna.fromJson(Map<String, dynamic> json) => ColunaExterna(
        nome: json['nome'] ?? '',
        tipo: json['tipo'] ?? '',
        aceitaNulo: json['aceita_nulo'] ?? true,
        eChave: json['e_chave'] ?? false,
      );
}

/// Uma amostra do que o banco devolve.
///
/// Tudo em texto: a tela só exibe, e data, decimal e bytes de cada banco
/// não têm equivalente direto em JSON.
class AmostraDaTabela {
  final String tabela;
  final List<String> colunas;
  final List<Map<String, String>> linhas;

  const AmostraDaTabela({
    required this.tabela,
    required this.colunas,
    required this.linhas,
  });

  factory AmostraDaTabela.fromJson(Map<String, dynamic> json) {
    return AmostraDaTabela(
      tabela: json['tabela'] ?? '',
      colunas: (json['colunas'] as List<dynamic>? ?? const [])
          .map((e) => e.toString())
          .toList(),
      linhas: (json['linhas'] as List<dynamic>? ?? const [])
          .map((e) => (e as Map<String, dynamic>)
              .map((k, v) => MapEntry(k, v?.toString() ?? '')))
          .toList(),
    );
  }
}

/// Um campo que o sistema precisa saber.
///
/// O catálogo vem do servidor — a tela não mantém cópia, porque uma cópia
/// desatualizada pediria um campo que o servidor já não usa.
class CampoInterno {
  final String chave;
  final String rotulo;
  final String ajuda;
  final bool obrigatorio;

  const CampoInterno({
    required this.chave,
    required this.rotulo,
    required this.ajuda,
    required this.obrigatorio,
  });

  factory CampoInterno.fromJson(Map<String, dynamic> json) => CampoInterno(
        chave: json['chave'] ?? '',
        rotulo: json['rotulo'] ?? '',
        ajuda: json['ajuda'] ?? '',
        obrigatorio: json['obrigatorio'] ?? false,
      );
}

class EntidadeMapeavel {
  final String chave;
  final String rotulo;
  final List<CampoInterno> campos;

  const EntidadeMapeavel({
    required this.chave,
    required this.rotulo,
    required this.campos,
  });

  List<CampoInterno> get obrigatorios =>
      campos.where((c) => c.obrigatorio).toList();
  List<CampoInterno> get opcionais =>
      campos.where((c) => !c.obrigatorio).toList();

  factory EntidadeMapeavel.fromJson(Map<String, dynamic> json) =>
      EntidadeMapeavel(
        chave: json['chave'] ?? '',
        rotulo: json['rotulo'] ?? '',
        campos: (json['campos'] as List<dynamic>? ?? const [])
            .map((e) => CampoInterno.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

/// O que já foi apontado para uma entidade.
class Mapeamento {
  final String entidade;
  final String rotulo;
  final String tabela;
  final Map<String, String> campos;
  final bool configurado;

  const Mapeamento({
    required this.entidade,
    required this.rotulo,
    required this.tabela,
    required this.campos,
    required this.configurado,
  });

  factory Mapeamento.fromJson(Map<String, dynamic> json) => Mapeamento(
        entidade: json['entidade'] ?? '',
        rotulo: json['rotulo'] ?? '',
        tabela: json['tabela'] ?? '',
        campos: (json['campos'] as Map<String, dynamic>? ?? const {})
            .map((k, v) => MapEntry(k, v?.toString() ?? '')),
        configurado: json['configurado'] ?? false,
      );
}

/// O resultado de uma consulta escrita pelo administrador.
///
/// `bloqueada` separa duas coisas que a tela precisa dizer de forma
/// diferente: a trava recusou a consulta (é regra), ou o banco recusou
/// (é erro de sintaxe, tabela inexistente, permissão).
class ResultadoDaConsulta {
  final List<String> colunas;
  final List<Map<String, String>> linhas;
  final String? erro;
  final bool bloqueada;

  const ResultadoDaConsulta({
    this.colunas = const [],
    this.linhas = const [],
    this.erro,
    this.bloqueada = false,
  });

  bool get ok => erro == null;

  factory ResultadoDaConsulta.fromJson(Map<String, dynamic> json) {
    return ResultadoDaConsulta(
      colunas: (json['colunas'] as List<dynamic>? ?? const [])
          .map((e) => e.toString())
          .toList(),
      linhas: (json['linhas'] as List<dynamic>? ?? const [])
          .map((e) => (e as Map<String, dynamic>)
              .map((k, v) => MapEntry(k, v?.toString() ?? '')))
          .toList(),
    );
  }

  factory ResultadoDaConsulta.falha(String mensagem, {bool bloqueada = false}) =>
      ResultadoDaConsulta(erro: mensagem, bloqueada: bloqueada);
}
