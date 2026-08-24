import 'package:flutter/material.dart';
import '../../app/theme.dart';

class AppSectionHeader extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final String? actionText;
  final VoidCallback? onAction;

  const AppSectionHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.trailing,
    this.actionText,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                    color: context.textPrimaryColor,
                    letterSpacing: -0.3,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle!,
                    style: TextStyle(
                      fontSize: 13,
                      color: context.textSecondaryColor,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (trailing != null)
            trailing!
          else if (actionText != null && onAction != null)
            InkWell(
              onTap: onAction,
              borderRadius: BorderRadius.circular(AppRadius.sm),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                child: Text(
                  actionText!,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: context.isDark ? AppColors.primary400 : AppColors.primary,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
