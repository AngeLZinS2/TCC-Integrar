import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_progress.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../shared/services/csv_download/csv_download.dart';
import '../models/company_model.dart';
import '../providers/company_provider.dart';

class CompaniesListScreen extends ConsumerStatefulWidget {
  const CompaniesListScreen({super.key});

  @override
  ConsumerState<CompaniesListScreen> createState() => _CompaniesListScreenState();
}

class _CompaniesListScreenState extends ConsumerState<CompaniesListScreen> {
  final _searchController = TextEditingController();
  String _search = '';
  bool _isExporting = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _handleExport() async {
    setState(() => _isExporting = true);
    try {
      final bytes = await ref.read(companyRepositoryProvider).exportCompaniesCsv();
      saveCsv(bytes, 'empresas.csv');
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

  List<CompanyModel> _applyFilter(List<CompanyModel> companies) {
    if (_search.isEmpty) return companies;
    final query = _search.toLowerCase();
    return companies.where((c) => c.name.toLowerCase().contains(query)).toList();
  }

  @override
  Widget build(BuildContext context) {
    final companiesAsync = ref.watch(companiesListProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () => ref.read(companiesListProvider.notifier).loadCompanies(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Empresas',
                subtitle: 'Cadastro e acompanhamento das empresas clientes.',
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
                      text: 'Nova Empresa',
                      icon: Icons.add_rounded,
                      size: AppButtonSize.sm,
                      onPressed: () => context.push('/owner/companies/new'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              TextField(
                controller: _searchController,
                onChanged: (value) => setState(() => _search = value),
                decoration: InputDecoration(
                  hintText: 'Buscar por nome da empresa...',
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
              const SizedBox(height: AppSpacing.xl),
              companiesAsync.when(
                loading: () => Column(
                  children: List.generate(
                    3,
                    (_) => const Padding(
                      padding: EdgeInsets.only(bottom: AppSpacing.md),
                      child: AppSkeleton.card(height: 92),
                    ),
                  ),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar a lista de empresas.',
                  onRetry: () => ref.read(companiesListProvider.notifier).loadCompanies(),
                ),
                data: (companies) {
                  final filtered = _applyFilter(companies);
                  if (filtered.isEmpty) {
                    return const AppEmptyState(
                      icon: Icons.apartment_outlined,
                      title: 'Nenhuma empresa encontrada',
                      description: 'Ajuste a busca ou cadastre uma nova empresa.',
                    );
                  }
                  return Column(
                    children: filtered
                        .map(
                          (company) => Padding(
                            padding: const EdgeInsets.only(bottom: AppSpacing.md),
                            child: _CompanyCard(company: company),
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

class _CompanyCard extends ConsumerWidget {
  final CompanyModel company;

  const _CompanyCard({required this.company});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppCard(
      onTap: () => context.push('/owner/companies/${company.id}'),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isWide = constraints.maxWidth > 560;

          final identity = Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: context.isDark ? const Color(0xFF1E3A8A).withValues(alpha: 0.4) : AppColors.primary50,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Icon(
                  Icons.apartment_rounded,
                  color: context.isDark ? AppColors.primary300 : AppColors.primary,
                  size: 22,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      company.name,
                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
                    ),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: AppSpacing.xs,
                      runSpacing: 4,
                      children: [
                        AppBadge(
                          label: company.isActive ? 'Ativa' : 'Inativa',
                          variant: company.isActive ? AppBadgeVariant.success : AppBadgeVariant.error,
                        ),
                        AppBadge(
                          label: '${company.totalCollaborators} colaboradores',
                          variant: AppBadgeVariant.neutral,
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
                value: company.avgCourseCompletionPercent / 100,
                showLabel: true,
                labelText: 'Treinamentos',
                color: AppColors.primary,
                height: 6,
              ),
              const SizedBox(height: AppSpacing.sm),
              AppProgress(
                value: company.avgChecklistCompletionPercent / 100,
                showLabel: true,
                labelText: 'Checklist',
                color: AppColors.purple,
                height: 6,
              ),
            ],
          );

          final toggleButton = AppButton(
            text: company.isActive ? 'Desativar' : 'Ativar',
            variant: company.isActive ? AppButtonVariant.danger : AppButtonVariant.secondary,
            size: AppButtonSize.sm,
            onPressed: () => ref.read(companiesListProvider.notifier).toggleActive(company.id),
          );

          if (isWide) {
            return Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(flex: 3, child: identity),
                const SizedBox(width: AppSpacing.xl),
                Expanded(flex: 2, child: progress),
                const SizedBox(width: AppSpacing.lg),
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
              const SizedBox(height: AppSpacing.md),
              Align(alignment: Alignment.centerRight, child: toggleButton),
            ],
          );
        },
      ),
    );
  }
}
