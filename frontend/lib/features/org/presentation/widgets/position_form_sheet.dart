import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme.dart';
import '../../../../core/widgets/app_button.dart';
import '../../../../core/widgets/custom_text_field.dart';
import '../../models/org_models.dart';
import '../../providers/org_provider.dart';

/// Formulário de cargo. Devolve `true` quando salvou.
Future<bool?> showPositionFormSheet(
  BuildContext context,
  WidgetRef ref, {
  PositionModel? position,
  int? initialSectorId,
}) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: context.surfaceColor,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.lg)),
    ),
    builder: (_) => _PositionForm(position: position, initialSectorId: initialSectorId),
  );
}

class _PositionForm extends ConsumerStatefulWidget {
  final PositionModel? position;
  final int? initialSectorId;

  const _PositionForm({this.position, this.initialSectorId});

  @override
  ConsumerState<_PositionForm> createState() => _PositionFormState();
}

class _PositionFormState extends ConsumerState<_PositionForm> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _descriptionController;
  int? _sectorId;
  late bool _isActive;
  bool _isLoading = false;
  String? _error;

  bool get _isEdit => widget.position != null;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.position?.name ?? '');
    _descriptionController = TextEditingController(text: widget.position?.description ?? '');
    _sectorId = widget.position?.sectorId ?? widget.initialSectorId;
    _isActive = widget.position?.isActive ?? true;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_sectorId == null) {
      setState(() => _error = 'Escolha o setor ao qual este cargo pertence.');
      return;
    }
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final repository = ref.read(orgRepositoryProvider);
      if (_isEdit) {
        await repository.updatePosition(
          widget.position!.id,
          name: _nameController.text.trim(),
          description: _descriptionController.text.trim(),
          sectorId: _sectorId,
          isActive: _isActive,
        );
      } else {
        await repository.createPosition(
          name: _nameController.text.trim(),
          sectorId: _sectorId!,
          description: _descriptionController.text.trim(),
        );
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceAll('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sectorsAsync = ref.watch(sectorsProvider);

    return Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.xxl,
        right: AppSpacing.xxl,
        top: AppSpacing.xl,
        bottom: MediaQuery.of(context).viewInsets.bottom + AppSpacing.xxl,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: context.borderColor,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.xl),
            Text(
              _isEdit ? 'Editar cargo' : 'Novo cargo',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: context.textPrimaryColor,
              ),
            ),
            const SizedBox(height: AppSpacing.xl),
            CustomTextField(
              controller: _nameController,
              label: 'Nome',
              hint: 'Ex.: Desenvolvedor Júnior',
              prefixIcon: Icons.work_outline_rounded,
              autofocus: !_isEdit,
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Informe o nome do cargo.' : null,
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              'Setor',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: context.textSecondaryColor,
              ),
            ),
            const SizedBox(height: 6),
            sectorsAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) => Text(
                'Não foi possível carregar os setores.',
                style: TextStyle(fontSize: 12, color: context.textMutedColor),
              ),
              data: (paged) {
                if (paged.items.isEmpty) {
                  return const Text(
                    'Crie um setor antes de cadastrar cargos.',
                    style: TextStyle(fontSize: 12, color: AppColors.error),
                  );
                }
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                  decoration: BoxDecoration(
                    border: Border.all(color: context.borderColor),
                    borderRadius: BorderRadius.circular(AppRadius.md),
                  ),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<int?>(
                      value: paged.items.any((s) => s.id == _sectorId) ? _sectorId : null,
                      isExpanded: true,
                      hint: const Text('Escolha o setor'),
                      onChanged: (v) => setState(() => _sectorId = v),
                      items: paged.items
                          .map((s) => DropdownMenuItem<int?>(
                                value: s.id,
                                child: Text(s.name),
                              ))
                          .toList(),
                    ),
                  ),
                );
              },
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              controller: _descriptionController,
              label: 'Descrição',
              hint: 'Responsabilidades do cargo (opcional)',
              prefixIcon: Icons.notes_outlined,
              maxLines: 2,
            ),
            if (_isEdit) ...[
              const SizedBox(height: AppSpacing.sm),
              SwitchListTile(
                value: _isActive,
                onChanged: (v) => setState(() => _isActive = v),
                contentPadding: EdgeInsets.zero,
                dense: true,
                title: Text(
                  'Cargo ativo',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: context.textPrimaryColor,
                  ),
                ),
                subtitle: Text(
                  'Cargo inativo não aparece em novos cadastros, mas preserva o histórico.',
                  style: TextStyle(fontSize: 11.5, color: context.textSecondaryColor),
                ),
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: AppSpacing.md),
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: context.isDark
                      ? AppColors.errorDark.withValues(alpha: 0.25)
                      : AppColors.errorLight,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Text(
                  _error!,
                  style: TextStyle(
                    fontSize: 12.5,
                    color: context.isDark ? AppColors.errorDarkText : AppColors.errorText,
                  ),
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.xxl),
            AppButton(
              text: _isEdit ? 'Salvar alterações' : 'Criar cargo',
              icon: Icons.check_rounded,
              isLoading: _isLoading,
              fullWidth: true,
              onPressed: _submit,
            ),
          ],
        ),
      ),
    );
  }
}
