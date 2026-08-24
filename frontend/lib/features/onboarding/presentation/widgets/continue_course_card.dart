import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../../app/theme.dart';
import '../../../../core/widgets/app_badge.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../shared/models/course_model.dart';

class ContinueCourseCard extends StatelessWidget {
  final CourseModel? course;

  const ContinueCourseCard({
    super.key,
    required this.course,
  });

  @override
  Widget build(BuildContext context) {
    if (course == null) return const SizedBox.shrink();

    final isInProgress = course!.userProgress.isInProgress;
    final moduleCount = course!.contents.length;
    final isDark = context.isDark;

    return AppCard(
      onTap: () => context.push('/courses/${course!.id}'),
      borderColor: isDark ? const Color(0xFF1D4ED8).withValues(alpha: 0.5) : AppColors.primary200,
      backgroundColor: isDark ? const Color(0xFF1E3A8A).withValues(alpha: 0.2) : AppColors.primary50.withValues(alpha: 0.4),
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: const Icon(Icons.play_arrow_rounded, color: Colors.white, size: 22),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isInProgress ? 'CONTINUE DE ONDE PAROU' : 'PRÓXIMO TREINAMENTO SUGERIDO',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        color: isDark ? AppColors.primary300 : AppColors.primary700,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      course!.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: context.textPrimaryColor,
                        letterSpacing: -0.2,
                      ),
                    ),
                  ],
                ),
              ),
              AppBadge(
                label: isInProgress ? 'Em andamento' : 'Pendente',
                variant: isInProgress ? AppBadgeVariant.warning : AppBadgeVariant.neutral,
                showDot: true,
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),

          if (course!.description.isNotEmpty) ...[
            Text(
              course!.description,
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

          Row(
            children: [
              Icon(
                Icons.layers_outlined,
                size: 15,
                color: isDark ? AppColors.darkTextMuted : AppColors.slate400,
              ),
              const SizedBox(width: 4),
              Text(
                '$moduleCount ${moduleCount == 1 ? "módulo disponível" : "módulos disponíveis"}',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: context.textSecondaryColor,
                ),
              ),
              const Spacer(),
              Row(
                children: [
                  Text(
                    'Acessar treinamento',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: isDark ? AppColors.primary400 : AppColors.primary,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    Icons.arrow_forward_rounded,
                    size: 14,
                    color: isDark ? AppColors.primary400 : AppColors.primary,
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
