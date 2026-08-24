import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../shared/models/automation_model.dart';
import '../providers/automations_provider.dart';
import 'new_automation_dialog.dart';

/// Automações da empresa.
///
/// Cada regra é lida como uma frase: "quando X acontecer, se Y, faça Z" —
/// é assim que quem configura pensa, e a tela segue essa ordem.
class AutomationsScreen extends ConsumerWidget {
  const AutomationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final regrasAsync = ref.watch(automationRulesProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(automationRulesProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Automações',
                subtitle:
                    'Regras que rodam sozinhas quando algo acontece — admissão, conclusão de treinamento, publicação de documento.',
                trailing: AppButton(
                  text: 'Nova Automação',
                  icon: Icons.add,
                  size: AppButtonSize.sm,
                  onPressed: () => _abrirFormulario(context, ref),
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              regrasAsync.when(
                loading: () => Column(
                  children: List.generate(
                    3,
                    (_) => const Padding(
                      padding: EdgeInsets.only(bottom: AppSpacing.md),
                      child: AppSkeleton.card(height: 130),
                    ),
                  ),
                ),
                error: (_, __) => AppErrorState(
                  message: 'Não foi possível carregar as automações.',
                  onRetry: () => ref.invalidate(automationRulesProvider),
                ),
                data: (resposta) {
                  final regras = resposta.results;
                  if (regras.isEmpty) {
                    return AppEmptyState(
                      icon: Icons.bolt_outlined,
                      title: 'Nenhuma automação',
                      description:
                          'Crie regras para o sistema agir sozinho — por exemplo, atribuir o treinamento de segurança a todo desenvolvedor admitido.',
                      actionText: 'Nova Automação',
                      onAction: () => _abrirFormulario(context, ref),
                    );
                  }
                  return Column(
                    children: [
                      for (final regra in regras)
                        Padding(
                          padding: const EdgeInsets.only(bottom: AppSpacing.md),
                          child: _AutomationCard(rule: regra),
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

  void _abrirFormulario(BuildContext context, WidgetRef ref) {
    showDialog<void>(
      context: context,
      builder: (_) => const NewAutomationDialog(),
    ).then((_) => ref.invalidate(automationRulesProvider));
  }
}

class _AutomationCard extends ConsumerWidget {
  final AutomationRule rule;

  const _AutomationCard({required this.rule});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  rule.name,
                  style: context.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: context.textPrimaryColor,
                  ),
                ),
              ),
              AppBadge(
                label: rule.isActive ? 'Ativa' : 'Pausada',
                variant: rule.isActive
                    ? AppBadgeVariant.success
                    : AppBadgeVariant.neutral,
              ),
              const SizedBox(width: AppSpacing.sm),
              Semantics(
                label: rule.isActive
                    ? 'Pausar automação ${rule.name}'
                    : 'Ativar automação ${rule.name}',
                child: Switch(
                  value: rule.isActive,
                  onChanged: (valor) => _alternar(context, ref, valor),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),

          // A regra lida como frase, na ordem em que quem configura pensa.
          _passo(
            context,
            Icons.play_circle_outline,
            'Quando',
            rule.triggerEventDisplay,
          ),
          if (rule.conditions.isNotEmpty)
            _passo(
              context,
              Icons.filter_alt_outlined,
              'Se',
              rule.conditions
                  .map((c) => '${c.fieldDisplay} ${c.operator} ${c.value}')
                  .join(' e '),
            ),
          _passo(
            context,
            Icons.bolt_outlined,
            'Então',
            rule.actions
                .map((a) => '${a.actionTypeDisplay} → ${a.targetDisplay}')
                .join(' · '),
          ),

          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Text(
                '${rule.runCount} execução(ões)',
                style: context.textTheme.bodySmall?.copyWith(
                  color: context.textMutedColor,
                ),
              ),
              const Spacer(),
              TextButton.icon(
                icon: const Icon(Icons.history, size: 16),
                label: const Text('Histórico'),
                onPressed: () => _verHistorico(context, ref),
              ),
              Semantics(
                button: true,
                label: 'Excluir automação ${rule.name}',
                child: IconButton(
                  icon: const Icon(Icons.delete_outline, size: 18),
                  color: AppColors.error,
                  tooltip: 'Excluir',
                  onPressed: () => _confirmarExclusao(context, ref),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _passo(
    BuildContext context,
    IconData icone,
    String rotulo,
    String texto,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icone, size: 15, color: AppColors.primary),
          const SizedBox(width: AppSpacing.sm),
          Text(
            '$rotulo ',
            style: context.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w600,
              color: context.textSecondaryColor,
            ),
          ),
          Expanded(
            child: Text(
              texto,
              style: context.textTheme.bodySmall?.copyWith(
                color: context.textPrimaryColor,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _alternar(
    BuildContext context,
    WidgetRef ref,
    bool ativa,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref
          .read(automationsRepositoryProvider)
          .toggleActive(rule.id, ativa);
      ref.invalidate(automationRulesProvider);
    } catch (erro) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(erro.toString().replaceFirst('Exception: ', '')),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }

  void _verHistorico(BuildContext context, WidgetRef ref) {
    showDialog<void>(
      context: context,
      builder: (_) => _RunsDialog(rule: rule),
    );
  }

  Future<void> _confirmarExclusao(BuildContext context, WidgetRef ref) async {
    final messenger = ScaffoldMessenger.of(context);
    final confirmou = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Excluir automação?'),
        content: Text(
          '"${rule.name}" deixará de rodar e o histórico de execuções será apagado. '
          'Para apenas suspendê-la, use o botão de pausa.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Excluir'),
          ),
        ],
      ),
    );
    if (confirmou != true) return;

    try {
      await ref.read(automationsRepositoryProvider).deleteRule(rule.id);
      ref.invalidate(automationRulesProvider);
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Automação excluída.'),
          backgroundColor: AppColors.success,
        ),
      );
    } catch (_) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Não foi possível excluir a automação.'),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }
}

class _RunsDialog extends ConsumerWidget {
  final AutomationRule rule;

  const _RunsDialog({required this.rule});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final execucoesAsync = ref.watch(automationRunsProvider(rule.id));

    return AlertDialog(
      title: Text('Histórico · ${rule.name}'),
      content: SizedBox(
        width: 520,
        height: 400,
        child: execucoesAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => AppErrorState(
            message: 'Não foi possível carregar o histórico.',
            onRetry: () => ref.invalidate(automationRunsProvider(rule.id)),
          ),
          data: (execucoes) {
            if (execucoes.isEmpty) {
              return const AppEmptyState(
                icon: Icons.history,
                title: 'Nenhuma execução',
                description:
                    'Esta automação ainda não foi acionada por nenhum evento.',
              );
            }
            return ListView.separated(
              itemCount: execucoes.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final execucao = execucoes[i];
                return ListTile(
                  dense: true,
                  leading: Icon(
                    execucao.failed
                        ? Icons.error_outline
                        : execucao.status == 'skipped'
                            ? Icons.remove_circle_outline
                            : Icons.check_circle_outline,
                    size: 18,
                    color: execucao.failed
                        ? AppColors.error
                        : execucao.status == 'skipped'
                            ? context.textMutedColor
                            : AppColors.success,
                  ),
                  title: Text(
                    execucao.subjectLabel.isEmpty
                        ? execucao.statusDisplay
                        : '${execucao.statusDisplay} · ${execucao.subjectLabel}',
                    style: context.textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  subtitle: Text(
                    execucao.detail,
                    style: context.textTheme.bodySmall?.copyWith(
                      color: context.textSecondaryColor,
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Fechar'),
        ),
      ],
    );
  }
}
