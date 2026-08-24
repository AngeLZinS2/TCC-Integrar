import 'package:flutter/material.dart';
import '../../app/theme.dart';
import 'app_motion.dart';

enum AppButtonVariant { primary, secondary, outline, ghost, danger }
enum AppButtonSize { sm, md, lg }

class AppButton extends StatefulWidget {
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
  State<AppButton> createState() => _AppButtonState();
}

class _AppButtonState extends State<AppButton> {
  bool _sobre = false;
  bool _pressionado = false;

  @override
  Widget build(BuildContext context) {
    // Atalhos para o corpo do build continuar legível depois da conversão
    // para StatefulWidget.
    final text = widget.text;
    final onPressed = widget.onPressed;
    final variant = widget.variant;
    final size = widget.size;
    final isLoading = widget.isLoading;
    final icon = widget.icon;
    final trailingIcon = widget.trailingIcon;
    final fullWidth = widget.fullWidth;

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

    final habilitado = !isLoading && onPressed != null;

    return SizedBox(
      width: fullWidth ? double.infinity : null,
      height: height,
      child: MouseRegion(
        onEnter: habilitado ? (_) => setState(() => _sobre = true) : null,
        onExit: habilitado ? (_) => setState(() => _sobre = false) : null,
        child: AnimatedScale(
          // Encolhe ao pressionar e cresce um fio sob o ponteiro. É a
          // confirmação tátil de que o clique registrou — sem ela, um botão
          // que dispara uma requisição lenta parece não ter respondido.
          scale: _pressionado
              ? 0.97
              : (_sobre && !prefereMovimentoReduzido(context) ? 1.02 : 1.0),
          duration: duracaoDe(context, 120),
          curve: Curves.easeOut,
          child: AnimatedContainer(
            duration: duracaoDe(context, 180),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppRadius.md),
              boxShadow: _sobre && habilitado && variant == AppButtonVariant.primary
                  ? [
                      BoxShadow(
                        color: bgColor.withValues(alpha: 0.42),
                        blurRadius: 18,
                        offset: const Offset(0, 6),
                      ),
                    ]
                  : const [],
            ),
            child: Listener(
              onPointerDown:
                  habilitado ? (_) => setState(() => _pressionado = true) : null,
              onPointerUp:
                  habilitado ? (_) => setState(() => _pressionado = false) : null,
              onPointerCancel:
                  habilitado ? (_) => setState(() => _pressionado = false) : null,
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
            ),
          ),
        ),
      ),
    );
  }
}
