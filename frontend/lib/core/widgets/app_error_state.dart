import 'package:flutter/material.dart';
import '../../app/theme.dart';
import 'app_button.dart';

class AppErrorState extends StatelessWidget {
  final String title;
  final String message;
  final VoidCallback onRetry;

  const AppErrorState({
    super.key,
    this.title = 'Não foi possível carregar os dados',
    required this.message,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.xxl),
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: context.borderColor),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: isDark ? AppColors.errorDark.withValues(alpha: 0.4) : AppColors.errorLight,
              shape: BoxShape.circle,
              border: Border.all(color: isDark ? AppColors.errorDarkBorder : AppColors.errorBorder),
            ),
            child: Icon(Icons.error_outline_rounded, size: 28, color: isDark ? AppColors.errorDarkText : AppColors.error),
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
            constraints: const BoxConstraints(maxWidth: 360),
            child: Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                color: context.textSecondaryColor,
                height: 1.5,
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.xl),
          AppButton(
            text: 'Tentar novamente',
            icon: Icons.refresh_rounded,
            onPressed: onRetry,
            variant: AppButtonVariant.outline,
            size: AppButtonSize.sm,
          ),
        ],
      ),
    );
  }
}
