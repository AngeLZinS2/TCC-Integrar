import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_text_field.dart';
import '../providers/communications_provider.dart';

class NewCommunicationScreen extends ConsumerStatefulWidget {
  const NewCommunicationScreen({super.key});

  @override
  ConsumerState<NewCommunicationScreen> createState() => _NewCommunicationScreenState();
}

class _NewCommunicationScreenState extends ConsumerState<NewCommunicationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _contentController = TextEditingController();
  bool _isUrgent = false;
  bool _isLoading = false;

  @override
  void dispose() {
    _titleController.dispose();
    _contentController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);
    try {
      final repository = ref.read(communicationsRepositoryProvider);
      await repository.createAnnouncement(
        title: _titleController.text.trim(),
        content: _contentController.text.trim(),
        isUrgent: _isUrgent,
      );

      if (!mounted) return;
      ref.invalidate(communicationsListProvider);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Comunicado publicado com sucesso!'), backgroundColor: AppColors.success),
      );
      context.pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao publicar: $e'), backgroundColor: AppColors.error),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        title: const Text('Novo Comunicado'),
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
                    Text('Criar Comunicado Oficial', style: context.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: AppSpacing.sm),
                    Text('Publique informativos, regras e anúncios. Todos os colaboradores verão na sua timeline.', style: context.textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary)),
                    const SizedBox(height: AppSpacing.xl),
                    
                    AppTextField(
                      label: 'Título',
                      controller: _titleController,
                      hintText: 'Ex: Feriado Nacional',
                      validator: (val) => val == null || val.isEmpty ? 'Informe o título' : null,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    
                    AppTextField(
                      label: 'Conteúdo',
                      controller: _contentController,
                      hintText: 'Detalhe o comunicado aqui...',
                      maxLines: 8,
                      validator: (val) => val == null || val.isEmpty ? 'Informe o conteúdo' : null,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    
                    CheckboxListTile(
                      title: const Text('Marcar como Urgente'),
                      subtitle: const Text('Destaque o comunicado em vermelho'),
                      value: _isUrgent,
                      onChanged: (val) => setState(() => _isUrgent = val ?? false),
                      contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading,
                      activeColor: AppColors.error,
                    ),
                    
                    const SizedBox(height: AppSpacing.xxl),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        AppButton(text: 'Cancelar', variant: AppButtonVariant.outline, onPressed: () => context.pop()),
                        const SizedBox(width: AppSpacing.md),
                        AppButton(text: 'Publicar', isLoading: _isLoading, onPressed: _submit),
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
