import 'package:flutter/material.dart';
import '../../../../app/theme.dart';

class CourseFilterSegmented extends StatelessWidget {
  final String selectedFilter; // 'all', 'in_progress', 'completed'
  final ValueChanged<String> onFilterChanged;

  const CourseFilterSegmented({
    super.key,
    required this.selectedFilter,
    required this.onFilterChanged,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF0F172A) : AppColors.slate100,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: context.borderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _SegmentButton(
            label: 'Todos',
            isSelected: selectedFilter == 'all',
            onTap: () => onFilterChanged('all'),
          ),
          _SegmentButton(
            label: 'Em andamento',
            isSelected: selectedFilter == 'in_progress',
            onTap: () => onFilterChanged('in_progress'),
          ),
          _SegmentButton(
            label: 'Concluídos',
            isSelected: selectedFilter == 'completed',
            onTap: () => onFilterChanged('completed'),
          ),
        ],
      ),
    );
  }
}

class _SegmentButton extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _SegmentButton({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: isSelected
              ? (isDark ? AppColors.darkCard : Colors.white)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          boxShadow: isSelected ? context.shadowSm : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
            color: isSelected
                ? (isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)
                : (isDark ? AppColors.darkTextMuted : AppColors.textSecondary),
          ),
        ),
      ),
    );
  }
}
