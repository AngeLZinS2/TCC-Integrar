import 'package:flutter/material.dart';
import '../../app/theme.dart';

class AppCard extends StatefulWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final Color? backgroundColor;
  final Color? borderColor;
  final double? borderRadius;
  final List<BoxShadow>? boxShadow;
  final bool enableHover;

  const AppCard({
    super.key,
    required this.child,
    this.padding,
    this.onTap,
    this.backgroundColor,
    this.borderColor,
    this.borderRadius,
    this.boxShadow,
    this.enableHover = true,
  });

  @override
  State<AppCard> createState() => _AppCardState();
}

class _AppCardState extends State<AppCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final radius = widget.borderRadius ?? AppRadius.lg;
    final isClickable = widget.onTap != null;
    final isDark = context.isDark;

    final defaultBg = widget.backgroundColor ?? (isDark ? AppColors.darkCard : AppColors.card);
    final defaultBorderColor = widget.borderColor ??
        (_isHovered && isClickable
            ? (isDark ? AppColors.primary400 : AppColors.primary300)
            : (isDark ? AppColors.darkBorder : AppColors.border));

    final defaultShadow = widget.boxShadow ??
        (_isHovered && widget.enableHover ? context.shadowMd : context.shadowSm);

    final border = Border.all(
      color: defaultBorderColor,
      width: 1.0,
    );

    return MouseRegion(
      cursor: isClickable ? SystemMouseCursors.click : SystemMouseCursors.basic,
      onEnter: (_) {
        if (mounted && widget.enableHover) setState(() => _isHovered = true);
      },
      onExit: (_) {
        if (mounted && widget.enableHover) setState(() => _isHovered = false);
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
        decoration: BoxDecoration(
          color: _isHovered && widget.enableHover && isClickable && widget.backgroundColor == null
              ? (isDark ? AppColors.darkCardHover : defaultBg)
              : defaultBg,
          borderRadius: BorderRadius.circular(radius),
          border: border,
          boxShadow: defaultShadow,
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(radius),
          child: InkWell(
            borderRadius: BorderRadius.circular(radius),
            onTap: widget.onTap,
            child: Padding(
              padding: widget.padding ?? const EdgeInsets.all(AppSpacing.lg),
              child: widget.child,
            ),
          ),
        ),
      ),
    );
  }
}
