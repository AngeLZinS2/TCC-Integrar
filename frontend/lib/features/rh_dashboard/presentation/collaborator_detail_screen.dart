import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_avatar.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_progress.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../models/collaborator_detail_model.dart';
import '../providers/dashboard_provider.dart';

class CollaboratorDetailScreen extends ConsumerWidget {
  final int collaboratorId;

  const CollaboratorDetailScreen({super.key, required this.collaboratorId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(collaboratorDetailProvider(collaboratorId));

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        backgroundColor: context.surfaceColor,
        foregroundColor: context.textPrimaryColor,
        elevation: 0,
        title: const Text('Detalhe do Colaborador'),
      ),
      body: detailAsync.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            children: [
              AppSkeleton.card(height: 140),
              SizedBox(height: AppSpacing.xl),
              AppSkeleton.card(height: 240),
            ],
          ),
        ),
        error: (err, _) => Padding(
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: AppErrorState(
            message: 'Não foi possível carregar os dados deste colaborador.',
            onRetry: () => ref.invalidate(collaboratorDetailProvider(collaboratorId)),
          ),
        ),
        data: (detail) => _CollaboratorDetailBody(detail: detail),
      ),
    );
  }
}

class _CollaboratorDetailBody extends StatelessWidget {
  final CollaboratorDetailModel detail;

  const _CollaboratorDetailBody({required this.detail});

  String _formatDate(DateTime date) =>
      '${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')}/${date.year}';

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.xxl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppCard(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AppAvatar(name: detail.fullName, size: 56),
                const SizedBox(width: AppSpacing.lg),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        detail.fullName,
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          color: context.textPrimaryColor,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        detail.email,
                        style: TextStyle(fontSize: 13, color: context.textSecondaryColor),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Wrap(
                        spacing: AppSpacing.sm,
                        runSpacing: AppSpacing.sm,
                        children: [
                          if (detail.sectorName != null)
                            AppBadge(label: detail.sectorName!, variant: AppBadgeVariant.primary),
                          if (detail.positionName != null)
                            AppBadge(label: detail.positionName!, variant: AppBadgeVariant.neutral),
                          AppBadge(
                            label: detail.isActive ? 'Ativo' : 'Inativo',
                            variant: detail.isActive ? AppBadgeVariant.success : AppBadgeVariant.error,
                          ),
                          AppBadge(
                            label: detail.neverLoggedIn
                                ? 'Nunca acessou'
                                : 'Último acesso: ${_formatDate(detail.lastLogin!)}',
                            variant: detail.neverLoggedIn ? AppBadgeVariant.warning : AppBadgeVariant.neutral,
                          ),
                          if (detail.hireDate != null)
                            AppBadge(
                              label: 'Contratado em ${_formatDate(detail.hireDate!)}',
                              variant: AppBadgeVariant.neutral,
                            ),
                          if (detail.isOverdue)
                            AppBadge(
                              label: '${detail.overdueCount} atrasado${detail.overdueCount == 1 ? '' : 's'}',
                              variant: AppBadgeVariant.error,
                              icon: Icons.event_busy_rounded,
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xl),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AppProgress(
                  value: detail.coursesPercent / 100,
                  showLabel: true,
                  labelText: 'Treinamentos (${detail.coursesCompleted}/${detail.coursesTotal})',
                  color: AppColors.primary,
                ),
                const SizedBox(height: AppSpacing.lg),
                AppProgress(
                  value: detail.checklistPercent / 100,
                  showLabel: true,
                  labelText: 'Checklist (${detail.checklistCompleted}/${detail.checklistTotal})',
                  color: AppColors.purple,
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xxl),
          Text(
            'Treinamentos',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
          ),
          const SizedBox(height: AppSpacing.sm),
          if (detail.courses.isEmpty)
            const AppEmptyState(
              icon: Icons.school_outlined,
              title: 'Nenhum treinamento elegível',
              description: 'Este colaborador não tem treinamentos vinculados ao seu setor/cargo.',
            )
          else
            ...detail.courses.map((course) => _CourseRow(course: course)),
          const SizedBox(height: AppSpacing.xxl),
          Text(
            'Checklist',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
          ),
          const SizedBox(height: AppSpacing.sm),
          if (detail.checklistItems.isEmpty)
            const AppEmptyState(
              icon: Icons.task_alt_rounded,
              title: 'Nenhum item elegível',
              description: 'Este colaborador não tem itens de checklist vinculados ao seu setor.',
            )
          else
            ...detail.checklistItems.map((item) => _ChecklistRow(item: item)),
        ],
      ),
    );
  }
}

class _CourseRow extends StatelessWidget {
  final CollaboratorCourseStatus course;

  const _CourseRow({required this.course});

  @override
  Widget build(BuildContext context) {
    final (variant, label) = switch (course.status) {
      'completed' => (AppBadgeVariant.success, 'Concluído'),
      'in_progress' => (AppBadgeVariant.warning, 'Em andamento'),
      _ => (AppBadgeVariant.neutral, 'Não iniciado'),
    };

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: AppCard(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
        enableHover: false,
        child: Row(
          children: [
            Expanded(
              child: Text(
                course.title,
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: context.textPrimaryColor),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            if (course.isOverdue) ...[
              const AppBadge(label: 'Atrasado', variant: AppBadgeVariant.error, icon: Icons.event_busy_rounded),
              const SizedBox(width: AppSpacing.sm),
            ],
            AppBadge(label: label, variant: variant),
          ],
        ),
      ),
    );
  }
}

class _ChecklistRow extends StatelessWidget {
  final CollaboratorChecklistStatus item;

  const _ChecklistRow({required this.item});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: AppCard(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
        enableHover: false,
        child: Row(
          children: [
            Icon(
              item.completed ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
              size: 20,
              color: item.completed
                  ? (context.isDark ? AppColors.successDarkText : AppColors.success)
                  : (context.isDark ? AppColors.darkTextMuted : AppColors.slate400),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Text(
                item.title,
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: context.textPrimaryColor),
              ),
            ),
            if (item.isOverdue)
              const AppBadge(label: 'Atrasado', variant: AppBadgeVariant.error, icon: Icons.event_busy_rounded),
          ],
        ),
      ),
    );
  }
}
