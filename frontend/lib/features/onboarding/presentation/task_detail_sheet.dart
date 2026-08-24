import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../shared/models/onboarding_task_model.dart';
import '../../auth/providers/auth_provider.dart';
import '../providers/onboarding_tasks_provider.dart';

/// Detalhe de uma tarefa, com o andamento.
///
/// Painel em vez de rota própria: a pessoa está varrendo a lista e quer
/// comentar ou concluir sem perder o lugar em que estava.
class TaskDetailSheet extends ConsumerStatefulWidget {
  final int taskId;

  const TaskDetailSheet({super.key, required this.taskId});

  @override
  ConsumerState<TaskDetailSheet> createState() => _TaskDetailSheetState();
}

class _TaskDetailSheetState extends ConsumerState<TaskDetailSheet> {
  final _comentario = TextEditingController();
  bool _interno = false;
  bool _enviando = false;

  @override
  void dispose() {
    _comentario.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tarefaAsync = ref.watch(onboardingTaskDetailProvider(widget.taskId));

    return DraggableScrollableSheet(
      initialChildSize: 0.75,
      minChildSize: 0.4,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: context.cardColor,
            borderRadius: const BorderRadius.vertical(
              top: Radius.circular(AppRadius.xl),
            ),
          ),
          child: tarefaAsync.when(
            loading: () => const Padding(
              padding: EdgeInsets.all(AppSpacing.xxl),
              child: AppSkeleton.card(height: 240),
            ),
            error: (_, __) => Padding(
              padding: const EdgeInsets.all(AppSpacing.xxl),
              child: AppErrorState(
                message: 'Não foi possível carregar a tarefa.',
                onRetry: () =>
                    ref.invalidate(onboardingTaskDetailProvider(widget.taskId)),
              ),
            ),
            data: (tarefa) => _conteudo(tarefa, scrollController),
          ),
        );
      },
    );
  }

  Widget _conteudo(OnboardingTaskModel tarefa, ScrollController controller) {
    final user = ref.watch(authNotifierProvider).user;
    final souResponsavel = tarefa.assignedToId == user?.id;
    final podeGerenciar = user?.managesCompany ?? false;
    final podeMudarStatus =
        (souResponsavel || podeGerenciar) && tarefa.status != 'cancelled';

    return ListView(
      controller: controller,
      padding: const EdgeInsets.all(AppSpacing.xxl),
      children: [
        Center(
          child: Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: context.borderColor,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                tarefa.title,
                style: context.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: context.textPrimaryColor,
                ),
              ),
            ),
            AppBadge(
              label: tarefa.isOverdue ? 'Atrasada' : tarefa.statusDisplay,
              variant: tarefa.isOverdue
                  ? AppBadgeVariant.error
                  : tarefa.isDone
                      ? AppBadgeVariant.success
                      : AppBadgeVariant.warning,
            ),
          ],
        ),
        if (tarefa.description.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          Text(
            tarefa.description,
            style: context.textTheme.bodyMedium?.copyWith(
              color: context.textSecondaryColor,
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.xl),
        _linha(
          Icons.person_outline,
          'Integração de',
          tarefa.employee?.fullName ?? '—',
        ),
        _linha(
          Icons.assignment_ind_outlined,
          'Responsável',
          tarefa.assignedTo?.fullName ?? 'Sem responsável',
        ),
        if (tarefa.dueDate != null)
          _linha(
            Icons.event_outlined,
            'Prazo',
            tarefa.isOverdue
                ? '${_data(tarefa.dueDate!)} · ${tarefa.daysLate} dia(s) de atraso'
                : _data(tarefa.dueDate!),
          ),
        _linha(Icons.flag_outlined, 'Prioridade', tarefa.priorityDisplay),

        if (podeMudarStatus) ...[
          const SizedBox(height: AppSpacing.xl),
          Row(
            children: [
              Expanded(
                child: AppButton(
                  text: tarefa.isDone ? 'Reabrir' : 'Concluir',
                  icon: tarefa.isDone ? Icons.undo : Icons.check,
                  variant: tarefa.isDone
                      ? AppButtonVariant.secondary
                      : AppButtonVariant.primary,
                  onPressed: () => _mudarStatus(
                    tarefa,
                    tarefa.isDone ? 'pending' : 'completed',
                  ),
                ),
              ),
              if (!tarefa.isDone && tarefa.status != 'in_progress') ...[
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: AppButton(
                    text: 'Em andamento',
                    variant: AppButtonVariant.secondary,
                    onPressed: () => _mudarStatus(tarefa, 'in_progress'),
                  ),
                ),
              ],
            ],
          ),
        ],

        const SizedBox(height: AppSpacing.xxl),
        Text(
          'Andamento',
          style: context.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w600,
            color: context.textPrimaryColor,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        if (tarefa.comments.isEmpty)
          Text(
            'Nenhum comentário ainda.',
            style: context.textTheme.bodySmall?.copyWith(
              color: context.textSecondaryColor,
            ),
          )
        else
          for (final comentario in tarefa.comments) _comentarioTile(comentario),

        const SizedBox(height: AppSpacing.lg),
        TextField(
          controller: _comentario,
          maxLines: 3,
          decoration: const InputDecoration(
            hintText: 'Escreva um comentário…',
            border: OutlineInputBorder(),
          ),
        ),
        if (podeGerenciar)
          CheckboxListTile(
            value: _interno,
            onChanged: (v) => setState(() => _interno = v ?? false),
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
            title: Text(
              'Nota interna',
              style: context.textTheme.bodySmall,
            ),
            subtitle: Text(
              'Visível apenas para RH e gestão — o colaborador não vê.',
              style: context.textTheme.bodySmall?.copyWith(
                color: context.textSecondaryColor,
              ),
            ),
          ),
        const SizedBox(height: AppSpacing.md),
        AppButton(
          text: 'Comentar',
          isLoading: _enviando,
          onPressed: _enviando ? null : () => _comentar(tarefa),
        ),
        const SizedBox(height: AppSpacing.xxl),
      ],
    );
  }

  Widget _comentarioTile(TaskComment comentario) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: comentario.isInternal
            ? AppColors.warningLight.withValues(alpha: context.isDark ? 0.1 : 1)
            : context.scaffoldBg,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: context.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                comentario.authorName,
                style: context.textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: context.textPrimaryColor,
                ),
              ),
              if (comentario.isInternal) ...[
                const SizedBox(width: AppSpacing.sm),
                const AppBadge(
                  label: 'Interno',
                  variant: AppBadgeVariant.warning,
                ),
              ],
            ],
          ),
          const SizedBox(height: 4),
          Text(
            comentario.message,
            style: context.textTheme.bodySmall?.copyWith(
              color: context.textSecondaryColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _linha(IconData icone, String rotulo, String valor) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        children: [
          Icon(icone, size: 16, color: context.textSecondaryColor),
          const SizedBox(width: AppSpacing.sm),
          Text(
            '$rotulo: ',
            style: context.textTheme.bodySmall?.copyWith(
              color: context.textSecondaryColor,
            ),
          ),
          Expanded(
            child: Text(
              valor,
              style: context.textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: context.textPrimaryColor,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _mudarStatus(OnboardingTaskModel tarefa, String novo) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref
          .read(onboardingTasksRepositoryProvider)
          .changeStatus(tarefa.id, novo);
      ref.invalidate(onboardingTaskDetailProvider(widget.taskId));
      ref.invalidate(onboardingTasksProvider);
      ref.invalidate(myOnboardingProvider);
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Tarefa atualizada.'),
          backgroundColor: AppColors.success,
        ),
      );
    } catch (erro) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(erro.toString().replaceFirst('Exception: ', '')),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }

  Future<void> _comentar(OnboardingTaskModel tarefa) async {
    final texto = _comentario.text.trim();
    if (texto.isEmpty) return;

    final messenger = ScaffoldMessenger.of(context);
    setState(() => _enviando = true);
    try {
      await ref.read(onboardingTasksRepositoryProvider).addComment(
            tarefa.id,
            texto,
            isInternal: _interno,
          );
      _comentario.clear();
      setState(() => _interno = false);
      ref.invalidate(onboardingTaskDetailProvider(widget.taskId));
    } catch (erro) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(erro.toString().replaceFirst('Exception: ', '')),
          backgroundColor: AppColors.error,
        ),
      );
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  static String _data(String iso) {
    final data = DateTime.tryParse(iso);
    if (data == null) return iso;
    return '${data.day.toString().padLeft(2, '0')}/'
        '${data.month.toString().padLeft(2, '0')}/${data.year}';
  }
}
