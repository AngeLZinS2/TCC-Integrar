import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../directory/models/directory_entry_model.dart';
import '../../directory/providers/directory_provider.dart';
import '../providers/onboarding_tasks_provider.dart';

/// Criar uma tarefa de integração.
///
/// Dois campos de pessoa, e eles NÃO são a mesma coisa: "de quem é a
/// integração" e "quem executa". Confundir os dois é o erro que o checklist
/// antigo não conseguia nem representar — por isso os rótulos dizem
/// exatamente isso, em vez de "colaborador" e "responsável".
class NewTaskDialog extends ConsumerStatefulWidget {
  /// Quando vem preenchido, a tarefa já nasce para esta pessoa — usado ao
  /// abrir o formulário de dentro da integração de alguém.
  final int? employeeId;

  const NewTaskDialog({super.key, this.employeeId});

  @override
  ConsumerState<NewTaskDialog> createState() => _NewTaskDialogState();
}

class _NewTaskDialogState extends ConsumerState<NewTaskDialog> {
  final _formKey = GlobalKey<FormState>();
  final _titulo = TextEditingController();
  final _descricao = TextEditingController();

  int? _employeeId;
  int? _assignedToId;
  String _prioridade = 'normal';
  DateTime? _prazo;
  bool _salvando = false;
  String? _erro;

  @override
  void initState() {
    super.initState();
    _employeeId = widget.employeeId;
  }

  @override
  void dispose() {
    _titulo.dispose();
    _descricao.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pessoasAsync = ref.watch(directoryListProvider);

    return AlertDialog(
      title: const Text('Nova Tarefa de Integração'),
      content: SizedBox(
        width: 460,
        child: pessoasAsync.when(
          loading: () => const SizedBox(
            height: 140,
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (_, __) => const SizedBox(
            height: 140,
            child: Center(child: Text('Não foi possível carregar as pessoas.')),
          ),
          data: (pessoas) => _formulario(pessoas),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _salvando ? null : () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        AppButton(
          text: 'Criar',
          isLoading: _salvando,
          size: AppButtonSize.sm,
          onPressed: _salvando ? null : _salvar,
        ),
      ],
    );
  }

  Widget _formulario(List<DirectoryEntryModel> pessoas) {
    return Form(
      key: _formKey,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CustomTextField(
              controller: _titulo,
              label: 'O que precisa ser feito',
              hint: 'Apresentar a equipe',
              validator: (v) => (v == null || v.trim().isEmpty)
                  ? 'Descreva a tarefa em uma linha.'
                  : null,
            ),
            const SizedBox(height: AppSpacing.lg),

            _rotulo('De quem é a integração'),
            DropdownButtonFormField<int>(
              initialValue: _employeeId,
              isExpanded: true,
              decoration: const InputDecoration(border: OutlineInputBorder()),
              hint: const Text('Escolha o colaborador'),
              items: [
                for (final p in pessoas)
                  DropdownMenuItem(
                    value: p.id,
                    child: Text(
                      p.sectorName == null
                          ? p.fullName
                          : '${p.fullName} · ${p.sectorName}',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: (v) => setState(() => _employeeId = v),
              validator: (v) =>
                  v == null ? 'Diga de quem é esta integração.' : null,
            ),
            const SizedBox(height: AppSpacing.lg),

            _rotulo('Quem executa'),
            DropdownButtonFormField<int>(
              initialValue: _assignedToId,
              isExpanded: true,
              decoration: const InputDecoration(border: OutlineInputBorder()),
              hint: const Text('Deixe em branco para definir depois'),
              items: [
                for (final p in pessoas)
                  DropdownMenuItem(
                    value: p.id,
                    child: Text(p.fullName, overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: (v) => setState(() => _assignedToId = v),
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              'Costuma ser outra pessoa: "criar acessos" é do RH, '
              '"enviar documentos" é do próprio colaborador.',
              style: context.textTheme.bodySmall?.copyWith(
                color: context.textMutedColor,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _rotulo('Prazo'),
                      OutlinedButton.icon(
                        icon: const Icon(Icons.event_outlined, size: 16),
                        label: Text(
                          _prazo == null
                              ? 'Sem prazo'
                              : '${_prazo!.day.toString().padLeft(2, '0')}/'
                                  '${_prazo!.month.toString().padLeft(2, '0')}/'
                                  '${_prazo!.year}',
                        ),
                        onPressed: _escolherPrazo,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _rotulo('Prioridade'),
                      DropdownButtonFormField<String>(
                        initialValue: _prioridade,
                        isExpanded: true,
                        decoration: const InputDecoration(
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(value: 'low', child: Text('Baixa')),
                          DropdownMenuItem(
                            value: 'normal',
                            child: Text('Normal'),
                          ),
                          DropdownMenuItem(value: 'high', child: Text('Alta')),
                          DropdownMenuItem(
                            value: 'urgent',
                            child: Text('Urgente'),
                          ),
                        ],
                        onChanged: (v) =>
                            setState(() => _prioridade = v ?? _prioridade),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),

            CustomTextField(
              controller: _descricao,
              label: 'Detalhes (opcional)',
              maxLines: 3,
            ),

            if (_erro != null) ...[
              const SizedBox(height: AppSpacing.md),
              Text(
                _erro!,
                style:
                    context.textTheme.bodySmall?.copyWith(color: AppColors.error),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _rotulo(String texto) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: Text(
        texto,
        style: context.textTheme.bodySmall?.copyWith(
          fontWeight: FontWeight.w600,
          color: context.textSecondaryColor,
        ),
      ),
    );
  }

  Future<void> _escolherPrazo() async {
    final hoje = DateTime.now();
    final escolhido = await showDatePicker(
      context: context,
      initialDate: _prazo ?? hoje,
      firstDate: hoje.subtract(const Duration(days: 365)),
      lastDate: hoje.add(const Duration(days: 365 * 2)),
    );
    if (escolhido != null) setState(() => _prazo = escolhido);
  }

  Future<void> _salvar() async {
    if (!_formKey.currentState!.validate()) return;

    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    setState(() {
      _salvando = true;
      _erro = null;
    });

    try {
      await ref.read(onboardingTasksRepositoryProvider).createTask(
            title: _titulo.text.trim(),
            employeeId: _employeeId!,
            description: _descricao.text.trim(),
            assignedToId: _assignedToId,
            dueDate: _prazo == null
                ? null
                : '${_prazo!.year}-'
                    '${_prazo!.month.toString().padLeft(2, '0')}-'
                    '${_prazo!.day.toString().padLeft(2, '0')}',
            priority: _prioridade,
          );
      ref.invalidate(onboardingTasksProvider);
      navigator.pop();
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Tarefa criada.'),
          backgroundColor: AppColors.success,
        ),
      );
    } catch (erro) {
      // O backend explica o motivo — "Você só gerencia a integração de quem
      // está na sua equipe" é exatamente o que o gestor precisa ler.
      setState(() => _erro = erro.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _salvando = false);
    }
  }
}
