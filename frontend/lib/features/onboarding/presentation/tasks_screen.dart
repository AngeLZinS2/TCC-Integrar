import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../shared/models/onboarding_task_model.dart';
import '../providers/onboarding_tasks_provider.dart';
import 'widgets/onboarding_task_card.dart';
import 'task_detail_sheet.dart';

/// Tarefas de integração.
///
/// A mesma tela serve o colaborador (vê a própria integração e o que lhe
/// foi atribuído), o gestor (a equipe) e o RH (a empresa) — quem filtra é
/// o backend, pelo papel de quem pediu.
class OnboardingTasksScreen extends ConsumerWidget {
  const OnboardingTasksScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tarefasAsync = ref.watch(onboardingTasksProvider);
    final filtro = ref.watch(taskFilterProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(onboardingTasksProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const AppSectionHeader(
                title: 'Tarefas de Integração',
                subtitle:
                    'Acompanhe o que cada pessoa precisa fazer para concluir a integração.',
              ),
              const SizedBox(height: AppSpacing.xl),
              _Filtros(filtro: filtro),
              const SizedBox(height: AppSpacing.lg),
              tarefasAsync.when(
                loading: () => Column(
                  children: List.generate(
                    4,
                    (_) => const Padding(
                      padding: EdgeInsets.only(bottom: AppSpacing.md),
                      child: AppSkeleton.card(height: 140),
                    ),
                  ),
                ),
                error: (erro, _) => AppErrorState(
                  message: 'Não foi possível carregar as tarefas.',
                  onRetry: () => ref.invalidate(onboardingTasksProvider),
                ),
                data: (resposta) {
                  final tarefas = resposta.results;
                  if (tarefas.isEmpty) {
                    return AppEmptyState(
                      icon: Icons.checklist_outlined,
                      title: 'Nenhuma tarefa',
                      description: _mensagemVazia(filtro),
                    );
                  }
                  return Column(
                    children: [
                      for (final tarefa in tarefas)
                        Padding(
                          padding: const EdgeInsets.only(bottom: AppSpacing.md),
                          child: OnboardingTaskCard(
                            task: tarefa,
                            onTap: () => _abrirDetalhe(context, ref, tarefa),
                            onToggle: tarefa.status == 'cancelled'
                                ? null
                                : () => _alternar(context, ref, tarefa),
                          ),
                        ),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// O vazio muda conforme o filtro: "nenhuma tarefa" sob o filtro de
  /// atrasadas é uma boa notícia, não uma lista vazia.
  String _mensagemVazia(TaskFilter filtro) {
    if (filtro.onlyOverdue) return 'Nada atrasado por aqui. Tudo em dia.';
    if (filtro.onlyMine) return 'Você não tem tarefas de integração atribuídas.';
    if (filtro.status == 'completed') return 'Nenhuma tarefa concluída ainda.';
    return 'Nenhuma tarefa de integração foi criada até agora.';
  }

  void _abrirDetalhe(
    BuildContext context,
    WidgetRef ref,
    OnboardingTaskModel tarefa,
  ) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => TaskDetailSheet(taskId: tarefa.id),
    ).then((_) => ref.invalidate(onboardingTasksProvider));
  }

  Future<void> _alternar(
    BuildContext context,
    WidgetRef ref,
    OnboardingTaskModel tarefa,
  ) async {
    final novo = tarefa.isDone ? 'pending' : 'completed';
    final messenger = ScaffoldMessenger.of(context);

    try {
      await ref
          .read(onboardingTasksRepositoryProvider)
          .changeStatus(tarefa.id, novo);
      ref.invalidate(onboardingTasksProvider);
      ref.invalidate(myOnboardingProvider);
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            novo == 'completed'
                ? 'Tarefa concluída.'
                : 'Tarefa reaberta.',
          ),
          backgroundColor: AppColors.success,
        ),
      );
    } catch (erro) {
      // A mensagem vem do backend ("Você não é o responsável por esta
      // tarefa") — é a única informação útil aqui.
      messenger.showSnackBar(
        SnackBar(
          content: Text(erro.toString().replaceFirst('Exception: ', '')),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }
}

class _Filtros extends ConsumerWidget {
  final TaskFilter filtro;

  const _Filtros({required this.filtro});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    void aplicar(TaskFilter novo) {
      ref.read(taskFilterProvider.notifier).state = novo;
    }

    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: [
        _chip(
          context,
          rotulo: 'Todas',
          ativo: filtro.status == null &&
              !filtro.onlyMine &&
              !filtro.onlyOverdue,
          aoTocar: () => aplicar(const TaskFilter()),
        ),
        _chip(
          context,
          rotulo: 'Minhas',
          ativo: filtro.onlyMine,
          aoTocar: () => aplicar(
            TaskFilter(onlyMine: !filtro.onlyMine, status: filtro.status),
          ),
        ),
        _chip(
          context,
          rotulo: 'Pendentes',
          ativo: filtro.status == 'pending',
          aoTocar: () => aplicar(
            filtro.status == 'pending'
                ? filtro.copyWith(clearStatus: true)
                : filtro.copyWith(status: 'pending'),
          ),
        ),
        _chip(
          context,
          rotulo: 'Concluídas',
          ativo: filtro.status == 'completed',
          aoTocar: () => aplicar(
            filtro.status == 'completed'
                ? filtro.copyWith(clearStatus: true)
                : filtro.copyWith(status: 'completed'),
          ),
        ),
        _chip(
          context,
          rotulo: 'Atrasadas',
          ativo: filtro.onlyOverdue,
          aoTocar: () => aplicar(
            filtro.copyWith(onlyOverdue: !filtro.onlyOverdue),
          ),
        ),
      ],
    );
  }

  Widget _chip(
    BuildContext context, {
    required String rotulo,
    required bool ativo,
    required VoidCallback aoTocar,
  }) {
    return Semantics(
      button: true,
      selected: ativo,
      label: 'Filtrar por $rotulo',
      child: FilterChip(
        label: Text(rotulo),
        selected: ativo,
        onSelected: (_) => aoTocar(),
        showCheckmark: false,
        selectedColor: AppColors.primary100,
        labelStyle: context.textTheme.bodySmall?.copyWith(
          color: ativo ? AppColors.primary700 : context.textSecondaryColor,
          fontWeight: ativo ? FontWeight.w600 : FontWeight.w500,
        ),
      ),
    );
  }
}
