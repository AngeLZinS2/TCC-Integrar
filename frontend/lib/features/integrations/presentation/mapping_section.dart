import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_motion.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../shared/models/integration_model.dart';
import '../providers/integrations_provider.dart';

/// Apontar o que é o quê no banco do cliente.
///
/// Para cada entidade — funcionários, setores, cargos — o administrador
/// escolhe UMA tabela e, dentro dela, qual coluna corresponde a cada campo
/// que o sistema usa. Tudo em caixas de seleção alimentadas pelo próprio
/// banco: ele nunca digita nome de tabela nem de coluna, e nunca escreve
/// SQL.
///
/// Obrigatórios e opcionais ficam separados de propósito (seção 15 da P4):
/// sem identificador não dá para reconhecer a mesma pessoa entre duas
/// sincronizações, e sem nome não dá para criar ninguém — o resto é
/// enriquecimento, e misturar os dois grupos esconderia isso.
class MappingSection extends ConsumerWidget {
  const MappingSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final camposAsync = ref.watch(camposDisponiveisProvider);
    final mapeamentosAsync = ref.watch(mapeamentosProvider);
    final tabelasAsync = ref.watch(tabelasProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'O que é o quê no seu banco',
          style: context.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w700,
            color: context.textPrimaryColor,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Escolha a tabela de cada tipo de informação e diga qual coluna '
          'corresponde a cada campo. O sistema não adivinha nada: quem sabe '
          'o significado dos dados é você.',
          style: context.textTheme.bodySmall?.copyWith(
            color: context.textSecondaryColor,
            height: 1.5,
          ),
        ),
        const SizedBox(height: AppSpacing.xl),

        if (camposAsync.isLoading ||
            mapeamentosAsync.isLoading ||
            tabelasAsync.isLoading)
          const AppSkeleton.card(height: 200)
        else if (tabelasAsync.hasError)
          AppErrorState(
            message: tabelasAsync.error
                .toString()
                .replaceFirst('Exception: ', ''),
            onRetry: () => ref.invalidate(tabelasProvider),
          )
        else if (camposAsync.hasError || mapeamentosAsync.hasError)
          AppErrorState(
            message: 'Não foi possível carregar o mapeamento.',
            onRetry: () {
              ref.invalidate(camposDisponiveisProvider);
              ref.invalidate(mapeamentosProvider);
            },
          )
        else
          _Lista(
            entidades: camposAsync.value ?? const [],
            mapeamentos: mapeamentosAsync.value ?? const [],
            tabelas: tabelasAsync.value ?? const [],
          ),
      ],
    );
  }
}

class _Lista extends StatelessWidget {
  final List<EntidadeMapeavel> entidades;
  final List<Mapeamento> mapeamentos;
  final List<TabelaExterna> tabelas;

  const _Lista({
    required this.entidades,
    required this.mapeamentos,
    required this.tabelas,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final (i, entidade) in entidades.indexed)
          AppFadeIn(
            delay: AppFadeIn.escalonar(i),
            child: Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.lg),
              child: _CartaoDaEntidade(
                entidade: entidade,
                mapeamento: mapeamentos.firstWhere(
                  (m) => m.entidade == entidade.chave,
                  orElse: () => Mapeamento(
                    entidade: entidade.chave,
                    rotulo: entidade.rotulo,
                    tabela: '',
                    campos: const {},
                    configurado: false,
                  ),
                ),
                tabelas: tabelas,
              ),
            ),
          ),
      ],
    );
  }
}

class _CartaoDaEntidade extends ConsumerStatefulWidget {
  final EntidadeMapeavel entidade;
  final Mapeamento mapeamento;
  final List<TabelaExterna> tabelas;

  const _CartaoDaEntidade({
    required this.entidade,
    required this.mapeamento,
    required this.tabelas,
  });

  @override
  ConsumerState<_CartaoDaEntidade> createState() => _CartaoDaEntidadeState();
}

class _CartaoDaEntidadeState extends ConsumerState<_CartaoDaEntidade> {
  String? _tabela;
  late Map<String, String> _campos;
  bool _aberto = false;
  bool _salvando = false;
  String? _erro;

  @override
  void initState() {
    super.initState();
    _tabela = widget.mapeamento.tabela.isEmpty ? null : widget.mapeamento.tabela;
    _campos = Map.of(widget.mapeamento.campos);
    // Nasce aberto quando ainda não foi configurado: é o passo pendente.
    _aberto = !widget.mapeamento.configurado;
  }

  @override
  Widget build(BuildContext context) {
    final e = widget.entidade;

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: () => setState(() => _aberto = !_aberto),
            child: Row(
              children: [
                Icon(_iconeDe(e.chave), size: 20, color: AppColors.primary),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        e.rotulo,
                        style: context.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: context.textPrimaryColor,
                        ),
                      ),
                      if (widget.mapeamento.configurado)
                        Text(
                          '${widget.mapeamento.tabela} · '
                          '${widget.mapeamento.campos.length} campo(s)',
                          style: context.textTheme.bodySmall
                              ?.copyWith(color: context.textSecondaryColor),
                        ),
                    ],
                  ),
                ),
                AppBadge(
                  label: widget.mapeamento.configurado
                      ? 'Configurado'
                      : 'Pendente',
                  variant: widget.mapeamento.configurado
                      ? AppBadgeVariant.success
                      : AppBadgeVariant.warning,
                ),
                const SizedBox(width: AppSpacing.sm),
                Icon(
                  _aberto ? Icons.expand_less : Icons.expand_more,
                  color: context.textSecondaryColor,
                ),
              ],
            ),
          ),

          if (_aberto) ...[
            const SizedBox(height: AppSpacing.xl),
            _seletorDeTabela(),
            if (_tabela != null) ...[
              const SizedBox(height: AppSpacing.xl),
              _seletoresDeCampo(),
            ],
            if (_erro != null) ...[
              const SizedBox(height: AppSpacing.md),
              Text(
                _erro!,
                style: context.textTheme.bodySmall
                    ?.copyWith(color: AppColors.error),
              ),
            ],
            const SizedBox(height: AppSpacing.xl),
            AppButton(
              text: 'Salvar ${e.rotulo.toLowerCase()}',
              icon: Icons.check,
              isLoading: _salvando,
              onPressed: _tabela == null || _salvando ? null : _salvar,
            ),
          ],
        ],
      ),
    );
  }

  // ── Tabela ─────────────────────────────────────────────────────────

  Widget _seletorDeTabela() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _rotulo(
          'Qual tabela contém ${widget.entidade.rotulo.toLowerCase()}?',
          obrigatorio: true,
        ),
        DropdownButtonFormField<String>(
          initialValue: _tabelaValida(),
          isExpanded: true,
          decoration: const InputDecoration(border: OutlineInputBorder()),
          hint: const Text('Escolha a tabela'),
          items: [
            for (final t in widget.tabelas)
              DropdownMenuItem(
                value: t.nomeCompleto,
                child: Text(t.nome, overflow: TextOverflow.ellipsis),
              ),
          ],
          onChanged: (v) => setState(() {
            // Trocar de tabela zera os campos: as colunas da tabela antiga
            // não existem na nova, e manter a escolha faria o servidor
            // recusar com um erro que o usuário não entenderia.
            if (v != _tabela) _campos = {};
            _tabela = v;
          }),
        ),
      ],
    );
  }

  /// A tabela guardada só vira valor do select se ainda existir na lista —
  /// senão o Dropdown quebra com "value not in items".
  String? _tabelaValida() {
    if (_tabela == null) return null;
    return widget.tabelas.any((t) => t.nomeCompleto == _tabela) ? _tabela : null;
  }

  // ── Campos ─────────────────────────────────────────────────────────

  Widget _seletoresDeCampo() {
    final colunasAsync = ref.watch(colunasProvider(_tabela!));

    return colunasAsync.when(
      loading: () => const AppSkeleton.card(height: 120),
      error: (erro, _) => AppErrorState(
        message: erro.toString().replaceFirst('Exception: ', ''),
        onRetry: () => ref.invalidate(colunasProvider(_tabela!)),
      ),
      data: (colunas) {
        final e = widget.entidade;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _subtitulo('Obrigatórios'),
            for (final campo in e.obrigatorios)
              _seletorDeColuna(campo, colunas),
            if (e.opcionais.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.lg),
              _subtitulo('Opcionais'),
              Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.md),
                child: Text(
                  'Só o que você apontar aqui é trazido para o sistema. '
                  'Deixe em branco o que não for usar.',
                  style: context.textTheme.bodySmall
                      ?.copyWith(color: context.textMutedColor),
                ),
              ),
              for (final campo in e.opcionais) _seletorDeColuna(campo, colunas),
            ],
          ],
        );
      },
    );
  }

  Widget _seletorDeColuna(CampoInterno campo, List<ColunaExterna> colunas) {
    final atual = _campos[campo.chave];
    final valido = colunas.any((c) => c.nome == atual) ? atual : null;

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _rotulo(campo.rotulo, obrigatorio: campo.obrigatorio),
          DropdownButtonFormField<String>(
            initialValue: valido,
            isExpanded: true,
            decoration: InputDecoration(
              border: const OutlineInputBorder(),
              helperText: campo.ajuda,
              helperMaxLines: 3,
            ),
            hint: Text(
              campo.obrigatorio ? 'Escolha a coluna' : 'Não trazer este dado',
            ),
            items: [
              if (!campo.obrigatorio)
                const DropdownMenuItem(
                  value: '',
                  child: Text('— não trazer —'),
                ),
              for (final c in colunas)
                DropdownMenuItem(
                  value: c.nome,
                  child: Text(
                    '${c.nome}  ·  ${c.tipo}',
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
            onChanged: (v) => setState(() {
              if (v == null || v.isEmpty) {
                _campos.remove(campo.chave);
              } else {
                _campos[campo.chave] = v;
              }
            }),
          ),
        ],
      ),
    );
  }

  // ── Auxiliares ─────────────────────────────────────────────────────

  Widget _rotulo(String texto, {bool obrigatorio = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: RichText(
        text: TextSpan(
          text: texto,
          style: context.textTheme.bodySmall?.copyWith(
            fontWeight: FontWeight.w600,
            color: context.textSecondaryColor,
          ),
          children: [
            if (obrigatorio)
              const TextSpan(
                text: ' *',
                style: TextStyle(color: AppColors.error),
              ),
          ],
        ),
      ),
    );
  }

  Widget _subtitulo(String texto) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Text(
        texto.toUpperCase(),
        style: context.textTheme.bodySmall?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: 0.6,
          color: context.textMutedColor,
        ),
      ),
    );
  }

  IconData _iconeDe(String entidade) => switch (entidade) {
        'employee' => Icons.groups_outlined,
        'sector' => Icons.corporate_fare_outlined,
        _ => Icons.work_outline_rounded,
      };

  Future<void> _salvar() async {
    final messenger = ScaffoldMessenger.of(context);
    setState(() {
      _salvando = true;
      _erro = null;
    });

    try {
      await ref.read(integrationsRepositoryProvider).salvarMapeamento(
            entidade: widget.entidade.chave,
            tabela: _tabela!,
            campos: _campos,
          );
      ref.invalidate(mapeamentosProvider);
      if (mounted) setState(() => _aberto = false);
      messenger.showSnackBar(
        SnackBar(
          content: Text('${widget.entidade.rotulo} mapeados.'),
          backgroundColor: AppColors.success,
        ),
      );
    } catch (erro) {
      // A mensagem vem do servidor: ele confere contra o banco de verdade
      // e diz exatamente qual campo faltou ou qual coluna não existe.
      setState(() => _erro = erro.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _salvando = false);
    }
  }
}
