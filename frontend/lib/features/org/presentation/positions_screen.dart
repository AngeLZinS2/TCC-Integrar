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
import '../../auth/providers/auth_provider.dart';
import '../models/org_models.dart';
import '../providers/org_provider.dart';
import 'widgets/position_form_sheet.dart';

class PositionsScreen extends ConsumerStatefulWidget {
  const PositionsScreen({super.key});

  @override
  ConsumerState<PositionsScreen> createState() => _PositionsScreenState();
}

class _PositionsScreenState extends ConsumerState<PositionsScreen> {
  final _searchController = TextEditingController();
  int? _sectorFilter;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _openForm({PositionModel? position}) async {
    final salvou = await showPositionFormSheet(
      context,
      ref,
      position: position,
      initialSectorId: _sectorFilter,
    );
    if (salvou == true && mounted) {
      ref.read(positionsProvider.notifier).load();
      ref.read(sectorsProvider.notifier).load(); // contagem de cargos muda
      _toast(position == null ? 'Cargo criado.' : 'Cargo atualizado.');
    }
  }

  Future<void> _confirmDelete(PositionModel position) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: context.surfaceColor,
        title: Text('Excluir cargo?', style: TextStyle(color: context.textPrimaryColor)),
        content: Text(
          'O cargo "${position.name}" será removido. Esta ação não pode ser desfeita.',
          style: TextStyle(color: context.textSecondaryColor),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Excluir', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
    if (confirmado != true) return;

    try {
      await ref.read(orgRepositoryProvider).deletePosition(position.id);
      ref.read(positionsProvider.notifier).load();
      ref.read(sectorsProvider.notifier).load();
      _toast('Cargo excluído.');
    } catch (e) {
      _toast(e.toString().replaceAll('Exception: ', ''), isError: true);
    }
  }

  void _toast(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? AppColors.error : AppColors.success,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.md)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(positionsProvider);
    final sectorsAsync = ref.watch(sectorsProvider);
    final user = ref.watch(authNotifierProvider).user;
    final podeGerenciar = user?.canManageOrg ?? false;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () => ref.read(positionsProvider.notifier).load(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Cargos',
                subtitle: 'Funções existentes em cada setor da empresa.',
                trailing: podeGerenciar
                    ? Semantics(
                        button: true,
                        label: 'Criar novo cargo',
                        child: AppButton(
                          text: 'Novo Cargo',
                          icon: Icons.add_rounded,
                          size: AppButtonSize.sm,
                          onPressed: () => _openForm(),
                        ),
                      )
                    : null,
              ),
              const SizedBox(height: AppSpacing.md),
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth > 640;
                  final busca = Semantics(
                    textField: true,
                    label: 'Buscar cargo por nome',
                    child: TextField(
                      controller: _searchController,
                      onSubmitted: (v) =>
                          ref.read(positionsProvider.notifier).load(search: v),
                      decoration: InputDecoration(
                        hintText: 'Buscar cargo...',
                        prefixIcon: const Icon(Icons.search_rounded, size: 20),
                        filled: true,
                        fillColor: context.surfaceColor,
                        contentPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(AppRadius.md),
                          borderSide: BorderSide(color: context.borderColor),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(AppRadius.md),
                          borderSide: BorderSide(color: context.borderColor),
                        ),
                      ),
                    ),
                  );

                  final filtroSetor = Container(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                    decoration: BoxDecoration(
                      color: context.surfaceColor,
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      border: Border.all(color: context.borderColor),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<int?>(
                        value: _sectorFilter,
                        hint: const Text('Todos os setores'),
                        onChanged: (v) {
                          setState(() => _sectorFilter = v);
                          ref.read(positionsProvider.notifier).load(
                                sectorId: v,
                                clearSector: v == null,
                              );
                        },
                        items: [
                          const DropdownMenuItem<int?>(
                            value: null,
                            child: Text('Todos os setores'),
                          ),
                          ...?sectorsAsync.valueOrNull?.items.map(
                            (s) => DropdownMenuItem<int?>(value: s.id, child: Text(s.name)),
                          ),
                        ],
                      ),
                    ),
                  );

                  if (isWide) {
                    return Row(
                      children: [
                        Expanded(child: busca),
                        const SizedBox(width: AppSpacing.md),
                        filtroSetor,
                      ],
                    );
                  }
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [busca, const SizedBox(height: AppSpacing.sm), filtroSetor],
                  );
                },
              ),
              const SizedBox(height: AppSpacing.xl),
              state.when(
                loading: () => Column(
                  children: List.generate(
                    4,
                    (_) => const Padding(
                      padding: EdgeInsets.only(bottom: AppSpacing.md),
                      child: AppSkeleton.card(height: 76),
                    ),
                  ),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar os cargos.',
                  onRetry: () => ref.read(positionsProvider.notifier).load(),
                ),
                data: (paged) {
                  if (paged.items.isEmpty) {
                    return AppEmptyState(
                      icon: Icons.work_outline_rounded,
                      title: 'Nenhum cargo encontrado',
                      description: 'Cadastre os cargos de cada setor para organizar '
                          'as trilhas de treinamento por função.',
                      actionText: podeGerenciar ? 'Criar cargo' : null,
                      onAction: podeGerenciar ? () => _openForm() : null,
                    );
                  }
                  return Column(
                    children: [
                      ...paged.items.map(
                        (p) => Padding(
                          padding: const EdgeInsets.only(bottom: AppSpacing.md),
                          child: _PositionCard(
                            position: p,
                            canManage: podeGerenciar,
                            onEdit: () => _openForm(position: p),
                            onDelete: () => _confirmDelete(p),
                          ),
                        ),
                      ),
                      if (paged.hasMore)
                        Padding(
                          padding: const EdgeInsets.only(top: AppSpacing.sm),
                          child: AppButton(
                            text: 'Carregar mais',
                            icon: Icons.expand_more_rounded,
                            variant: AppButtonVariant.outline,
                            isLoading: paged.isLoadingMore,
                            onPressed: () => ref.read(positionsProvider.notifier).loadMore(),
                          ),
                        ),
                      Padding(
                        padding: const EdgeInsets.only(top: AppSpacing.md),
                        child: Text(
                          'Mostrando ${paged.items.length} de ${paged.count}',
                          style: TextStyle(fontSize: 12, color: context.textMutedColor),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PositionCard extends StatelessWidget {
  final PositionModel position;
  final bool canManage;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  const _PositionCard({
    required this.position,
    required this.canManage,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '${position.name}, setor ${position.sectorName ?? ""}, '
          '${position.collaboratorsCount} colaboradores',
      child: AppCard(
        onTap: canManage ? onEdit : null,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          position.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w700,
                            color: context.textPrimaryColor,
                          ),
                        ),
                      ),
                      if (!position.isActive) ...[
                        const SizedBox(width: AppSpacing.sm),
                        const AppBadge(label: 'Inativo', variant: AppBadgeVariant.neutral),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: AppSpacing.xs,
                    runSpacing: 4,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      if (position.sectorName != null)
                        AppBadge(
                          label: position.sectorName!,
                          variant: AppBadgeVariant.primary,
                        ),
                      Text(
                        '${position.collaboratorsCount} '
                        '${position.collaboratorsCount == 1 ? "colaborador" : "colaboradores"}',
                        style: TextStyle(fontSize: 12, color: context.textSecondaryColor),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            if (canManage) ...[
              IconButton(
                tooltip: 'Editar cargo',
                icon: Icon(Icons.edit_outlined, size: 19, color: context.textMutedColor),
                onPressed: onEdit,
              ),
              IconButton(
                tooltip: position.hasCollaborators
                    ? 'Não é possível excluir: há colaboradores neste cargo'
                    : 'Excluir cargo',
                icon: Icon(
                  Icons.delete_outline_rounded,
                  size: 19,
                  color: position.hasCollaborators
                      ? context.textMutedColor.withValues(alpha: 0.4)
                      : AppColors.error,
                ),
                onPressed: position.hasCollaborators ? null : onDelete,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
