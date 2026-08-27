import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_motion.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../../shared/models/integration_model.dart';
import '../providers/integrations_provider.dart';

/// Conectar o banco da empresa.
///
/// A linguagem segue a seção 44 da P4: o administrador não é programador.
/// Nada de "FK source" nem "target column" — e o aviso mais importante da
/// tela é que a plataforma **nunca escreve** no banco dele, porque é isso
/// que decide se ele vai autorizar a conexão.
class IntegrationScreen extends ConsumerWidget {
  const IntegrationScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final conexaoAsync = ref.watch(conexaoProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(conexaoProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 860),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const AppSectionHeader(
                    title: 'Integração com o seu banco',
                    subtitle:
                        'Traga colaboradores, setores e cargos direto do sistema que a sua empresa já usa.',
                  ),
                  const SizedBox(height: AppSpacing.xl),
                  const _AvisoSomenteLeitura(),
                  const SizedBox(height: AppSpacing.xl),
                  conexaoAsync.whenAnimado(
                    context,
                    loading: () => const AppSkeleton.card(height: 320),
                    error: (_, __) => AppErrorState(
                      message: 'Não foi possível carregar a configuração.',
                      onRetry: () => ref.invalidate(conexaoProvider),
                    ),
                    data: (conexao) => _Formulario(conexao: conexao),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// O aviso que decide se o administrador autoriza a conexão.
///
/// Fica acima do formulário de propósito: é a informação que ele precisa
/// antes de digitar a senha do banco de produção, não depois.
class _AvisoSomenteLeitura extends StatelessWidget {
  const _AvisoSomenteLeitura();

  @override
  Widget build(BuildContext context) {
    return AppFadeIn(
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.lg),
        decoration: BoxDecoration(
          color: AppColors.success.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: AppColors.success.withValues(alpha: 0.3)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.lock_outline, size: 20, color: AppColors.success),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'O seu banco é apenas lido. Nunca alterado.',
                    style: context.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: context.textPrimaryColor,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'A plataforma não executa nenhum comando capaz de criar, '
                    'alterar ou excluir dados. Recomendamos cadastrar um '
                    'usuário com permissão somente de leitura (SELECT).',
                    style: context.textTheme.bodySmall?.copyWith(
                      color: context.textSecondaryColor,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Formulario extends ConsumerStatefulWidget {
  final ConexaoExterna conexao;

  const _Formulario({required this.conexao});

  @override
  ConsumerState<_Formulario> createState() => _FormularioState();
}

class _FormularioState extends ConsumerState<_Formulario> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _host;
  late final TextEditingController _porta;
  late final TextEditingController _banco;
  late final TextEditingController _schema;
  late final TextEditingController _usuario;
  final _senha = TextEditingController();

  late String _tipo;
  late bool _usarSsl;
  bool _salvando = false;
  bool _testando = false;
  String? _erro;
  ResultadoDoTeste? _resultado;

  @override
  void initState() {
    super.initState();
    final c = widget.conexao;
    _host = TextEditingController(text: c.host);
    _porta = TextEditingController(text: c.porta?.toString() ?? '');
    _banco = TextEditingController(text: c.banco);
    _schema = TextEditingController(text: c.schema);
    _usuario = TextEditingController(text: c.usuario);
    _tipo = c.tipo;
    _usarSsl = c.usarSsl;
  }

  @override
  void dispose() {
    for (final c in [_host, _porta, _banco, _schema, _usuario, _senha]) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bancosAsync = ref.watch(bancosSuportadosProvider);
    final jaConfigurada = widget.conexao.configurada;

    return AppCard(
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    jaConfigurada ? 'Conexão' : 'Conectar banco de dados',
                    style: context.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: context.textPrimaryColor,
                    ),
                  ),
                ),
                if (jaConfigurada) _selo(),
              ],
            ),
            const SizedBox(height: AppSpacing.xl),

            _rotulo('Qual banco a sua empresa usa'),
            bancosAsync.when(
              loading: () => const AppSkeleton.card(height: 56),
              error: (_, __) => Text(
                'Não foi possível carregar a lista de bancos.',
                style: context.textTheme.bodySmall
                    ?.copyWith(color: AppColors.error),
              ),
              data: (bancos) => DropdownButtonFormField<String>(
                initialValue: bancos.any((b) => b.valor == _tipo) ? _tipo : null,
                isExpanded: true,
                decoration: const InputDecoration(border: OutlineInputBorder()),
                hint: const Text('Escolha'),
                items: [
                  for (final b in bancos)
                    DropdownMenuItem(value: b.valor, child: Text(b.rotulo)),
                ],
                onChanged: (v) => setState(() => _tipo = v ?? _tipo),
                validator: (v) => v == null ? 'Escolha o banco.' : null,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 3,
                  child: CustomTextField(
                    controller: _host,
                    label: 'Endereço do servidor',
                    hint: 'erp.suaempresa.com.br',
                    validator: (v) => (v == null || v.trim().isEmpty)
                        ? 'Informe o endereço.'
                        : null,
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: CustomTextField(
                    controller: _porta,
                    label: 'Porta',
                    hint: _portaPadrao(),
                    keyboardType: TextInputType.number,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),

            CustomTextField(
              controller: _banco,
              label: _tipo == 'oracle'
                  ? 'Nome do serviço (service name)'
                  : 'Nome do banco de dados',
              validator: (v) => (v == null || v.trim().isEmpty)
                  ? 'Informe o banco.'
                  : null,
            ),
            const SizedBox(height: AppSpacing.lg),

            CustomTextField(
              controller: _schema,
              label: 'Schema (opcional)',
              hint: 'Deixe em branco para usar o padrão',
            ),
            const SizedBox(height: AppSpacing.lg),

            CustomTextField(
              controller: _usuario,
              label: 'Usuário de leitura',
              hint: 'integration_readonly',
              validator: (v) => (v == null || v.trim().isEmpty)
                  ? 'Informe o usuário.'
                  : null,
            ),
            const SizedBox(height: AppSpacing.lg),

            CustomTextField(
              controller: _senha,
              label: 'Senha',
              obscureText: true,
              hint: widget.conexao.temSenha
                  ? 'Já cadastrada — preencha só para trocar'
                  : null,
              validator: (v) {
                // Na criação a senha é obrigatória; na edição, em branco
                // significa "mantenha a que está guardada".
                if (!widget.conexao.temSenha && (v == null || v.isEmpty)) {
                  return 'Informe a senha do usuário de leitura.';
                }
                return null;
              },
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              'A senha é guardada cifrada e nunca é exibida de volta.',
              style: context.textTheme.bodySmall
                  ?.copyWith(color: context.textMutedColor),
            ),
            const SizedBox(height: AppSpacing.lg),

            CheckboxListTile(
              value: _usarSsl,
              onChanged: (v) => setState(() => _usarSsl = v ?? false),
              controlAffinity: ListTileControlAffinity.leading,
              contentPadding: EdgeInsets.zero,
              title: Text('Conexão segura (SSL)', style: context.textTheme.bodyMedium),
            ),

            if (_erro != null) ...[
              const SizedBox(height: AppSpacing.md),
              Text(
                _erro!,
                style: context.textTheme.bodySmall
                    ?.copyWith(color: AppColors.error),
              ),
            ],
            if (_resultado != null) ...[
              const SizedBox(height: AppSpacing.lg),
              _AvisoDoTeste(resultado: _resultado!),
            ],

            const SizedBox(height: AppSpacing.xl),
            Row(
              children: [
                Expanded(
                  child: AppButton(
                    text: jaConfigurada ? 'Salvar alterações' : 'Salvar conexão',
                    icon: Icons.save_outlined,
                    isLoading: _salvando,
                    onPressed: _salvando ? null : _salvar,
                  ),
                ),
                if (jaConfigurada) ...[
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: AppButton(
                      text: 'Testar leitura',
                      icon: Icons.wifi_tethering,
                      variant: AppButtonVariant.secondary,
                      isLoading: _testando,
                      onPressed: _testando ? null : _testar,
                    ),
                  ),
                ],
              ],
            ),

            if (jaConfigurada) ...[
              const SizedBox(height: AppSpacing.xxl),
              const Divider(),
              const SizedBox(height: AppSpacing.lg),
              _Descoberta(habilitada: widget.conexao.conectando),
            ],
          ],
        ),
      ),
    );
  }

  Widget _selo() {
    final c = widget.conexao;
    if (c.conectando) {
      return const AppBadge(label: 'Conectando', variant: AppBadgeVariant.success);
    }
    if (c.comFalha) {
      return const AppBadge(label: 'Com falha', variant: AppBadgeVariant.error);
    }
    return const AppBadge(label: 'Nunca testada', variant: AppBadgeVariant.neutral);
  }

  Widget _rotulo(String texto) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: Text(
        texto,
        style: context.textTheme.bodySmall?.copyWith(
          fontWeight: FontWeight.w600,
          color: context.textSecondaryColor,
        ),
      ),
    );
  }

  String _portaPadrao() => switch (_tipo) {
        'mysql' || 'mariadb' => '3306',
        'oracle' => '1521',
        _ => '5432',
      };

  Future<void> _salvar() async {
    if (!_formKey.currentState!.validate()) return;

    final messenger = ScaffoldMessenger.of(context);
    setState(() {
      _salvando = true;
      _erro = null;
      _resultado = null;
    });

    try {
      await ref.read(integrationsRepositoryProvider).salvarConexao(
            tipo: _tipo,
            host: _host.text.trim(),
            porta: int.tryParse(_porta.text.trim()),
            banco: _banco.text.trim(),
            schema: _schema.text.trim(),
            usuario: _usuario.text.trim(),
            senha: _senha.text,
            usarSsl: _usarSsl,
          );
      _senha.clear();
      ref.invalidate(conexaoProvider);
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Conexão salva.'),
          backgroundColor: AppColors.success,
        ),
      );
    } catch (erro) {
      setState(() => _erro = erro.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _salvando = false);
    }
  }

  Future<void> _testar() async {
    setState(() {
      _testando = true;
      _erro = null;
      _resultado = null;
    });

    final resultado =
        await ref.read(integrationsRepositoryProvider).testarConexao();

    if (!mounted) return;
    setState(() {
      _resultado = resultado;
      _testando = false;
    });
    ref.invalidate(conexaoProvider);
    if (resultado.ok) ref.invalidate(tabelasProvider);
  }
}

class _AvisoDoTeste extends StatelessWidget {
  final ResultadoDoTeste resultado;

  const _AvisoDoTeste({required this.resultado});

  @override
  Widget build(BuildContext context) {
    final cor = resultado.ok ? AppColors.success : AppColors.error;

    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: cor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: cor.withValues(alpha: 0.3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            resultado.ok ? Icons.check_circle_outline : Icons.error_outline,
            size: 18,
            color: cor,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              resultado.ok
                  ? '${resultado.mensagem} '
                      '${resultado.tabelasEncontradas} tabela(s) encontrada(s).'
                  : resultado.mensagem,
              style: context.textTheme.bodySmall?.copyWith(
                color: context.textPrimaryColor,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// As tabelas que o banco reportou.
///
/// A P4 (seção 14) pede que o sistema sugira, mas nunca assuma: aqui só se
/// mostra o que veio do banco. Quem diz o que cada tabela significa é o
/// administrador, no mapeamento — que é a próxima etapa.
class _Descoberta extends ConsumerWidget {
  final bool habilitada;

  const _Descoberta({required this.habilitada});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (!habilitada) {
      return const AppEmptyState(
        icon: Icons.table_chart_outlined,
        title: 'Teste a leitura primeiro',
        description:
            'Assim que a conexão for confirmada, as tabelas do seu banco aparecem aqui.',
      );
    }

    final tabelasAsync = ref.watch(tabelasProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Tabelas encontradas',
          style: context.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w700,
            color: context.textPrimaryColor,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Na próxima etapa você indica qual delas contém os colaboradores, '
          'os setores e os cargos.',
          style: context.textTheme.bodySmall
              ?.copyWith(color: context.textSecondaryColor),
        ),
        const SizedBox(height: AppSpacing.lg),
        tabelasAsync.whenAnimado(
          context,
          loading: () => const AppSkeleton.card(height: 120),
          error: (erro, _) => AppErrorState(
            message: erro.toString().replaceFirst('Exception: ', ''),
            onRetry: () => ref.invalidate(tabelasProvider),
          ),
          data: (tabelas) {
            if (tabelas.isEmpty) {
              return const AppEmptyState(
                icon: Icons.table_chart_outlined,
                title: 'Nenhuma tabela visível',
                description:
                    'O usuário conectou, mas não enxerga tabela nenhuma. Confira se ele tem permissão de leitura no schema.',
              );
            }
            return Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                for (final (i, t) in tabelas.indexed)
                  AppFadeIn(
                    delay: AppFadeIn.escalonar(i),
                    child: _ChipDeTabela(tabela: t),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _ChipDeTabela extends ConsumerWidget {
  final TabelaExterna tabela;

  const _ChipDeTabela({required this.tabela});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Semantics(
      button: true,
      label: 'Ver colunas da tabela ${tabela.nome}',
      child: ActionChip(
        avatar: const Icon(Icons.table_rows_outlined, size: 16),
        label: Text(tabela.nome),
        onPressed: () => showDialog<void>(
          context: context,
          builder: (_) => _ColunasDialog(tabela: tabela),
        ),
      ),
    );
  }
}

class _ColunasDialog extends ConsumerWidget {
  final TabelaExterna tabela;

  const _ColunasDialog({required this.tabela});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colunasAsync = ref.watch(colunasProvider(tabela.nomeCompleto));

    return AlertDialog(
      title: Text(tabela.nome),
      content: SizedBox(
        width: 460,
        height: 380,
        child: colunasAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (erro, _) => AppErrorState(
            message: erro.toString().replaceFirst('Exception: ', ''),
            onRetry: () =>
                ref.invalidate(colunasProvider(tabela.nomeCompleto)),
          ),
          data: (colunas) => ListView.separated(
            itemCount: colunas.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (_, i) {
              final c = colunas[i];
              return ListTile(
                dense: true,
                leading: Icon(
                  c.eChave ? Icons.key : Icons.abc,
                  size: 18,
                  color: c.eChave
                      ? AppColors.warning
                      : context.textMutedColor,
                ),
                title: Text(c.nome, style: context.textTheme.bodyMedium),
                subtitle: Text(
                  c.aceitaNulo ? '${c.tipo} · pode ficar vazio' : c.tipo,
                  style: context.textTheme.bodySmall
                      ?.copyWith(color: context.textSecondaryColor),
                ),
              );
            },
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Fechar'),
        ),
      ],
    );
  }
}
