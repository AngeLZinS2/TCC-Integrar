import 'package:flutter/material.dart';
import '../../../../app/theme.dart';
import '../../../../shared/models/hr_request_model.dart';

class RequestCard extends StatelessWidget {
  final HRRequest request;
  final VoidCallback onTap;

  const RequestCard({
    super.key,
    required this.request,
    required this.onTap,
  });

  Color _getStatusColor(String status) {
    switch (status) {
      case 'received': return AppColors.primary;
      case 'in_progress': return AppColors.warning;
      case 'resolved': return AppColors.success;
      case 'closed': return AppColors.textSecondary;
      case 'cancelled': return AppColors.error;
      default: return AppColors.textSecondary;
    }
  }

  String _getStatusText(String status) {
    switch (status) {
      case 'received': return 'Recebida';
      case 'in_progress': return 'Em Andamento';
      case 'resolved': return 'Resolvida';
      case 'closed': return 'Fechada';
      case 'cancelled': return 'Cancelada';
      default: return status;
    }
  }

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppSpacing.md),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.lg),
        decoration: BoxDecoration(
          color: context.surfaceColor,
          borderRadius: BorderRadius.circular(AppSpacing.md),
          border: Border.all(color: context.borderColor),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  request.number,
                  style: context.textTheme.labelMedium?.copyWith(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getStatusColor(request.status).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(AppSpacing.xs),
                  ),
                  child: Text(
                    _getStatusText(request.status),
                    style: context.textTheme.labelSmall?.copyWith(
                      color: _getStatusColor(request.status),
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              request.subject,
              style: context.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              'Categoria: ${request.category.toUpperCase()}',
              style: context.textTheme.bodySmall?.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const Spacer(),
            Row(
              children: [
                const Icon(Icons.person_outline, size: 16, color: AppColors.textSecondary),
                const SizedBox(width: AppSpacing.xs),
                Expanded(
                  child: Text(
                    request.requesterDetails['full_name'] ?? 'Usuário',
                    style: context.textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Text(
                  request.createdAt.split('T').first,
                  style: context.textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
