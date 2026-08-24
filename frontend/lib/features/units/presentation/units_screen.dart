import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../../shared/models/unit_model.dart';
import '../providers/units_provider.dart';

/// Unidades (filiais) da empresa.
///
/// `Company` é o tenant; `Unit` é localização dentro dele. A tela deixa
/// isso explícito no subtítulo porque confundir os dois é o erro caro.
class UnitsScreen extends ConsumerWidget {
  const UnitsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unidadesAsync = ref.watch(unitsListProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(unitsListProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Unidades',
                subtitle:
                    'Filiais e locais de trabalho da empresa. Servem para segmentar comunicados, eventos, documentos e treinamentos.',
                trailing: AppButton(
                  text: 'Nova Unidade',
                  icon: Icons.add,
                  size: AppButtonSize.sm,
                  onPressed: () => _abrirFormulario(context, ref),
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              unidadesAsync.when(
                loading: () => GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate:
                      const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 360,
                    mainAxisExtent: 160,
                    crossAxisSpacing: AppSpacing.lg,
                    mainAxisSpacing: AppSpacing.lg,
                  ),
                  itemCount: 3,
                  itemBuilder: (_, __) => const AppSkeleton.card(height: 160),
                ),
                error: (_, __) => AppErrorState(
                  message: 'Não foi possível carregar as unidades.',
                  onRetry: () => ref.invalidate(unitsListProvider),
                ),
                data: (resposta) {
                  final unidades = resposta.results;
                  if (unidades.isEmpty) {
                    return AppEmptyState(
                      icon: Icons.apartment_outlined,
                      title: 'Nenhuma unidade cadastrada',
                      description:
                          'Cadastre as filiais para poder direcionar conteúdo a locais específicos.',
                      actionText: 'Nova Unidade',
                      onAction: () => _abrirFormulario(context, ref),
                    );
                  }
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate:
                        const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 360,
                      mainAxisExtent: 160,
                      crossAxisSpacing: AppSpacing.lg,
                      mainAxisSpacing: AppSpacing.lg,
                    ),
                    itemCount: unidades.length,
                    itemBuilder: (_, i) => _UnitCard(
                      unit: unidades[i],
                      onDelete: () => _confirmarExclusao(
                        context,
                        ref,
                        unidades[i],
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _abrirFormulario(BuildContext context, WidgetRef ref) {
    showDialog<void>(
      context: context,
      builder: (_) => const _UnitFormDialog(),
    ).then((_) => ref.invalidate(unitsListProvider));
  }

  /// Excluir unidade é destrutivo e afeta todo mundo lotado nela — a
  /// confirmação diz exatamente isso, em vez de um "tem certeza?" genérico.
  Future<void> _confirmarExclusao(
    BuildContext context,
    WidgetRef ref,
    UnitModel unidade,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    final confirmou = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Excluir unidade?'),
        content: Text(
          unidade.employeeCount > 0
              ? '${unidade.name} tem ${unidade.employeeCount} colaborador(es) lotado(s). '
                  'Eles ficarão sem unidade definida e voltarão a receber conteúdo de todas as unidades.'
              : '${unidade.name} será removida permanentemente.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Excluir'),
          ),
        ],
      ),
    );

    if (confirmou != true) return;

    try {
      await ref.read(unitsRepositoryProvider).deleteUnit(unidade.id);
      ref.invalidate(unitsListProvider);
      messenger.showSnackBar(
        SnackBar(
          content: Text('${unidade.name} foi excluída.'),
          backgroundColor: AppColors.success,
        ),
      );
    } catch (_) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Não foi possível excluir a unidade.'),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }
}

class _UnitCard extends StatelessWidget {
  final UnitModel unit;
  final VoidCallback onDelete;

  const _UnitCard({required this.unit, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label:
          '${unit.name}, ${unit.employeeCount} colaboradores, ${unit.isActive ? "ativa" : "inativa"}',
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    unit.name,
                    style: context.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: context.textPrimaryColor,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                AppBadge(
                  label: unit.isActive ? 'Ativa' : 'Inativa',
                  variant: unit.isActive
                      ? AppBadgeVariant.success
                      : AppBadgeVariant.neutral,
                ),
              ],
            ),
            if (unit.code.isNotEmpty) ...[
              const SizedBox(height: 2),
              Text(
                'Código ${unit.code}',
                style: context.textTheme.bodySmall?.copyWith(
                  color: context.textMutedColor,
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.md),
            if (unit.location.isNotEmpty)
              _info(context, Icons.place_outlined, unit.location),
            if (unit.managerName != null)
              _info(context, Icons.badge_outlined, unit.managerName!),
            _info(
              context,
              Icons.people_outline,
              '${unit.employeeCount} colaborador(es)',
            ),
            const Spacer(),
            Align(
              alignment: Alignment.centerRight,
              child: Semantics(
                button: true,
                label: 'Excluir unidade ${unit.name}',
                child: IconButton(
                  icon: const Icon(Icons.delete_outline, size: 18),
                  color: AppColors.error,
                  onPressed: onDelete,
                  tooltip: 'Excluir',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _info(BuildContext context, IconData icone, String texto) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Icon(icone, size: 14, color: context.textSecondaryColor),
          const SizedBox(width: AppSpacing.xs),
          Expanded(
            child: Text(
              texto,
              style: context.textTheme.bodySmall?.copyWith(
                color: context.textSecondaryColor,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _UnitFormDialog extends ConsumerStatefulWidget {
  const _UnitFormDialog();

  @override
  ConsumerState<_UnitFormDialog> createState() => _UnitFormDialogState();
}

class _UnitFormDialogState extends ConsumerState<_UnitFormDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nome = TextEditingController();
  final _codigo = TextEditingController();
  final _endereco = TextEditingController();
  final _cidade = TextEditingController();
  final _uf = TextEditingController();
  bool _salvando = false;
  String? _erro;

  @override
  void dispose() {
    _nome.dispose();
    _codigo.dispose();
    _endereco.dispose();
    _cidade.dispose();
    _uf.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Nova Unidade'),
      content: SizedBox(
        width: 420,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CustomTextField(
                  controller: _nome,
                  label: 'Nome',
                  hint: 'Unidade Centro',
                  validator: (v) => (v == null || v.trim().isEmpty)
                      ? 'Informe o nome da unidade.'
                      : null,
                ),
                const SizedBox(height: AppSpacing.md),
                CustomTextField(
                  controller: _codigo,
                  label: 'Código (opcional)',
                  hint: 'CTR',
                ),
                const SizedBox(height: AppSpacing.md),
                CustomTextField(
                  controller: _endereco,
                  label: 'Endereço (opcional)',
                ),
                const SizedBox(height: AppSpacing.md),
                Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: CustomTextField(
                        controller: _cidade,
                        label: 'Cidade',
                      ),
                    ),
                    const SizedBox(width: AppSpacing.md),
                    Expanded(
                      child: CustomTextField(
                        controller: _uf,
                        label: 'UF',
                        hint: 'SP',
                      ),
                    ),
                  ],
                ),
                if (_erro != null) ...[
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    _erro!,
                    style: context.textTheme.bodySmall
                        ?.copyWith(color: AppColors.error),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _salvando ? null : () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        AppButton(
          text: 'Salvar',
          isLoading: _salvando,
          size: AppButtonSize.sm,
          onPressed: _salvando ? null : _salvar,
        ),
      ],
    );
  }

  Future<void> _salvar() async {
    if (!_formKey.currentState!.validate()) return;

    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    setState(() {
      _salvando = true;
      _erro = null;
    });

    try {
      await ref.read(unitsRepositoryProvider).createUnit(
            name: _nome.text.trim(),
            code: _codigo.text.trim(),
            address: _endereco.text.trim(),
            city: _cidade.text.trim(),
            state: _uf.text.trim(),
          );
      navigator.pop();
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Unidade criada.'),
          backgroundColor: AppColors.success,
        ),
      );
    } catch (erro) {
      // O backend explica o motivo (nome ou código já usado); mostrar isso
      // no formulário é o que permite corrigir.
      setState(() => _erro = erro.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _salvando = false);
    }
  }
}
