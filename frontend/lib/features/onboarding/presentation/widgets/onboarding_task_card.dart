import 'package:flutter/material.dart';

import '../../../../app/theme.dart';
import '../../../../core/widgets/app_badge.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../shared/models/onboarding_task_model.dart';

/// Cartão de uma tarefa de integração.
///
/// O que precisa ser lido de relance: se está atrasada, de quem é a
/// integração e quem tem que executar. O resto é detalhe da tela cheia.
class OnboardingTaskCard extends StatelessWidget {
  final OnboardingTaskModel task;
  final VoidCallback? onTap;
  final VoidCallback? onToggle;
  final bool showEmployee;

  const OnboardingTaskCard({
    super.key,
    required this.task,
    this.onTap,
    this.onToggle,
    this.showEmployee = true,
  });

  @override
  Widget build(BuildContext context) {
    final atrasada = task.isOverdue;

    return Semantics(
      button: onTap != null,
      label: _descricaoParaLeitorDeTela(),
      child: AppCard(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (onToggle != null) _botaoConcluir(context),
                Expanded(
                  child: Text(
                    task.title,
                    style: context.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: context.textPrimaryColor,
                      decoration:
                          task.isDone ? TextDecoration.lineThrough : null,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                AppBadge(
                  label: atrasada ? 'Atrasada' : task.statusDisplay,
                  variant: _corDoStatus(atrasada),
                ),
              ],
            ),
            if (task.description.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                task.description,
                style: context.textTheme.bodySmall?.copyWith(
                  color: context.textSecondaryColor,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            const SizedBox(height: AppSpacing.md),
            Wrap(
              spacing: AppSpacing.md,
              runSpacing: AppSpacing.xs,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                if (showEmployee && task.employee != null)
                  _info(context, Icons.person_outline, task.employee!.fullName),
                _info(
                  context,
                  Icons.assignment_ind_outlined,
                  task.assignedTo?.fullName ?? 'Sem responsável',
                ),
                if (task.dueDate != null)
                  _info(
                    context,
                    Icons.event_outlined,
                    atrasada
                        ? '${_data(task.dueDate!)} · ${task.daysLate}d de atraso'
                        : _data(task.dueDate!),
                    destaque: atrasada,
                  ),
                if (task.commentCount > 0)
                  _info(
                    context,
                    Icons.chat_bubble_outline,
                    '${task.commentCount}',
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _botaoConcluir(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: AppSpacing.sm),
      child: Semantics(
        button: true,
        label: task.isDone
            ? 'Reabrir tarefa ${task.title}'
            : 'Concluir tarefa ${task.title}',
        child: InkWell(
          onTap: onToggle,
          borderRadius: BorderRadius.circular(20),
          child: Padding(
            padding: const EdgeInsets.all(2),
            child: Icon(
              task.isDone
                  ? Icons.check_circle
                  : Icons.radio_button_unchecked,
              size: 22,
              color: task.isDone
                  ? AppColors.success
                  : context.textSecondaryColor,
            ),
          ),
        ),
      ),
    );
  }

  Widget _info(
    BuildContext context,
    IconData icone,
    String texto, {
    bool destaque = false,
  }) {
    final cor = destaque ? AppColors.error : context.textSecondaryColor;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icone, size: 14, color: cor),
        const SizedBox(width: 4),
        Text(
          texto,
          style: context.textTheme.bodySmall?.copyWith(
            color: cor,
            fontWeight: destaque ? FontWeight.w600 : null,
          ),
        ),
      ],
    );
  }

  AppBadgeVariant _corDoStatus(bool atrasada) {
    if (atrasada) return AppBadgeVariant.error;
    switch (task.status) {
      case 'completed':
        return AppBadgeVariant.success;
      case 'in_progress':
        return AppBadgeVariant.info;
      case 'cancelled':
        return AppBadgeVariant.neutral;
      default:
        return AppBadgeVariant.warning;
    }
  }

  /// Uma frase completa para o leitor de tela, em vez dos fragmentos soltos
  /// que ele leria varrendo o cartão.
  String _descricaoParaLeitorDeTela() {
    final partes = <String>[task.title];
    if (task.isOverdue) {
      partes.add('atrasada há ${task.daysLate} dias');
    } else {
      partes.add(task.statusDisplay.toLowerCase());
    }
    if (task.assignedTo != null) {
      partes.add('responsável ${task.assignedTo!.fullName}');
    }
    return partes.join(', ');
  }

  static String _data(String iso) {
    final data = DateTime.tryParse(iso);
    if (data == null) return iso;
    return '${data.day.toString().padLeft(2, '0')}/'
        '${data.month.toString().padLeft(2, '0')}';
  }
}
