import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../../../../app/theme.dart';
import '../../models/dashboard_overview_model.dart';

class StatusDonutChart extends StatelessWidget {
  final CourseStatusDistribution distribution;

  const StatusDonutChart({super.key, required this.distribution});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    final total = distribution.total;

    if (total == 0) {
      return SizedBox(
        height: 120,
        child: Center(
          child: Text(
            'Sem treinamentos cadastrados ainda',
            style: TextStyle(fontSize: 13, color: context.textMutedColor),
          ),
        ),
      );
    }

    final completedColor = isDark ? AppColors.successDarkText : AppColors.success;
    final inProgressColor = isDark ? AppColors.warningDarkText : AppColors.warning;
    final notStartedColor = isDark ? AppColors.darkTextMuted : AppColors.slate300;

    final sections = <PieChartSectionData>[
      if (distribution.completed > 0)
        PieChartSectionData(value: distribution.completed.toDouble(), color: completedColor, radius: 22, showTitle: false),
      if (distribution.inProgress > 0)
        PieChartSectionData(value: distribution.inProgress.toDouble(), color: inProgressColor, radius: 22, showTitle: false),
      if (distribution.notStarted > 0)
        PieChartSectionData(value: distribution.notStarted.toDouble(), color: notStartedColor, radius: 22, showTitle: false),
    ];

    return Row(
      children: [
        SizedBox(
          width: 120,
          height: 120,
          child: PieChart(
            PieChartData(sections: sections, centerSpaceRadius: 34, sectionsSpace: 2),
          ),
        ),
        const SizedBox(width: AppSpacing.xl),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              _LegendRow(label: 'Concluídos', value: distribution.completed, color: completedColor),
              const SizedBox(height: AppSpacing.sm),
              _LegendRow(label: 'Em andamento', value: distribution.inProgress, color: inProgressColor),
              const SizedBox(height: AppSpacing.sm),
              _LegendRow(label: 'Não iniciados', value: distribution.notStarted, color: notStartedColor),
            ],
          ),
        ),
      ],
    );
  }
}

class _LegendRow extends StatelessWidget {
  final String label;
  final int value;
  final Color color;

  const _LegendRow({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(width: 10, height: 10, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: Text(label, style: TextStyle(fontSize: 13, color: context.textSecondaryColor)),
        ),
        Text(
          '$value',
          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
        ),
      ],
    );
  }
}
