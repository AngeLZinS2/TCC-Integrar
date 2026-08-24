import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_progress.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../shared/models/checklist_model.dart';
import '../../notifications/providers/notification_provider.dart';
import '../providers/checklist_provider.dart';
import 'widgets/checklist_item_tile.dart';

class ChecklistScreen extends ConsumerWidget {
  const ChecklistScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final checklistAsync = ref.watch(checklistProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () => ref.read(checklistProvider.notifier).loadChecklist(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Page Header
              const AppSectionHeader(
                title: 'Checklist de Integração',
                subtitle: 'Acompanhe e confirme as etapas essenciais nos seus primeiros 30 dias na empresa.',
              ),
              const SizedBox(height: AppSpacing.lg),

              checklistAsync.when(
                loading: () => const Column(
                  children: [
                    AppSkeleton.card(height: 100),
                    SizedBox(height: AppSpacing.xxl),
                    AppSkeleton.card(height: 60),
                    SizedBox(height: AppSpacing.sm),
                    AppSkeleton.card(height: 60),
                  ],
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar o checklist de integração.',
                  onRetry: () => ref.read(checklistProvider.notifier).loadChecklist(),
                ),
                data: (items) {
                  if (items.isEmpty) {
                    return const AppEmptyState(
                      icon: Icons.checklist_rtl_rounded,
                      title: 'Nenhum item no checklist',
                      description: 'Não há tarefas de integração cadastradas para o seu setor no momento.',
                    );
                  }

                  final total = items.length;
                  final completed = items.where((i) => i.isCompleted).length;
                  final progress = total > 0 ? (completed / total) : 0.0;

                  final day1Items = items.where((i) => i.deadline == 'day1').toList();
                  final week1Items = items.where((i) => i.deadline == 'week1').toList();
                  final month1Items = items.where((i) => i.deadline == 'month1').toList();

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // ── Completion Meter Card ────────────────────────
                      Container(
                        padding: const EdgeInsets.all(AppSpacing.xl),
                        decoration: BoxDecoration(
                          color: context.cardColor,
                          borderRadius: BorderRadius.circular(AppRadius.lg),
                          border: Border.all(color: context.borderColor),
                          boxShadow: context.shadowSm,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.task_alt_rounded, color: AppColors.primary, size: 20),
                                const SizedBox(width: 8),
                                Text(
                                  'Progresso das Tarefas de Integração',
                                  style: TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w700,
                                    color: context.textPrimaryColor,
                                  ),
                                ),
                                const Spacer(),
                                Text(
                                  '$completed de $total concluídas (${(progress * 100).toInt()}%)',
                                  style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                    color: context.textSecondaryColor,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: AppSpacing.md),
                            AppProgress(
                              value: progress,
                              height: 8,
                              color: AppColors.primary,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xxl),

                      // ── Section 1: Dia 1 ─────────────────────────────
                      if (day1Items.isNotEmpty) ...[
                        _buildTimelineGroup(
                          context,
                          ref,
                          icon: Icons.looks_one_rounded,
                          iconColor: AppColors.primary,
                          title: 'Dia 1 — Primeiro Dia',
                          subtitle: 'Configurações de acessos, equipamentos e boas-vindas.',
                          items: day1Items,
                        ),
                        const SizedBox(height: AppSpacing.xxl),
                      ],

                      // ── Section 2: Primeira Semana ───────────────────
                      if (week1Items.isNotEmpty) ...[
                        _buildTimelineGroup(
                          context,
                          ref,
                          icon: Icons.calendar_view_week_rounded,
                          iconColor: AppColors.warning,
                          title: 'Primeira Semana',
                          subtitle: 'Alinhamentos com liderança, cultura e processos do setor.',
                          items: week1Items,
                        ),
                        const SizedBox(height: AppSpacing.xxl),
                      ],

                      // ── Section 3: Primeiro Mês ──────────────────────
                      if (month1Items.isNotEmpty) ...[
                        _buildTimelineGroup(
                          context,
                          ref,
                          icon: Icons.calendar_month_rounded,
                          iconColor: AppColors.purple,
                          title: 'Primeiro Mês',
                          subtitle: 'Reunião de feedback inicial e conclusão da ambientação.',
                          items: month1Items,
                        ),
                      ],
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

  Widget _buildTimelineGroup(
    BuildContext context,
    WidgetRef ref, {
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required List<ChecklistItemModel> items,
  }) {
    final groupCompleted = items.where((i) => i.isCompleted).length;
    final isDark = context.isDark;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: Icon(icon, color: iconColor, size: 18),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: context.textPrimaryColor,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: TextStyle(fontSize: 12, color: context.textSecondaryColor),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E293B) : AppColors.slate100,
                borderRadius: BorderRadius.circular(AppRadius.pill),
                border: isDark ? Border.all(color: context.borderColor) : null,
              ),
              child: Text(
                '$groupCompleted/${items.length}',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: context.textSecondaryColor,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: items.length,
          separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.sm),
          itemBuilder: (context, index) {
            final item = items[index];
            return ChecklistItemTile(
              item: item,
              onToggle: () async {
                await ref.read(checklistProvider.notifier).toggleItem(item.id);
                // Concluir o último item dispara a notificação de checklist
                // completo no servidor — recarrega para o contador atualizar.
                ref.read(notificationsProvider.notifier).loadNotifications();
              },
            );
          },
        ),
      ],
    );
  }
}
