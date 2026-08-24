import 'package:flutter/material.dart';
import '../../../../app/theme.dart';
import '../../../../core/widgets/app_badge.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../shared/models/material_model.dart';

class MaterialCard extends StatelessWidget {
  final MaterialModel material;
  final VoidCallback onOpen;

  const MaterialCard({
    super.key,
    required this.material,
    required this.onOpen,
  });

  IconData _getFileIcon(String ext) {
    switch (ext.toUpperCase()) {
      case 'PDF':
        return Icons.picture_as_pdf_rounded;
      case 'DOC':
      case 'DOCX':
        return Icons.description_rounded;
      case 'XLS':
      case 'XLSX':
        return Icons.table_chart_rounded;
      case 'HTML':
      case 'HTM':
        return Icons.language_rounded;
      default:
        return Icons.insert_drive_file_rounded;
    }
  }

  Color _getFileColor(String ext, bool isDark) {
    switch (ext.toUpperCase()) {
      case 'PDF':
        return isDark ? AppColors.errorDarkText : const Color(0xFFEF4444);
      case 'DOC':
      case 'DOCX':
        return isDark ? AppColors.primary300 : const Color(0xFF2563EB);
      case 'XLS':
      case 'XLSX':
        return isDark ? AppColors.successDarkText : const Color(0xFF10B981);
      case 'HTML':
      case 'HTM':
        return isDark ? AppColors.infoDarkText : const Color(0xFF0EA5E9);
      default:
        return isDark ? AppColors.purpleDarkText : AppColors.purple;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    final ext = material.fileExtension;
    final color = _getFileColor(ext, isDark);
    final icon = _getFileIcon(ext);

    return AppCard(
      onTap: onOpen,
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Icon(icon, color: color, size: 24),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AppBadge(
                      label: material.isGeneral ? 'GERAL' : (material.sectorName?.toUpperCase() ?? 'SETOR'),
                      variant: material.isGeneral ? AppBadgeVariant.neutral : AppBadgeVariant.primary,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      material.typeDisplay,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: color,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),

          Text(
            material.title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: context.textPrimaryColor,
              letterSpacing: -0.2,
            ),
          ),
          const Spacer(),

          Row(
            children: [
              if (material.createdAt != null)
                Text(
                  'Atualizado em ${material.createdAt!.day}/${material.createdAt!.month}/${material.createdAt!.year}',
                  style: TextStyle(fontSize: 11, color: context.textMutedColor),
                )
              else
                Text('Documento oficial', style: TextStyle(fontSize: 11, color: context.textMutedColor)),
              const Spacer(),
              Row(
                children: [
                  Text(
                    'Visualizar',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: isDark ? AppColors.primary400 : AppColors.primary,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    Icons.open_in_new_rounded,
                    size: 14,
                    color: isDark ? AppColors.primary400 : AppColors.primary,
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
