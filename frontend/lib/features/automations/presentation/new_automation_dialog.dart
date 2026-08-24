import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../../shared/models/automation_model.dart';
import '../providers/automations_provider.dart';

/// Formulário de uma automação.
///
/// Os selects vêm do catálogo da API. Manter uma cópia das opções aqui
/// deixaria o app oferecendo um gatilho que o backend recusa assim que
/// alguém mexesse no catálogo do servidor.
class NewAutomationDialog extends ConsumerStatefulWidget {
  const NewAutomationDialog({super.key});

  @override
  ConsumerState<NewAutomationDialog> createState() =>
      _NewAutomationDialogState();
}

class _NewAutomationDialogState extends ConsumerState<NewAutomationDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nome = TextEditingController();
  final _titulo = TextEditingController();
  final _mensagem = TextEditingController();

  String? _evento;
  String _acao = 'send_notification';
  String _alvo = 'employee';
  bool _salvando = false;
  String? _erro;

  @override
  void dispose() {
    _nome.dispose();
    _titulo.dispose();
    _mensagem.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final catalogoAsync = ref.watch(automationCatalogProvider);

    return AlertDialog(
      title: const Text('Nova Automação'),
      content: SizedBox(
        width: 480,
        child: catalogoAsync.when(
          loading: () => const SizedBox(
            height: 160,
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (_, __) => const SizedBox(
            height: 160,
            child: Center(
              child: Text('Não foi possível carregar as opções.'),
            ),
          ),
          data: (catalogo) => _formulario(catalogo),
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

  Widget _formulario(AutomationCatalog catalogo) {
    // Só as ações de aviso entram nesta primeira versão: onboarding e
    // treinamento exigem escolher template/curso, que é outro formulário.
    final acoesDeAviso = catalogo.actions
        .where((a) => a.value == 'send_notification' || a.value == 'send_email')
        .toList();

    return Form(
      key: _formKey,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CustomTextField(
              controller: _nome,
              label: 'Nome da automação',
              hint: 'Boas-vindas de admissão',
              validator: (v) => (v == null || v.trim().isEmpty)
                  ? 'Dê um nome para reconhecer esta regra depois.'
                  : null,
            ),
            const SizedBox(height: AppSpacing.lg),

            _rotulo('Quando acontecer'),
            DropdownButtonFormField<String>(
              initialValue: _evento,
              isExpanded: true,
              decoration: const InputDecoration(border: OutlineInputBorder()),
              hint: const Text('Escolha o evento'),
              items: [
                for (final evento in catalogo.events)
                  DropdownMenuItem(
                    value: evento.value,
                    child: Text(evento.label),
                  ),
              ],
              onChanged: (v) => setState(() => _evento = v),
              validator: (v) => v == null ? 'Escolha o evento.' : null,
            ),
            const SizedBox(height: AppSpacing.lg),

            _rotulo('Então'),
            DropdownButtonFormField<String>(
              initialValue: _acao,
              isExpanded: true,
              decoration: const InputDecoration(border: OutlineInputBorder()),
              items: [
                for (final acao in acoesDeAviso)
                  DropdownMenuItem(value: acao.value, child: Text(acao.label)),
              ],
              onChanged: (v) => setState(() => _acao = v ?? _acao),
            ),
            const SizedBox(height: AppSpacing.md),

            _rotulo('Para'),
            DropdownButtonFormField<String>(
              initialValue: _alvo,
              isExpanded: true,
              decoration: const InputDecoration(border: OutlineInputBorder()),
              items: [
                for (final alvo in catalogo.targets)
                  DropdownMenuItem(value: alvo.value, child: Text(alvo.label)),
              ],
              onChanged: (v) => setState(() => _alvo = v ?? _alvo),
            ),
            const SizedBox(height: AppSpacing.lg),

            CustomTextField(
              controller: _titulo,
              label: 'Título do aviso',
              hint: 'Bem-vindo(a) ao time!',
            ),
            const SizedBox(height: AppSpacing.md),
            CustomTextField(
              controller: _mensagem,
              label: 'Mensagem',
              hint: 'Olá, {employee_name}! Sua integração começou.',
              maxLines: 3,
              validator: (v) => (v == null || v.trim().isEmpty)
                  ? 'Escreva a mensagem que será enviada.'
                  : null,
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              'Use {employee_name} para inserir o nome da pessoa.',
              style: context.textTheme.bodySmall?.copyWith(
                color: context.textMutedColor,
              ),
            ),

            if (_erro != null) ...[
              const SizedBox(height: AppSpacing.md),
              Text(
                _erro!,
                style: context.textTheme.bodySmall
                    ?.copyWith(color: AppColors.error),
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

  Future<void> _salvar() async {
    if (!_formKey.currentState!.validate()) return;

    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    setState(() {
      _salvando = true;
      _erro = null;
    });

    try {
      await ref.read(automationsRepositoryProvider).createRule(
            name: _nome.text.trim(),
            triggerEvent: _evento!,
            actions: [
              AutomationAction(
                actionType: _acao,
                target: _alvo,
                config: {
                  if (_titulo.text.trim().isNotEmpty)
                    'title': _titulo.text.trim(),
                  'message': _mensagem.text.trim(),
                },
              ),
            ],
          );
      navigator.pop();
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Automação criada.'),
          backgroundColor: AppColors.success,
        ),
      );
    } catch (erro) {
      setState(() => _erro = erro.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _salvando = false);
    }
  }
}
