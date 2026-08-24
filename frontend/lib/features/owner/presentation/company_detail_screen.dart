import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../core/widgets/stat_summary_card.dart';
import '../../rh_dashboard/models/dashboard_overview_model.dart';
import '../../rh_dashboard/presentation/widgets/sector_bar_chart.dart';
import '../../rh_dashboard/presentation/widgets/status_donut_chart.dart';
import '../providers/company_provider.dart';

class CompanyDetailScreen extends ConsumerWidget {
  final int companyId;

  const CompanyDetailScreen({super.key, required this.companyId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final overviewAsync = ref.watch(companyDashboardProvider(companyId));

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        backgroundColor: context.surfaceColor,
        foregroundColor: context.textPrimaryColor,
        elevation: 0,
        title: const Text('Detalhe da Empresa'),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(companyDashboardProvider(companyId));
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              overviewAsync.when(
                loading: () => const Column(
                  children: [
                    AppSkeleton.card(height: 220),
                  ],
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar as estatísticas desta empresa.',
                  onRetry: () => ref.invalidate(companyDashboardProvider(companyId)),
                ),
                data: (overview) => _CompanyOverview(overview: overview),
              ),
              const SizedBox(height: AppSpacing.xxl),
              const _PrivacyNotice(),
            ],
          ),
        ),
      ),
    );
  }
}

class _CompanyOverview extends StatelessWidget {
  final DashboardOverviewModel overview;

  const _CompanyOverview({required this.overview});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final crossAxisCount = constraints.maxWidth > 700 ? 4 : 2;
            return GridView.count(
              crossAxisCount: crossAxisCount,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: AppSpacing.lg,
              mainAxisSpacing: AppSpacing.lg,
              childAspectRatio: 1.6,
              children: [
                StatSummaryCard(
                  icon: Icons.groups_rounded,
                  iconColor: isDark ? AppColors.primary300 : AppColors.primary,
                  iconBgColor: isDark ? const Color(0xFF1E3A8A).withValues(alpha: 0.4) : AppColors.primary50,
                  value: '${overview.totalCollaborators}',
                  title: 'Colaboradores',
                  subtitle: '${overview.activeLast30Days} ativos (30 dias)',
                ),
                StatSummaryCard(
                  icon: Icons.person_off_outlined,
                  iconColor: isDark ? AppColors.warningDarkText : AppColors.warning,
                  iconBgColor: isDark ? AppColors.warningDark.withValues(alpha: 0.4) : AppColors.warningLight,
                  value: '${overview.neverLoggedIn}',
                  title: 'Nunca acessaram',
                  subtitle: 'ainda não fizeram login',
                ),
                StatSummaryCard(
                  icon: Icons.school_outlined,
                  iconColor: isDark ? AppColors.successDarkText : AppColors.success,
                  iconBgColor: isDark ? AppColors.successDark.withValues(alpha: 0.4) : AppColors.successLight,
                  value: '${overview.avgCourseCompletionPercent.toStringAsFixed(0)}%',
                  title: 'Treinamentos',
                  subtitle: 'conclusão média',
                ),
                StatSummaryCard(
                  icon: Icons.task_alt_rounded,
                  iconColor: isDark ? AppColors.purpleDarkText : AppColors.purple,
                  iconBgColor: isDark ? AppColors.purpleDark.withValues(alpha: 0.4) : AppColors.purpleLight,
                  value: '${overview.avgChecklistCompletionPercent.toStringAsFixed(0)}%',
                  title: 'Checklist',
                  subtitle: 'conclusão média',
                ),
              ],
            );
          },
        ),
        const SizedBox(height: AppSpacing.xl),
        LayoutBuilder(
          builder: (context, constraints) {
            final isWide = constraints.maxWidth > 800;

            final statusPanel = AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'Status dos Treinamentos',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
                        ),
                      ),
                      AppBadge(label: '${overview.fullyCompletedCount} em dia', variant: AppBadgeVariant.success),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  StatusDonutChart(distribution: overview.courseStatusDistribution),
                ],
              ),
            );

            final sectorPanel = AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Progresso por Setor',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  SectorBarChart(bySector: overview.bySector),
                ],
              ),
            );

            if (isWide) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: statusPanel),
                  const SizedBox(width: AppSpacing.lg),
                  Expanded(child: sectorPanel),
                ],
              );
            }
            return Column(children: [statusPanel, const SizedBox(height: AppSpacing.lg), sectorPanel]);
          },
        ),
      ],
    );
  }
}

/// Explica por que o painel da plataforma mostra apenas números.
///
/// A restrição é do backend, não desta tela: o endpoint que devolvia a
/// lista nominal de colaboradores foi removido. Esta nota existe para que
/// a ausência do dado seja lida como decisão de projeto, não como falha.
class _PrivacyNotice extends StatelessWidget {
  const _PrivacyNotice();

  @override
  Widget build(BuildContext context) {
    return AppCard(
      enableHover: false,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.shield_outlined, size: 20, color: context.textMutedColor),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Dados dos colaboradores',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: context.textPrimaryColor,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'A plataforma mostra apenas indicadores agregados de cada empresa. '
                  'Nomes, e-mails e o progresso individual de cada colaborador são '
                  'visíveis somente para o RH da própria empresa.',
                  style: TextStyle(
                    fontSize: 12,
                    height: 1.45,
                    color: context.textSecondaryColor,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
