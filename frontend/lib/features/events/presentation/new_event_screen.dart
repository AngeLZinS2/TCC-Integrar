import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_text_field.dart';
import '../providers/events_provider.dart';

class NewEventScreen extends ConsumerStatefulWidget {
  const NewEventScreen({super.key});

  @override
  ConsumerState<NewEventScreen> createState() => _NewEventScreenState();
}

class _NewEventScreenState extends ConsumerState<NewEventScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  DateTime? _selectedDate;
  bool _isLoading = false;

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _selectDate(BuildContext context) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate ?? DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365 * 2)),
    );
    if (picked != null && picked != _selectedDate) {
      setState(() {
        _selectedDate = picked;
      });
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedDate == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, selecione uma data.'), backgroundColor: AppColors.error),
      );
      return;
    }

    setState(() => _isLoading = true);
    try {
      final repository = ref.read(eventsRepositoryProvider);
      final dateStr = "${_selectedDate!.year}-${_selectedDate!.month.toString().padLeft(2, '0')}-${_selectedDate!.day.toString().padLeft(2, '0')}";
      
      await repository.createEvent(
        title: _titleController.text.trim(),
        description: _descriptionController.text.trim(),
        date: dateStr,
      );

      if (!mounted) return;
      ref.invalidate(eventsListProvider);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Evento agendado com sucesso!'), backgroundColor: AppColors.success),
      );
      context.pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao agendar evento: $e'), backgroundColor: AppColors.error),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateStr = _selectedDate == null
        ? 'Selecione uma data'
        : "${_selectedDate!.day.toString().padLeft(2, '0')}/${_selectedDate!.month.toString().padLeft(2, '0')}/${_selectedDate!.year}";

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        title: const Text('Novo Evento'),
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
                    Text('Agendar Evento Corporativo', style: context.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: AppSpacing.sm),
                    Text('Festas, palestras, ou feriados que afetam a empresa toda.', style: context.textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary)),
                    const SizedBox(height: AppSpacing.xl),
                    
                    AppTextField(
                      label: 'Título do Evento',
                      controller: _titleController,
                      hintText: 'Ex: Confraternização de Fim de Ano',
                      validator: (val) => val == null || val.isEmpty ? 'Informe o título' : null,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    
                    Text('Data do Evento', style: context.textTheme.labelMedium?.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: AppSpacing.xs),
                    InkWell(
                      onTap: () => _selectDate(context),
                      child: Container(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        decoration: BoxDecoration(
                          border: Border.all(color: context.borderColor),
                          borderRadius: BorderRadius.circular(AppSpacing.sm),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(dateStr, style: context.textTheme.bodyMedium),
                            const Icon(Icons.calendar_today, size: 20, color: AppColors.textSecondary),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    
                    AppTextField(
                      label: 'Descrição Detalhada',
                      controller: _descriptionController,
                      hintText: 'Local, horário e detalhes importantes...',
                      maxLines: 5,
                      validator: (val) => val == null || val.isEmpty ? 'Informe a descrição' : null,
                    ),
                    
                    const SizedBox(height: AppSpacing.xxl),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        AppButton(text: 'Cancelar', variant: AppButtonVariant.outline, onPressed: () => context.pop()),
                        const SizedBox(width: AppSpacing.md),
                        AppButton(text: 'Agendar Evento', isLoading: _isLoading, onPressed: _submit),
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
