import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../core/widgets/stat_summary_card.dart';
import '../../company/presentation/company_settings_screen.dart' show SetupChecklistCard;
import '../models/dashboard_overview_model.dart';
import '../providers/dashboard_provider.dart';
import 'widgets/sector_bar_chart.dart';
import 'widgets/status_donut_chart.dart';

class RhDashboardScreen extends ConsumerWidget {
  const RhDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final overviewAsync = ref.watch(dashboardOverviewProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(dashboardOverviewProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const AppSectionHeader(
                title: 'Painel RH',
                subtitle: 'Visão geral da integração de todos os colaboradores.',
              ),
              const SizedBox(height: AppSpacing.lg),
              // Empresa recém-criada cai aqui primeiro. O checklist some
              // sozinho assim que a configuração termina.
              const SetupChecklistCard(hideWhenComplete: true),
              const SizedBox(height: AppSpacing.lg),
              overviewAsync.when(
                loading: () => Column(
                  children: [
                    LayoutBuilder(
                      builder: (context, constraints) => GridView.count(
                        crossAxisCount: constraints.maxWidth > 700 ? 4 : 2,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        crossAxisSpacing: AppSpacing.lg,
                        mainAxisSpacing: AppSpacing.lg,
                        childAspectRatio: 1.4,
                        children: List.generate(4, (_) => const AppSkeleton.card(height: 110)),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xl),
                    const AppSkeleton.card(height: 220),
                  ],
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar as estatísticas do painel.',
                  onRetry: () => ref.invalidate(dashboardOverviewProvider),
                ),
                data: (overview) => _DashboardBody(overview: overview),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashboardBody extends StatelessWidget {
  final DashboardOverviewModel overview;

  const _DashboardBody({required this.overview});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final crossAxisCount = constraints.maxWidth > 900
                ? 5
                : constraints.maxWidth > 500
                    ? 2
                    : 1;
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
                  subtitle: overview.inactiveCollaborators == 0
                      ? '${overview.activeCollaborators} ativos'
                      : '${overview.activeCollaborators} ativos · '
                          '${overview.inactiveCollaborators} inativos',
                ),
                StatSummaryCard(
                  icon: Icons.person_off_outlined,
                  iconColor: isDark ? AppColors.warningDarkText : AppColors.warning,
                  iconBgColor: isDark ? AppColors.warningDark.withValues(alpha: 0.4) : AppColors.warningLight,
                  value: '${overview.hiredLast30Days}',
                  title: 'Novos colaboradores',
                  subtitle: 'admitidos nos últimos 30 dias',
                ),
                StatSummaryCard(
                  icon: Icons.event_busy_rounded,
                  iconColor: isDark ? AppColors.errorDarkText : AppColors.error,
                  iconBgColor: isDark ? AppColors.errorDark.withValues(alpha: 0.4) : AppColors.errorLight,
                  value: '${overview.overdueCollaboratorsCount}',
                  title: 'Atrasados',
                  subtitle: 'com prazo vencido',
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
        _OnboardingStagePanel(overview: overview),
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
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: context.textPrimaryColor,
                          ),
                        ),
                      ),
                      AppBadge(
                        label: '${overview.fullyCompletedCount} em dia',
                        variant: AppBadgeVariant.success,
                      ),
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
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: context.textPrimaryColor,
                    ),
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
            return Column(
              children: [
                statusPanel,
                const SizedBox(height: AppSpacing.lg),
                sectorPanel,
              ],
            );
          },
        ),
        const SizedBox(height: AppSpacing.xl),
        AppButton(
          text: 'Ver todos os colaboradores',
          trailingIcon: Icons.arrow_forward_rounded,
          variant: AppButtonVariant.outline,
          onPressed: () => context.push('/rh/collaborators'),
        ),
      ],
    );
  }
}


/// Estágio da integração de cada pessoa.
///
/// As quatro categorias são mutuamente exclusivas e somam o total — quem
/// está atrasado conta como atrasado, não como "em andamento", porque é o
/// estado que exige ação do RH.
class _OnboardingStagePanel extends StatelessWidget {
  final DashboardOverviewModel overview;

  const _OnboardingStagePanel({required this.overview});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    final total = overview.totalCollaborators;

    final estagios = [
      (
        'Concluída',
        overview.onboardingCompleted,
        isDark ? AppColors.successDarkText : AppColors.success,
        Icons.check_circle_rounded,
      ),
      (
        'Em andamento',
        overview.onboardingInProgress,
        AppColors.primary,
        Icons.timelapse_rounded,
      ),
      (
        'Atrasada',
        overview.onboardingOverdue,
        isDark ? AppColors.errorDarkText : AppColors.error,
        Icons.event_busy_rounded,
      ),
      (
        'Não iniciada',
        overview.onboardingNotStarted,
        context.textMutedColor,
        Icons.radio_button_unchecked_rounded,
      ),
    ];

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Estágio da Integração',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: context.textPrimaryColor,
                  ),
                ),
              ),
              AppBadge(
                label: '${overview.onboardingPercent.toStringAsFixed(0)}% médio',
                variant: AppBadgeVariant.primary,
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          LayoutBuilder(
            builder: (context, constraints) {
              final colunas = constraints.maxWidth > 620 ? 4 : 2;
              return GridView.count(
                crossAxisCount: colunas,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisSpacing: AppSpacing.lg,
                mainAxisSpacing: AppSpacing.lg,
                childAspectRatio: 2.1,
                children: estagios.map((e) {
                  final (rotulo, valor, cor, icone) = e;
                  final percentual = total == 0 ? 0 : (valor / total * 100).round();
                  return Semantics(
                    label: '$rotulo: $valor colaboradores, $percentual por cento',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Row(
                          children: [
                            Icon(icone, size: 15, color: cor),
                            const SizedBox(width: 5),
                            Flexible(
                              child: Text(
                                rotulo,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w600,
                                  color: context.textSecondaryColor,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          '$valor',
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.w800,
                            color: cor,
                            letterSpacing: -0.6,
                          ),
                        ),
                        Text(
                          '$percentual% do time',
                          style: TextStyle(fontSize: 11, color: context.textMutedColor),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              );
            },
          ),
        ],
      ),
    );
  }
}
