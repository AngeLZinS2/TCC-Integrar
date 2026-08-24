import 'package:flutter/material.dart';
import '../../app/theme.dart';
import 'app_card.dart';

class StatSummaryCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final Color iconBgColor;
  final String title;
  final String value;
  final String? subtitle;
  final VoidCallback? onTap;

  const StatSummaryCard({
    super.key,
    required this.icon,
    required this.iconColor,
    required this.iconBgColor,
    required this.title,
    required this.value,
    this.subtitle,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: onTap,
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: iconBgColor,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Icon(icon, size: 20, color: iconColor),
              ),
              if (onTap != null) ...[
                const Spacer(),
                Icon(
                  Icons.arrow_forward_ios_rounded,
                  size: 12,
                  color: context.isDark ? AppColors.darkTextMuted : AppColors.slate400,
                ),
              ],
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            value,
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: context.textPrimaryColor,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            title,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: context.textPrimaryColor,
            ),
          ),
          if (subtitle != null)
            Text(
              subtitle!,
              style: TextStyle(
                fontSize: 11,
                color: context.textMutedColor,
              ),
            ),
        ],
      ),
    );
  }
}
