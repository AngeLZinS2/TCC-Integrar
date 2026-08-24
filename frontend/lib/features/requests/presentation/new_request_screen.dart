import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/app_dropdown.dart';
import '../providers/requests_provider.dart';

class NewRequestScreen extends ConsumerStatefulWidget {
  const NewRequestScreen({super.key});

  @override
  ConsumerState<NewRequestScreen> createState() => _NewRequestScreenState();
}

class _NewRequestScreenState extends ConsumerState<NewRequestScreen> {
  final _formKey = GlobalKey<FormState>();
  final _subjectController = TextEditingController();
  final _descriptionController = TextEditingController();

  String _category = 'benefits';
  String _priority = 'normal';
  bool _isLoading = false;

  final _categories = const [
    AppDropdownOption(value: 'benefits', label: 'Benefícios (VT, VR, Plano de Saúde)'),
    AppDropdownOption(value: 'payroll', label: 'Folha de Pagamento / Ponto'),
    AppDropdownOption(value: 'vacation', label: 'Férias / Afastamentos'),
    AppDropdownOption(value: 'documents', label: 'Solicitação de Documentos'),
    AppDropdownOption(value: 'other', label: 'Outros'),
  ];

  final _priorities = const [
    AppDropdownOption(value: 'low', label: 'Baixa (Até 5 dias úteis)'),
    AppDropdownOption(value: 'normal', label: 'Normal (Até 3 dias úteis)'),
    AppDropdownOption(value: 'high', label: 'Alta (Até 24h)'),
  ];

  @override
  void dispose() {
    _subjectController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);
    try {
      final repository = ref.read(requestsRepositoryProvider);
      await repository.createRequest(
        category: _category,
        subject: _subjectController.text.trim(),
        description: _descriptionController.text.trim(),
        priority: _priority,
      );

      if (!mounted) return;
      ref.invalidate(requestsListProvider);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Solicitação criada com sucesso!'),
          backgroundColor: AppColors.success,
        ),
      );
      context.pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Erro ao criar solicitação: $e'),
          backgroundColor: AppColors.error,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        title: const Text('Nova Solicitação ao RH'),
        backgroundColor: context.surfaceColor,
        elevation: 0,
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.xxl),
            child: Container(
              padding: const EdgeInsets.all(AppSpacing.xxl),
              decoration: BoxDecoration(
                color: context.surfaceColor,
                borderRadius: BorderRadius.circular(AppSpacing.lg),
                border: Border.all(color: context.borderColor),
              ),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Preencha os detalhes do seu chamado',
                      style: context.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      'Seja claro e forneça o máximo de informações para agilizar o atendimento.',
                      style: context.textTheme.bodyMedium?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xl),
                    Row(
                      children: [
                        Expanded(
                          child: AppDropdown(
                            label: 'Categoria',
                            value: _category,
                            options: _categories,
                            onChanged: (val) => setState(() => _category = val!),
                          ),
                        ),
                        const SizedBox(width: AppSpacing.lg),
                        Expanded(
                          child: AppDropdown(
                            label: 'Prioridade',
                            value: _priority,
                            options: _priorities,
                            onChanged: (val) => setState(() => _priority = val!),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    AppTextField(
                      label: 'Assunto',
                      controller: _subjectController,
                      hintText: 'Ex: Dúvida sobre desconto no Vale Transporte',
                      validator: (val) => val == null || val.isEmpty ? 'Informe o assunto' : null,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    AppTextField(
                      label: 'Descrição',
                      controller: _descriptionController,
                      hintText: 'Descreva detalhadamente o que você precisa...',
                      maxLines: 5,
                      validator: (val) => val == null || val.isEmpty ? 'Informe a descrição' : null,
                    ),
                    const SizedBox(height: AppSpacing.xxl),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        AppButton(
                          text: 'Cancelar',
                          variant: AppButtonVariant.outline,
                          onPressed: () => context.pop(),
                        ),
                        const SizedBox(width: AppSpacing.md),
                        AppButton(
                          text: 'Abrir Solicitação',
                          isLoading: _isLoading,
                          onPressed: _submit,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
