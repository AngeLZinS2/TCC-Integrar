import 'package:flutter/material.dart';
import '../../../../app/theme.dart';
import '../../../../core/widgets/app_badge.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../shared/models/course_model.dart';

class CourseCard extends StatelessWidget {
  final CourseModel course;
  final VoidCallback onTap;

  const CourseCard({
    super.key,
    required this.course,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final progress = course.userProgress;
    final isCompleted = progress.isCompleted;
    final isInProgress = progress.isInProgress;
    final isDark = context.isDark;

    AppBadgeVariant badgeVariant;
    String statusLabel;
    IconData statusIcon;

    if (isCompleted) {
      badgeVariant = AppBadgeVariant.success;
      statusLabel = 'Concluído';
      statusIcon = Icons.check_circle_rounded;
    } else if (course.isLocked) {
      badgeVariant = AppBadgeVariant.neutral;
      statusLabel = 'Bloqueado';
      statusIcon = Icons.lock_outline_rounded;
    } else if (isInProgress) {
      badgeVariant = AppBadgeVariant.warning;
      statusLabel = 'Em andamento';
      statusIcon = Icons.timelapse_rounded;
    } else {
      badgeVariant = AppBadgeVariant.neutral;
      statusLabel = 'Não iniciado';
      statusIcon = Icons.radio_button_unchecked_rounded;
    }

    final moduleCount = course.contents.length;

    final actionColor = isCompleted
        ? (isDark ? AppColors.successDarkText : AppColors.successText)
        : (isDark ? AppColors.primary400 : AppColors.primary);

    return AppCard(
      onTap: onTap,
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Scope and Status Badges Row (Overflow safe)
          Row(
            children: [
              Flexible(
                child: AppBadge(
                  label: course.isGeneral ? 'GERAL' : (course.sectorName?.toUpperCase() ?? 'SETOR'),
                  variant: course.isGeneral ? AppBadgeVariant.neutral : AppBadgeVariant.primary,
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              AppBadge(
                label: statusLabel,
                variant: badgeVariant,
                icon: statusIcon,
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),

          // Course Title
          Text(
            course.title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: context.textPrimaryColor,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),

          // Description
          if (course.isLocked && course.prerequisiteTitle != null) ...[
            Text(
              'Requer: ${course.prerequisiteTitle}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: context.textMutedColor,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
          ] else if (course.description.isNotEmpty) ...[
            Text(
              course.description,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 13,
                color: context.textSecondaryColor,
                height: 1.4,
              ),
            ),
            const SizedBox(height: AppSpacing.md),
          ],

          const Spacer(),

          // Footer info + CTA (Overflow safe)
          Row(
            children: [
              Expanded(
                child: Row(
                  children: [
                    Icon(
                      Icons.layers_outlined,
                      size: 15,
                      color: isDark ? AppColors.darkTextMuted : AppColors.slate400,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '$moduleCount ${moduleCount == 1 ? "módulo" : "módulos"}',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: context.textSecondaryColor,
                      ),
                    ),
                    if (course.positionName != null) ...[
                      const SizedBox(width: 6),
                      Flexible(
                        child: Text(
                          '• ${course.positionName}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 12,
                            color: context.textMutedColor,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    isCompleted
                        ? 'Revisar'
                        : course.isLocked
                            ? 'Bloqueado'
                            : (isInProgress ? 'Continuar' : 'Começar'),
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: actionColor,
                    ),
                  ),
                  const SizedBox(width: 3),
                  Icon(
                    Icons.arrow_forward_ios_rounded,
                    size: 11,
                    color: actionColor,
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
