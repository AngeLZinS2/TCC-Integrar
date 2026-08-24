import 'package:flutter/material.dart';
import '../../../../app/theme.dart';
import '../../../../core/widgets/app_progress.dart';
import '../../models/dashboard_overview_model.dart';

class SectorBarChart extends StatelessWidget {
  final List<SectorBreakdown> bySector;

  const SectorBarChart({super.key, required this.bySector});

  @override
  Widget build(BuildContext context) {
    if (bySector.isEmpty) {
      return SizedBox(
        height: 80,
        child: Center(
          child: Text(
            'Nenhum colaborador vinculado a um setor ainda',
            style: TextStyle(fontSize: 13, color: context.textMutedColor),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final sector in bySector) ...[
          Row(
            children: [
              Expanded(
                child: Text(
                  sector.sectorName,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: context.textPrimaryColor,
                  ),
                ),
              ),
              Text(
                '${sector.collaborators} colaborador${sector.collaborators == 1 ? '' : 'es'}',
                style: TextStyle(fontSize: 11, color: context.textMutedColor),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          AppProgress(
            value: sector.avgCoursePercent / 100,
            showLabel: true,
            labelText: 'Treinamentos',
            color: AppColors.primary,
            height: 6,
          ),
          const SizedBox(height: AppSpacing.xs),
          AppProgress(
            value: sector.avgChecklistPercent / 100,
            showLabel: true,
            labelText: 'Checklist',
            color: AppColors.purple,
            height: 6,
          ),
          if (sector != bySector.last) const SizedBox(height: AppSpacing.lg),
        ],
      ],
    );
  }
}
