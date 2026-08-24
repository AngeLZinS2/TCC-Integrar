import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../notifications/providers/notification_provider.dart';
import '../providers/course_provider.dart';
import '../providers/quiz_provider.dart';

class CourseDetailScreen extends ConsumerWidget {
  /// Conclusão manual — só para treinamento SEM avaliação.
  Widget _botaoConcluir(WidgetRef ref, dynamic course) {
    return AppButton(
      text: 'Marcar como Concluído',
      icon: Icons.check_circle_outline_rounded,
      size: AppButtonSize.lg,
      onPressed: () async {
        await ref
            .read(coursesListProvider.notifier)
            .updateProgress(course.id, 'completed');
        ref.invalidate(courseDetailProvider(course.id));
        // Concluir dispara notificações no servidor (treinamento concluído,
        // trilha completa, treinamento desbloqueado) — recarrega para o
        // contador do topo refletir na hora.
        ref.read(notificationsProvider.notifier).loadNotifications();
      },
    );
  }

  final int courseId;

  const CourseDetailScreen({
    super.key,
    required this.courseId,
  });

  IconData _getContentIcon(String type) {
    switch (type.toLowerCase()) {
      case 'video':
        return Icons.play_circle_fill_rounded;
      case 'pdf':
        return Icons.picture_as_pdf_rounded;
      case 'text':
      default:
        return Icons.article_rounded;
    }
  }

  Color _getContentColor(String type, bool isDark) {
    switch (type.toLowerCase()) {
      case 'video':
        return isDark ? AppColors.errorDarkText : const Color(0xFFEF4444);
      case 'pdf':
        return isDark ? const Color(0xFFFB923C) : const Color(0xFFF97316);
      case 'text':
      default:
        return isDark ? AppColors.primary300 : AppColors.primary;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final courseAsync = ref.watch(courseDetailProvider(courseId));
    final isDark = context.isDark;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        backgroundColor: context.surfaceColor,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_rounded, color: context.textPrimaryColor),
          onPressed: () => context.pop(),
        ),
        title: Text(
          'Detalhes do Treinamento',
          style: TextStyle(color: context.textPrimaryColor),
        ),
      ),
      body: courseAsync.when(
        loading: () => const SingleChildScrollView(
          padding: EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSkeleton.card(height: 180),
              SizedBox(height: AppSpacing.xxl),
              AppSkeleton(width: 200, height: 24),
              SizedBox(height: AppSpacing.lg),
              AppSkeleton.card(height: 80),
              SizedBox(height: AppSpacing.md),
              AppSkeleton.card(height: 80),
            ],
          ),
        ),
        error: (err, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.xxl),
            child: AppErrorState(
              message: 'Não foi possível carregar as informações do treinamento.',
              onRetry: () => ref.refresh(courseDetailProvider(courseId)),
            ),
          ),
        ),
        data: (course) {
          final isCompleted = course.userProgress.isCompleted;
          final isInProgress = course.userProgress.isInProgress;

          return Column(
            children: [
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(AppSpacing.xxl),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 900),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // ── LMS Hero Header ────────────────────────────
                        AppCard(
                          padding: const EdgeInsets.all(AppSpacing.xxl),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  AppBadge(
                                    label: course.isGeneral
                                        ? 'GERAL'
                                        : (course.sectorName?.toUpperCase() ?? 'SETOR'),
                                    variant: course.isGeneral
                                        ? AppBadgeVariant.neutral
                                        : AppBadgeVariant.primary,
                                  ),
                                  if (course.positionName != null) ...[
                                    const SizedBox(width: AppSpacing.sm),
                                    AppBadge(
                                      label: course.positionName!,
                                      variant: AppBadgeVariant.info,
                                    ),
                                  ],
                                  const Spacer(),
                                  AppBadge(
                                    label: course.isLocked && !isCompleted
                                        ? 'Bloqueado'
                                        : course.userProgress.statusDisplay,
                                    variant: isCompleted
                                        ? AppBadgeVariant.success
                                        : course.isLocked
                                            ? AppBadgeVariant.neutral
                                            : (isInProgress
                                                ? AppBadgeVariant.warning
                                                : AppBadgeVariant.neutral),
                                    showDot: true,
                                  ),
                                ],
                              ),
                              const SizedBox(height: AppSpacing.lg),

                              Text(
                                course.title,
                                style: TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.w800,
                                  color: context.textPrimaryColor,
                                  letterSpacing: -0.5,
                                ),
                              ),
                              if (course.description.isNotEmpty) ...[
                                const SizedBox(height: AppSpacing.md),
                                Text(
                                  course.description,
                                  style: TextStyle(
                                    fontSize: 14,
                                    color: context.textSecondaryColor,
                                    height: 1.6,
                                  ),
                                ),
                              ],
                              const SizedBox(height: AppSpacing.xl),

                              // Course Meta Chips
                              Row(
                                children: [
                                  Icon(
                                    Icons.layers_outlined,
                                    size: 16,
                                    color: isDark ? AppColors.darkTextMuted : AppColors.slate400,
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    '${course.contents.length} módulos de conteúdo',
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                      color: context.textSecondaryColor,
                                    ),
                                  ),
                                  if (course.userProgress.completedAt != null) ...[
                                    const SizedBox(width: AppSpacing.lg),
                                    Icon(
                                      Icons.verified_outlined,
                                      size: 16,
                                      color: isDark ? AppColors.successDarkText : AppColors.success,
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      'Concluído em ${course.userProgress.completedAt!.day}/${course.userProgress.completedAt!.month}/${course.userProgress.completedAt!.year}',
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        color: isDark ? AppColors.successDarkText : AppColors.successText,
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: AppSpacing.xxl),

                        // ── Content Modules Section ────────────────────
                        Text(
                          'Conteúdos do Treinamento',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: context.textPrimaryColor,
                            letterSpacing: -0.3,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.xs),
                        Text(
                          'Assista aos vídeos e leia os materiais abaixo para completar este treinamento.',
                          style: TextStyle(
                            fontSize: 13,
                            color: context.textSecondaryColor,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.lg),

                        if (course.contents.isEmpty)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(AppSpacing.xxl),
                            decoration: BoxDecoration(
                              color: context.cardColor,
                              borderRadius: BorderRadius.circular(AppRadius.lg),
                              border: Border.all(color: context.borderColor),
                            ),
                            child: Center(
                              child: Text(
                                'Nenhum módulo de conteúdo cadastrado para este treinamento ainda.',
                                style: TextStyle(color: context.textSecondaryColor),
                              ),
                            ),
                          )
                        else
                          ListView.separated(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: course.contents.length,
                            separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.md),
                            itemBuilder: (context, index) {
                              final content = course.contents[index];
                              final icon = _getContentIcon(content.type);
                              final color = _getContentColor(content.type, isDark);

                              return AppCard(
                                padding: const EdgeInsets.all(AppSpacing.lg),
                                child: Row(
                                  children: [
                                    Container(
                                      width: 44,
                                      height: 44,
                                      decoration: BoxDecoration(
                                        color: color.withValues(alpha: 0.12),
                                        borderRadius: BorderRadius.circular(AppRadius.md),
                                      ),
                                      child: Icon(icon, color: color, size: 22),
                                    ),
                                    const SizedBox(width: AppSpacing.lg),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Container(
                                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                decoration: BoxDecoration(
                                                  color: isDark ? const Color(0xFF1E293B) : AppColors.slate100,
                                                  borderRadius: BorderRadius.circular(4),
                                                ),
                                                child: Text(
                                                  'MÓDULO #${content.order}',
                                                  style: TextStyle(
                                                    fontSize: 10,
                                                    fontWeight: FontWeight.w800,
                                                    color: context.textSecondaryColor,
                                                  ),
                                                ),
                                              ),
                                              const SizedBox(width: AppSpacing.sm),
                                              Text(
                                                content.typeDisplay,
                                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color),
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: 4),
                                          Text(
                                            content.fileUrl,
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            style: TextStyle(
                                              fontSize: 13,
                                              fontWeight: FontWeight.w600,
                                              color: context.textPrimaryColor,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(width: AppSpacing.md),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                      decoration: BoxDecoration(
                                        color: isDark ? const Color(0xFF1E3A8A).withValues(alpha: 0.4) : AppColors.primary50,
                                        borderRadius: BorderRadius.circular(AppRadius.md),
                                        border: isDark ? Border.all(color: const Color(0xFF1D4ED8).withValues(alpha: 0.4)) : null,
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Text(
                                            'Abrir',
                                            style: TextStyle(
                                              fontSize: 12,
                                              fontWeight: FontWeight.w700,
                                              color: isDark ? AppColors.primary300 : AppColors.primary,
                                            ),
                                          ),
                                          const SizedBox(width: 4),
                                          Icon(
                                            Icons.open_in_new_rounded,
                                            size: 14,
                                            color: isDark ? AppColors.primary300 : AppColors.primary,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                      ],
                    ),
                  ),
                ),
              ),

              // ── Fixed Bottom Action Bar ──────────────────────────────
              Container(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xxl, vertical: AppSpacing.lg),
                decoration: BoxDecoration(
                  color: context.surfaceColor,
                  border: Border(top: BorderSide(color: context.borderColor)),
                ),
                child: SafeArea(
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 900),
                      child: Row(
                        children: [
                          if (course.isLocked && !isCompleted)
                            Expanded(
                              child: Container(
                                height: 50,
                                decoration: BoxDecoration(
                                  color: isDark ? const Color(0xFF1E293B) : AppColors.slate100,
                                  borderRadius: BorderRadius.circular(AppRadius.md),
                                  border: Border.all(color: context.borderColor),
                                ),
                                alignment: Alignment.center,
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.lock_outline_rounded, size: 18, color: context.textMutedColor),
                                    const SizedBox(width: AppSpacing.sm),
                                    Flexible(
                                      child: Text(
                                        course.prerequisiteTitle != null
                                            ? 'Conclua "${course.prerequisiteTitle}" para desbloquear'
                                            : 'Treinamento bloqueado até o pré-requisito ser concluído',
                                        textAlign: TextAlign.center,
                                        style: TextStyle(
                                          fontSize: 13,
                                          fontWeight: FontWeight.w600,
                                          color: context.textSecondaryColor,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            )
                          else if (course.userProgress.isNotStarted)
                            Expanded(
                              child: AppButton(
                                text: 'Iniciar Treinamento',
                                icon: Icons.play_arrow_rounded,
                                size: AppButtonSize.lg,
                                onPressed: () async {
                                  await ref
                                      .read(coursesListProvider.notifier)
                                      .updateProgress(course.id, 'in_progress');
                                  ref.invalidate(courseDetailProvider(course.id));
                                },
                              ),
                            )
                          else if (isInProgress)
                            Expanded(
                              // Treinamento com avaliação não fecha por
                              // autodeclaração — quem marca como concluído é a
                              // aprovação no quiz. Oferecer "Marcar como
                              // Concluído" aqui seria um botão que o backend
                              // sempre recusa com 400.
                              child: ref
                                  .watch(courseQuizProvider(course.id))
                                  .maybeWhen(
                                    data: (quiz) => quiz != null
                                        ? AppButton(
                                            text: 'Fazer Avaliação',
                                            icon: Icons.quiz_outlined,
                                            size: AppButtonSize.lg,
                                            onPressed: () async {
                                              final aprovado =
                                                  await context.push<bool>(
                                                '/courses/${course.id}/quiz'
                                                '?title=${Uri.encodeComponent(course.title)}',
                                              );
                                              ref.invalidate(
                                                courseDetailProvider(course.id),
                                              );
                                              ref.invalidate(
                                                courseQuizProvider(course.id),
                                              );
                                              if (aprovado == true) {
                                                ref
                                                    .read(notificationsProvider
                                                        .notifier)
                                                    .loadNotifications();
                                              }
                                            },
                                          )
                                        : _botaoConcluir(ref, course),
                                    orElse: () => _botaoConcluir(ref, course),
                                  ),
                            )
                          else ...[
                            Expanded(
                              child: Container(
                                height: 50,
                                decoration: BoxDecoration(
                                  color: isDark ? AppColors.successDark.withValues(alpha: 0.4) : AppColors.successLight,
                                  borderRadius: BorderRadius.circular(AppRadius.md),
                                  border: Border.all(color: isDark ? AppColors.successDarkBorder : AppColors.successBorder),
                                ),
                                alignment: Alignment.center,
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(
                                      Icons.verified_rounded,
                                      color: isDark ? AppColors.successDarkText : AppColors.success,
                                      size: 20,
                                    ),
                                    const SizedBox(width: AppSpacing.sm),
                                    Text(
                                      'Treinamento Concluído com Sucesso!',
                                      style: TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w700,
                                        color: isDark ? AppColors.successDarkText : AppColors.successText,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
