import 'package:flutter/material.dart';
import '../../app/theme.dart';

enum AppButtonVariant { primary, secondary, outline, ghost, danger }
enum AppButtonSize { sm, md, lg }

class AppButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final AppButtonVariant variant;
  final AppButtonSize size;
  final bool isLoading;
  final IconData? icon;
  final IconData? trailingIcon;
  final bool fullWidth;

  const AppButton({
    super.key,
    required this.text,
    required this.onPressed,
    this.variant = AppButtonVariant.primary,
    this.size = AppButtonSize.md,
    this.isLoading = false,
    this.icon,
    this.trailingIcon,
    this.fullWidth = false,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    final (height, fontSize, hPadding, iconSize) = switch (size) {
      AppButtonSize.sm => (36.0, 13.0, 12.0, 16.0),
      AppButtonSize.md => (44.0, 14.0, 18.0, 18.0),
      AppButtonSize.lg => (52.0, 15.0, 24.0, 20.0),
    };

    Color bgColor;
    Color fgColor;
    BorderSide borderSide = BorderSide.none;

    switch (variant) {
      case AppButtonVariant.primary:
        bgColor = AppColors.primary;
        fgColor = Colors.white;
        break;
      case AppButtonVariant.secondary:
        bgColor = isDark ? const Color(0xFF1E293B) : AppColors.slate100;
        fgColor = isDark ? AppColors.darkTextPrimary : AppColors.slate800;
        borderSide = isDark ? const BorderSide(color: AppColors.darkBorder, width: 1.0) : BorderSide.none;
        break;
      case AppButtonVariant.outline:
        bgColor = Colors.transparent;
        fgColor = isDark ? AppColors.darkTextPrimary : AppColors.slate700;
        borderSide = BorderSide(color: isDark ? AppColors.darkBorder : AppColors.border, width: 1.2);
        break;
      case AppButtonVariant.ghost:
        bgColor = Colors.transparent;
        fgColor = isDark ? AppColors.darkTextSecondary : AppColors.slate700;
        break;
      case AppButtonVariant.danger:
        bgColor = isDark ? AppColors.errorDark.withValues(alpha: 0.4) : AppColors.errorLight;
        fgColor = isDark ? AppColors.errorDarkText : AppColors.errorText;
        borderSide = BorderSide(color: isDark ? AppColors.errorDarkBorder : AppColors.errorBorder, width: 1.0);
        break;
    }

    final buttonChild = Row(
      mainAxisSize: fullWidth ? MainAxisSize.max : MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (isLoading) ...[
          SizedBox(
            width: iconSize,
            height: iconSize,
            child: CircularProgressIndicator(
              strokeWidth: 2.2,
              valueColor: AlwaysStoppedAnimation<Color>(fgColor),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
        ] else if (icon != null) ...[
          Icon(icon, size: iconSize, color: fgColor),
          const SizedBox(width: AppSpacing.sm),
        ],
        Text(
          text,
          style: TextStyle(
            fontSize: fontSize,
            fontWeight: FontWeight.w600,
            color: fgColor,
            letterSpacing: -0.2,
          ),
        ),
        if (!isLoading && trailingIcon != null) ...[
          const SizedBox(width: AppSpacing.sm),
          Icon(trailingIcon, size: iconSize, color: fgColor),
        ],
      ],
    );

    return SizedBox(
      width: fullWidth ? double.infinity : null,
      height: height,
      child: ElevatedButton(
        onPressed: isLoading ? null : onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: bgColor,
          foregroundColor: fgColor,
          elevation: 0,
          padding: EdgeInsets.symmetric(horizontal: hPadding),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
            side: borderSide,
          ),
          disabledBackgroundColor: bgColor.withValues(alpha: 0.6),
        ),
        child: buttonChild,
      ),
    );
  }
}
