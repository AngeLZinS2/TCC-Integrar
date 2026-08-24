import 'package:flutter/material.dart';
import '../../app/theme.dart';
import 'app_button.dart';

class AppEmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;
  final String? actionText;
  final VoidCallback? onAction;

  const AppEmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.description,
    this.actionText,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xxl, vertical: AppSpacing.huge),
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: context.borderColor),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E3A8A).withValues(alpha: 0.35) : AppColors.primary50,
              shape: BoxShape.circle,
              border: Border.all(
                color: isDark ? const Color(0xFF1D4ED8).withValues(alpha: 0.4) : AppColors.primary100,
              ),
            ),
            child: Icon(icon, size: 28, color: isDark ? AppColors.primary400 : AppColors.primary),
          ),
          const SizedBox(height: AppSpacing.lg),
          Text(
            title,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: context.textPrimaryColor,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 380),
            child: Text(
              description,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                color: context.textSecondaryColor,
                height: 1.5,
              ),
            ),
          ),
          if (actionText != null && onAction != null) ...[
            const SizedBox(height: AppSpacing.xl),
            AppButton(
              text: actionText!,
              onPressed: onAction!,
              size: AppButtonSize.sm,
            ),
          ],
        ],
      ),
    );
  }
}
