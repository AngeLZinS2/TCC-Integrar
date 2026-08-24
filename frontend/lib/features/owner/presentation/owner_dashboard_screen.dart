import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_progress.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../core/widgets/stat_summary_card.dart';
import '../models/company_model.dart';
import '../providers/company_provider.dart';

class OwnerDashboardScreen extends ConsumerWidget {
  const OwnerDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
              const AppSectionHeader(
                title: 'Painel do Dono',
                subtitle: 'Visão geral de todas as empresas cadastradas na plataforma.',
              ),
              const SizedBox(height: AppSpacing.lg),
              companiesAsync.when(
                loading: () => Column(
                  children: [
                    LayoutBuilder(
                      builder: (context, constraints) => GridView.count(
                        crossAxisCount: constraints.maxWidth > 700 ? 3 : 1,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        crossAxisSpacing: AppSpacing.lg,
                        mainAxisSpacing: AppSpacing.lg,
                        childAspectRatio: 1.7,
                        children: List.generate(3, (_) => const AppSkeleton.card(height: 110)),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xl),
                    const AppSkeleton.card(height: 220),
                  ],
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar as estatísticas da plataforma.',
                  onRetry: () => ref.read(companiesListProvider.notifier).loadCompanies(),
                ),
                data: (companies) => _OwnerDashboardBody(companies: companies),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _OwnerDashboardBody extends StatelessWidget {
  final List<CompanyModel> companies;

  const _OwnerDashboardBody({required this.companies});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    final totalCompanies = companies.length;
    final activeCompanies = companies.where((c) => c.isActive).length;
    final totalCollaborators = companies.fold<int>(0, (sum, c) => sum + c.totalCollaborators);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final crossAxisCount = constraints.maxWidth > 700 ? 3 : 1;
            return GridView.count(
              crossAxisCount: crossAxisCount,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: AppSpacing.lg,
              mainAxisSpacing: AppSpacing.lg,
              childAspectRatio: 1.7,
              children: [
                StatSummaryCard(
                  icon: Icons.apartment_rounded,
                  iconColor: isDark ? AppColors.primary300 : AppColors.primary,
                  iconBgColor: isDark ? const Color(0xFF1E3A8A).withValues(alpha: 0.4) : AppColors.primary50,
                  value: '$totalCompanies',
                  title: 'Empresas Cadastradas',
                  subtitle: '$activeCompanies ativas',
                ),
                StatSummaryCard(
                  icon: Icons.groups_rounded,
                  iconColor: isDark ? AppColors.successDarkText : AppColors.success,
                  iconBgColor: isDark ? AppColors.successDark.withValues(alpha: 0.4) : AppColors.successLight,
                  value: '$totalCollaborators',
                  title: 'Colaboradores',
                  subtitle: 'em toda a plataforma',
                ),
                StatSummaryCard(
                  icon: Icons.person_off_outlined,
                  iconColor: isDark ? AppColors.warningDarkText : AppColors.warning,
                  iconBgColor: isDark ? AppColors.warningDark.withValues(alpha: 0.4) : AppColors.warningLight,
                  value: '${totalCompanies - activeCompanies}',
                  title: 'Empresas Inativas',
                  subtitle: 'acesso bloqueado',
                ),
              ],
            );
          },
        ),
        const SizedBox(height: AppSpacing.xl),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Progresso por Empresa',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
              ),
              const SizedBox(height: AppSpacing.lg),
              if (companies.isEmpty)
                Text(
                  'Nenhuma empresa cadastrada ainda.',
                  style: TextStyle(fontSize: 13, color: context.textMutedColor),
                )
              else
                for (final company in companies) ...[
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          company.name,
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
                        ),
                      ),
                      AppBadge(
                        label: company.isActive ? 'Ativa' : 'Inativa',
                        variant: company.isActive ? AppBadgeVariant.success : AppBadgeVariant.error,
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  AppProgress(
                    value: company.avgCourseCompletionPercent / 100,
                    showLabel: true,
                    labelText: 'Treinamentos',
                    color: AppColors.primary,
                    height: 6,
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  AppProgress(
                    value: company.avgChecklistCompletionPercent / 100,
                    showLabel: true,
                    labelText: 'Checklist',
                    color: AppColors.purple,
                    height: 6,
                  ),
                  if (company != companies.last) const SizedBox(height: AppSpacing.lg),
                ],
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
        AppButton(
          text: 'Ver todas as empresas',
          trailingIcon: Icons.arrow_forward_rounded,
          variant: AppButtonVariant.outline,
          onPressed: () => context.push('/owner/companies'),
        ),
      ],
    );
  }
}
