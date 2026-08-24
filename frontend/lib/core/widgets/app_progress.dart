import 'package:flutter/material.dart';
import '../../app/theme.dart';

class AppProgress extends StatelessWidget {
  final double value; // 0.0 a 1.0
  final double height;
  final Color? color;
  final Color? backgroundColor;
  final bool showLabel;
  final String? labelText;

  const AppProgress({
    super.key,
    required this.value,
    this.height = 8.0,
    this.color,
    this.backgroundColor,
    this.showLabel = false,
    this.labelText,
  });

  @override
  Widget build(BuildContext context) {
    final clampedValue = value.clamp(0.0, 1.0);
    final percent = (clampedValue * 100).toInt();
    final isDark = context.isDark;

    final defaultBg = backgroundColor ?? (isDark ? const Color(0xFF334155) : AppColors.slate200);

    final progressBar = ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.pill),
      child: TweenAnimationBuilder<double>(
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeOutCubic,
        tween: Tween(begin: 0.0, end: clampedValue),
        builder: (context, animVal, _) {
          return LinearProgressIndicator(
            value: animVal,
            minHeight: height,
            backgroundColor: defaultBg,
            valueColor: AlwaysStoppedAnimation<Color>(color ?? AppColors.primary),
          );
        },
      ),
    );

    if (!showLabel) return progressBar;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              labelText ?? 'Progresso',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: context.textSecondaryColor,
              ),
            ),
            Text(
              '$percent%',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: context.textPrimaryColor,
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        progressBar,
      ],
    );
  }
}
