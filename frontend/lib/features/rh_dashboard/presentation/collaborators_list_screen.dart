import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_avatar.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_progress.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../shared/services/csv_download/csv_download.dart';
import '../models/collaborator_row_model.dart';
import '../providers/dashboard_provider.dart';

enum _SortOption { nameAsc, overallDesc, overallAsc, lastLogin }

class CollaboratorsListScreen extends ConsumerStatefulWidget {
  const CollaboratorsListScreen({super.key});

  @override
  ConsumerState<CollaboratorsListScreen> createState() => _CollaboratorsListScreenState();
}

class _CollaboratorsListScreenState extends ConsumerState<CollaboratorsListScreen> {
  final _searchController = TextEditingController();
  String _search = '';
  _SortOption _sort = _SortOption.nameAsc;
  bool _isExporting = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _handleExport() async {
    setState(() => _isExporting = true);
    try {
      final bytes = await ref.read(dashboardRepositoryProvider).exportCollaboratorsCsv();
      saveCsv(bytes, 'colaboradores.csv');
    } catch (e) {
      if (mounted) {
        final message = e.toString().replaceAll('Exception: ', '');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.md)),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isExporting = false);
    }
  }

  List<CollaboratorRowModel> _applyFilters(List<CollaboratorRowModel> rows) {
    var filtered = rows;
    if (_search.isNotEmpty) {
      final query = _search.toLowerCase();
      filtered = filtered
          .where((r) => r.fullName.toLowerCase().contains(query) || r.email.toLowerCase().contains(query))
          .toList();
    }
    filtered = [...filtered];
    switch (_sort) {
      case _SortOption.nameAsc:
        filtered.sort((a, b) => a.fullName.compareTo(b.fullName));
      case _SortOption.overallDesc:
        filtered.sort((a, b) => b.overallPercent.compareTo(a.overallPercent));
      case _SortOption.overallAsc:
        filtered.sort((a, b) => a.overallPercent.compareTo(b.overallPercent));
      case _SortOption.lastLogin:
        filtered.sort((a, b) {
          if (a.lastLogin == null && b.lastLogin == null) return 0;
          if (a.lastLogin == null) return 1;
          if (b.lastLogin == null) return -1;
          return b.lastLogin!.compareTo(a.lastLogin!);
        });
    }
    return filtered;
  }

  @override
  Widget build(BuildContext context) {
    final collaboratorsAsync = ref.watch(collaboratorsListProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(collaboratorsListProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Colaboradores',
                subtitle: 'Progresso individual de treinamentos e checklist de integração.',
                trailing: Wrap(
                  spacing: AppSpacing.sm,
                  children: [
                    AppButton(
                      text: 'Baixar CSV',
                      icon: Icons.download_rounded,
                      variant: AppButtonVariant.outline,
                      size: AppButtonSize.sm,
                      isLoading: _isExporting,
                      onPressed: _handleExport,
                    ),
                    AppButton(
                      text: 'Novo Colaborador',
                      icon: Icons.person_add_alt_1_rounded,
                      size: AppButtonSize.sm,
                      onPressed: () => context.push('/rh/collaborators/new'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth > 640;
                  final searchField = TextField(
                    controller: _searchController,
                    onChanged: (value) => setState(() => _search = value),
                    decoration: InputDecoration(
                      hintText: 'Buscar por nome ou e-mail...',
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
                  );
                  final sortDropdown = Container(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                    decoration: BoxDecoration(
                      color: context.surfaceColor,
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      border: Border.all(color: context.borderColor),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<_SortOption>(
                        value: _sort,
                        onChanged: (value) => setState(() => _sort = value ?? _SortOption.nameAsc),
                        items: const [
                          DropdownMenuItem(value: _SortOption.nameAsc, child: Text('Nome (A-Z)')),
                          DropdownMenuItem(value: _SortOption.overallDesc, child: Text('Maior progresso')),
                          DropdownMenuItem(value: _SortOption.overallAsc, child: Text('Menor progresso')),
                          DropdownMenuItem(value: _SortOption.lastLogin, child: Text('Último acesso')),
                        ],
                      ),
                    ),
                  );

                  if (isWide) {
                    return Row(
                      children: [
                        Expanded(child: searchField),
                        const SizedBox(width: AppSpacing.md),
                        sortDropdown,
                      ],
                    );
                  }
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      searchField,
                      const SizedBox(height: AppSpacing.sm),
                      sortDropdown,
                    ],
                  );
                },
              ),
              const SizedBox(height: AppSpacing.xl),
              collaboratorsAsync.when(
                loading: () => Column(
                  children: List.generate(
                    4,
                    (_) => const Padding(
                      padding: EdgeInsets.only(bottom: AppSpacing.md),
                      child: AppSkeleton.card(height: 92),
                    ),
                  ),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar a lista de colaboradores.',
                  onRetry: () => ref.invalidate(collaboratorsListProvider),
                ),
                data: (rows) {
                  final filtered = _applyFilters(rows);
                  if (filtered.isEmpty) {
                    return const AppEmptyState(
                      icon: Icons.people_outline_rounded,
                      title: 'Nenhum colaborador encontrado',
                      description: 'Ajuste a busca ou aguarde novos cadastros do RH.',
                    );
                  }
                  return Column(
                    children: filtered
                        .map(
                          (row) => Padding(
                            padding: const EdgeInsets.only(bottom: AppSpacing.md),
                            child: _CollaboratorRowCard(row: row),
                          ),
                        )
                        .toList(),
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

class _CollaboratorRowCard extends ConsumerWidget {
  final CollaboratorRowModel row;

  const _CollaboratorRowCard({required this.row});

  Future<void> _confirmToggleActive(BuildContext context, WidgetRef ref) async {
    final activate = !row.isActive;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(activate ? 'Reativar colaborador?' : 'Desativar colaborador?'),
        content: Text(
          activate
              ? '${row.fullName} voltará a ter acesso ao sistema.'
              : '${row.fullName} perderá o acesso ao sistema até ser reativado.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(activate ? 'Reativar' : 'Desativar'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      await ref.read(dashboardRepositoryProvider).toggleColaboradorActive(row.id);
      ref.invalidate(collaboratorsListProvider);
    } catch (e) {
      if (context.mounted) {
        final message = e.toString().replaceAll('Exception: ', '');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.md)),
          ),
        );
      }
    }
  }

  Future<void> _confirmToggleSectorLeader(BuildContext context, WidgetRef ref) async {
    final grant = !row.isSectorLeader;
    if (grant && row.sectorName == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Defina um setor para o colaborador antes de torná-lo líder.'),
          backgroundColor: AppColors.error,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.md)),
        ),
      );
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(grant ? 'Tornar líder do setor?' : 'Remover liderança do setor?'),
        content: Text(
          grant
              ? '${row.fullName} poderá cadastrar treinamentos do setor ${row.sectorName}.'
              : '${row.fullName} não poderá mais cadastrar treinamentos.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(grant ? 'Tornar líder' : 'Remover'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      await ref.read(dashboardRepositoryProvider).toggleSectorLeader(row.id);
      ref.invalidate(collaboratorsListProvider);
    } catch (e) {
      if (context.mounted) {
        final message = e.toString().replaceAll('Exception: ', '');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.md)),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppCard(
      onTap: () => context.push('/rh/collaborators/${row.id}'),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isWide = constraints.maxWidth > 560;

          final identity = Row(
            children: [
              AppAvatar(name: row.fullName, size: 42),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      row.fullName,
                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
                    ),
                    Text(
                      row.email,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 12, color: context.textSecondaryColor),
                    ),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: AppSpacing.xs,
                      runSpacing: 4,
                      children: [
                        if (row.sectorName != null)
                          AppBadge(label: row.sectorName!, variant: AppBadgeVariant.primary),
                        if (row.isSectorLeader)
                          const AppBadge(
                            label: 'Líder do Setor',
                            variant: AppBadgeVariant.purple,
                            icon: Icons.shield_outlined,
                          ),
                        if (!row.isActive)
                          const AppBadge(label: 'Inativo', variant: AppBadgeVariant.error),
                        AppBadge(
                          label: row.neverLoggedIn ? 'Nunca acessou' : 'Já acessou',
                          variant: row.neverLoggedIn ? AppBadgeVariant.warning : AppBadgeVariant.neutral,
                        ),
                        if (row.isOverdue)
                          AppBadge(
                            label: '${row.overdueCount} atrasado${row.overdueCount == 1 ? '' : 's'}',
                            variant: AppBadgeVariant.error,
                            icon: Icons.event_busy_rounded,
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          );

          final progress = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              AppProgress(
                value: row.coursesPercent / 100,
                showLabel: true,
                labelText: 'Treinamentos',
                color: AppColors.primary,
                height: 6,
              ),
              const SizedBox(height: AppSpacing.sm),
              AppProgress(
                value: row.checklistPercent / 100,
                showLabel: true,
                labelText: 'Checklist',
                color: AppColors.purple,
                height: 6,
              ),
            ],
          );

          final toggleButton = IconButton(
            tooltip: row.isActive ? 'Desativar colaborador' : 'Reativar colaborador',
            icon: Icon(
              row.isActive ? Icons.person_off_outlined : Icons.person_add_alt_1_rounded,
              size: 20,
              color: row.isActive
                  ? (context.isDark ? AppColors.errorDarkText : AppColors.error)
                  : (context.isDark ? AppColors.successDarkText : AppColors.success),
            ),
            onPressed: () => _confirmToggleActive(context, ref),
          );

          final editButton = IconButton(
            tooltip: 'Editar colaborador',
            icon: Icon(Icons.edit_outlined, size: 19, color: context.textMutedColor),
            onPressed: () async {
              final salvou = await context.push('/rh/collaborators/${row.id}/edit');
              if (salvou == true) ref.invalidate(collaboratorsListProvider);
            },
          );

          final sectorLeaderButton = IconButton(
            tooltip: row.isSectorLeader ? 'Remover liderança do setor' : 'Tornar líder do setor',
            icon: Icon(
              row.isSectorLeader ? Icons.shield_rounded : Icons.shield_outlined,
              size: 20,
              color: row.isSectorLeader ? AppColors.purple : context.textMutedColor,
            ),
            onPressed: () => _confirmToggleSectorLeader(context, ref),
          );

          if (isWide) {
            return Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(flex: 3, child: identity),
                const SizedBox(width: AppSpacing.xl),
                Expanded(flex: 2, child: progress),
                const SizedBox(width: AppSpacing.lg),
                _OverallBadge(percent: row.overallPercent),
                editButton,
                sectorLeaderButton,
                toggleButton,
              ],
            );
          }

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              identity,
              const SizedBox(height: AppSpacing.md),
              progress,
              const SizedBox(height: AppSpacing.sm),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _OverallBadge(percent: row.overallPercent),
                  Row(children: [editButton, sectorLeaderButton, toggleButton]),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}

class _OverallBadge extends StatelessWidget {
  final int percent;

  const _OverallBadge({required this.percent});

  @override
  Widget build(BuildContext context) {
    final variant = percent >= 100
        ? AppBadgeVariant.success
        : percent >= 50
            ? AppBadgeVariant.primary
            : AppBadgeVariant.warning;
    return AppBadge(label: '$percent% geral', variant: variant);
  }
}
