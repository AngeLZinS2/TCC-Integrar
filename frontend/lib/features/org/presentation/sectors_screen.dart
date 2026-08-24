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
import 'widgets/sector_form_sheet.dart';

class SectorsScreen extends ConsumerStatefulWidget {
  const SectorsScreen({super.key});

  @override
  ConsumerState<SectorsScreen> createState() => _SectorsScreenState();
}

class _SectorsScreenState extends ConsumerState<SectorsScreen> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _openForm({SectorModel? sector}) async {
    final salvou = await showSectorFormSheet(context, ref, sector: sector);
    if (salvou == true && mounted) {
      ref.read(sectorsProvider.notifier).load();
      ref.invalidate(managerOptionsProvider);
      _toast(sector == null ? 'Setor criado.' : 'Setor atualizado.');
    }
  }

  Future<void> _confirmDelete(SectorModel sector) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: context.surfaceColor,
        title: Text('Excluir setor?', style: TextStyle(color: context.textPrimaryColor)),
        content: Text(
          'O setor "${sector.name}" será removido. Esta ação não pode ser desfeita.',
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
      await ref.read(orgRepositoryProvider).deleteSector(sector.id);
      ref.read(sectorsProvider.notifier).load();
      _toast('Setor excluído.');
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
    final state = ref.watch(sectorsProvider);
    final user = ref.watch(authNotifierProvider).user;
    final podeGerenciar = user?.canManageOrg ?? false;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () => ref.read(sectorsProvider.notifier).load(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Setores',
                subtitle: 'Estrutura organizacional da sua empresa.',
                trailing: podeGerenciar
                    ? Semantics(
                        button: true,
                        label: 'Criar novo setor',
                        child: AppButton(
                          text: 'Novo Setor',
                          icon: Icons.add_rounded,
                          size: AppButtonSize.sm,
                          onPressed: () => _openForm(),
                        ),
                      )
                    : null,
              ),
              const SizedBox(height: AppSpacing.md),
              Semantics(
                textField: true,
                label: 'Buscar setor por nome',
                child: TextField(
                  controller: _searchController,
                  onSubmitted: (v) => ref.read(sectorsProvider.notifier).load(search: v),
                  decoration: InputDecoration(
                    hintText: 'Buscar setor...',
                    prefixIcon: const Icon(Icons.search_rounded, size: 20),
                    suffixIcon: _searchController.text.isEmpty
                        ? null
                        : IconButton(
                            tooltip: 'Limpar busca',
                            icon: const Icon(Icons.close_rounded, size: 18),
                            onPressed: () {
                              _searchController.clear();
                              ref.read(sectorsProvider.notifier).load(search: '');
                              setState(() {});
                            },
                          ),
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
                  onChanged: (_) => setState(() {}),
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              state.when(
                loading: () => Column(
                  children: List.generate(
                    4,
                    (_) => const Padding(
                      padding: EdgeInsets.only(bottom: AppSpacing.md),
                      child: AppSkeleton.card(height: 88),
                    ),
                  ),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar os setores.',
                  onRetry: () => ref.read(sectorsProvider.notifier).load(),
                ),
                data: (paged) {
                  if (paged.items.isEmpty) {
                    return AppEmptyState(
                      icon: Icons.corporate_fare_rounded,
                      title: paged.search.isEmpty
                          ? 'Nenhum setor cadastrado'
                          : 'Nenhum setor encontrado',
                      description: paged.search.isEmpty
                          ? 'Comece criando os setores da sua empresa — eles organizam colaboradores, treinamentos e materiais.'
                          : 'Tente outro termo de busca.',
                      actionText: podeGerenciar && paged.search.isEmpty ? 'Criar primeiro setor' : null,
                      onAction: podeGerenciar && paged.search.isEmpty ? () => _openForm() : null,
                    );
                  }
                  return Column(
                    children: [
                      ...paged.items.map(
                        (s) => Padding(
                          padding: const EdgeInsets.only(bottom: AppSpacing.md),
                          child: _SectorCard(
                            sector: s,
                            canManage: podeGerenciar,
                            onEdit: () => _openForm(sector: s),
                            onDelete: () => _confirmDelete(s),
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
                            onPressed: () => ref.read(sectorsProvider.notifier).loadMore(),
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

class _SectorCard extends StatelessWidget {
  final SectorModel sector;
  final bool canManage;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  const _SectorCard({
    required this.sector,
    required this.canManage,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '${sector.name}, ${sector.collaboratorsCount} colaboradores',
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
                          sector.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: context.textPrimaryColor,
                          ),
                        ),
                      ),
                      if (!sector.isActive) ...[
                        const SizedBox(width: AppSpacing.sm),
                        const AppBadge(label: 'Inativo', variant: AppBadgeVariant.neutral),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${sector.collaboratorsCount} '
                    '${sector.collaboratorsCount == 1 ? "colaborador" : "colaboradores"}'
                    ' · ${sector.positionsCount} '
                    '${sector.positionsCount == 1 ? "cargo" : "cargos"}',
                    style: TextStyle(fontSize: 12.5, color: context.textSecondaryColor),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Icon(
                        Icons.person_outline_rounded,
                        size: 14,
                        color: context.textMutedColor,
                      ),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          sector.managerName == null
                              ? 'Sem gestor definido'
                              : 'Gestor: ${sector.managerName}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 12,
                            color: sector.managerName == null
                                ? context.textMutedColor
                                : context.textSecondaryColor,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            if (canManage) ...[
              IconButton(
                tooltip: 'Editar setor',
                icon: Icon(Icons.edit_outlined, size: 19, color: context.textMutedColor),
                onPressed: onEdit,
              ),
              IconButton(
                tooltip: sector.hasCollaborators
                    ? 'Não é possível excluir: há colaboradores neste setor'
                    : 'Excluir setor',
                icon: Icon(
                  Icons.delete_outline_rounded,
                  size: 19,
                  color: sector.hasCollaborators
                      ? context.textMutedColor.withValues(alpha: 0.4)
                      : AppColors.error,
                ),
                onPressed: sector.hasCollaborators ? null : onDelete,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
