import 'package:flutter/material.dart';
import '../../../../app/theme.dart';
import '../../../../core/widgets/app_badge.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../shared/models/checklist_model.dart';

class ChecklistItemTile extends StatelessWidget {
  final ChecklistItemModel item;
  final VoidCallback onToggle;

  const ChecklistItemTile({
    super.key,
    required this.item,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final isDone = item.isCompleted;
    final isDark = context.isDark;

    final defaultBg = isDone
        ? (isDark ? const Color(0xFF0F172A) : AppColors.slate50)
        : (isDark ? AppColors.darkCard : Colors.white);

    final defaultBorder = isDone
        ? (isDark ? AppColors.successDarkBorder.withValues(alpha: 0.5) : AppColors.successBorder.withValues(alpha: 0.6))
        : (isDark ? AppColors.darkBorder : AppColors.border);

    return AppCard(
      onTap: onToggle,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
      backgroundColor: defaultBg,
      borderColor: defaultBorder,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Modern Checkbox
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: isDone
                  ? AppColors.success
                  : (isDark ? const Color(0xFF1E293B) : Colors.white),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: isDone ? AppColors.success : (isDark ? AppColors.darkBorder : AppColors.slate300),
                width: 1.8,
              ),
            ),
            child: isDone
                ? const Icon(Icons.check_rounded, size: 16, color: Colors.white)
                : null,
          ),
          const SizedBox(width: AppSpacing.lg),

          // Title & Meta
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: isDone ? FontWeight.w500 : FontWeight.w600,
                    color: isDone
                        ? (isDark ? AppColors.darkTextMuted : AppColors.slate500)
                        : context.textPrimaryColor,
                    decoration: isDone ? TextDecoration.lineThrough : null,
                  ),
                ),
                if (item.sectorName != null || item.completedAt != null) ...[
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      if (item.sectorName != null)
                        AppBadge(
                          label: item.sectorName!,
                          variant: AppBadgeVariant.primary,
                        ),
                      if (item.completedAt != null) ...[
                        const SizedBox(width: AppSpacing.sm),
                        Text(
                          'Concluído em ${item.completedAt!.day}/${item.completedAt!.month}',
                          style: TextStyle(
                            fontSize: 11,
                            color: isDark ? AppColors.successDarkText : AppColors.successText,
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
