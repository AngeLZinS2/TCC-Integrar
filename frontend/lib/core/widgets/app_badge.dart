import 'package:flutter/material.dart';
import '../../app/theme.dart';

enum AppBadgeVariant { primary, success, warning, error, info, neutral, purple }

class AppBadge extends StatelessWidget {
  final String label;
  final AppBadgeVariant variant;
  final IconData? icon;
  final bool showDot;

  const AppBadge({
    super.key,
    required this.label,
    this.variant = AppBadgeVariant.neutral,
    this.icon,
    this.showDot = false,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    Color bg;
    Color fg;
    Color border;

    switch (variant) {
      case AppBadgeVariant.primary:
        bg = isDark ? const Color(0xFF1E3A8A).withValues(alpha: 0.45) : AppColors.primary50;
        fg = isDark ? AppColors.primary300 : AppColors.primary700;
        border = isDark ? const Color(0xFF1D4ED8).withValues(alpha: 0.5) : AppColors.primary200;
        break;
      case AppBadgeVariant.success:
        bg = isDark ? AppColors.successDark.withValues(alpha: 0.45) : AppColors.successLight;
        fg = isDark ? AppColors.successDarkText : AppColors.successText;
        border = isDark ? AppColors.successDarkBorder : AppColors.successBorder;
        break;
      case AppBadgeVariant.warning:
        bg = isDark ? AppColors.warningDark.withValues(alpha: 0.45) : AppColors.warningLight;
        fg = isDark ? AppColors.warningDarkText : AppColors.warningText;
        border = isDark ? AppColors.warningDarkBorder : AppColors.warningBorder;
        break;
      case AppBadgeVariant.error:
        bg = isDark ? AppColors.errorDark.withValues(alpha: 0.45) : AppColors.errorLight;
        fg = isDark ? AppColors.errorDarkText : AppColors.errorText;
        border = isDark ? AppColors.errorDarkBorder : AppColors.errorBorder;
        break;
      case AppBadgeVariant.info:
        bg = isDark ? AppColors.infoDark.withValues(alpha: 0.45) : AppColors.infoLight;
        fg = isDark ? AppColors.infoDarkText : AppColors.infoText;
        border = isDark ? AppColors.infoDarkBorder : AppColors.infoBorder;
        break;
      case AppBadgeVariant.purple:
        bg = isDark ? AppColors.purpleDark.withValues(alpha: 0.45) : AppColors.purpleLight;
        fg = isDark ? AppColors.purpleDarkText : AppColors.purpleText;
        border = isDark ? AppColors.purpleDarkBorder : AppColors.purpleBorder;
        break;
      case AppBadgeVariant.neutral:
        bg = isDark ? const Color(0xFF1E293B) : AppColors.slate100;
        fg = isDark ? AppColors.darkTextSecondary : AppColors.slate700;
        border = isDark ? AppColors.darkBorder : AppColors.slate200;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3.5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: border, width: 1.0),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showDot) ...[
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: fg,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 5),
          ] else if (icon != null) ...[
            Icon(icon, size: 12, color: fg),
            const SizedBox(width: 4),
          ],
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: fg,
                letterSpacing: 0.2,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
