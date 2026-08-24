import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme.dart';
import '../../../../core/widgets/app_button.dart';
import '../../../../core/widgets/custom_text_field.dart';
import '../../models/org_models.dart';
import '../../providers/org_provider.dart';

/// Formulário de setor em bottom sheet — criar e editar usam a mesma tela,
/// já que os campos são idênticos e a diferença é só o verbo da chamada.
///
/// Devolve `true` quando salvou.
Future<bool?> showSectorFormSheet(
  BuildContext context,
  WidgetRef ref, {
  SectorModel? sector,
}) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: context.surfaceColor,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.lg)),
    ),
    builder: (_) => _SectorForm(sector: sector),
  );
}

class _SectorForm extends ConsumerStatefulWidget {
  final SectorModel? sector;

  const _SectorForm({this.sector});

  @override
  ConsumerState<_SectorForm> createState() => _SectorFormState();
}

class _SectorFormState extends ConsumerState<_SectorForm> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _descriptionController;
  int? _managerId;
  late bool _isActive;
  bool _isLoading = false;
  String? _error;

  bool get _isEdit => widget.sector != null;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.sector?.name ?? '');
    _descriptionController = TextEditingController(text: widget.sector?.description ?? '');
    _managerId = widget.sector?.managerId;
    _isActive = widget.sector?.isActive ?? true;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final repository = ref.read(orgRepositoryProvider);
      if (_isEdit) {
        await repository.updateSector(
          widget.sector!.id,
          name: _nameController.text.trim(),
          description: _descriptionController.text.trim(),
          managerId: _managerId,
          clearManager: _managerId == null,
          isActive: _isActive,
        );
      } else {
        await repository.createSector(
          name: _nameController.text.trim(),
          description: _descriptionController.text.trim(),
          managerId: _managerId,
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
    final managersAsync = ref.watch(managerOptionsProvider);

    return Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.xxl,
        right: AppSpacing.xxl,
        top: AppSpacing.xl,
        // Levanta o formulário acima do teclado.
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
              _isEdit ? 'Editar setor' : 'Novo setor',
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
              hint: 'Ex.: Tecnologia da Informação',
              prefixIcon: Icons.corporate_fare_rounded,
              autofocus: !_isEdit,
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Informe o nome do setor.' : null,
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              controller: _descriptionController,
              label: 'Descrição',
              hint: 'O que este setor faz (opcional)',
              prefixIcon: Icons.notes_outlined,
              maxLines: 2,
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              'Gestor responsável',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: context.textSecondaryColor,
              ),
            ),
            const SizedBox(height: 6),
            managersAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) => Text(
                'Não foi possível carregar os gestores.',
                style: TextStyle(fontSize: 12, color: context.textMutedColor),
              ),
              data: (managers) => Container(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                decoration: BoxDecoration(
                  border: Border.all(color: context.borderColor),
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<int?>(
                    value: managers.any((m) => m.id == _managerId) ? _managerId : null,
                    isExpanded: true,
                    hint: const Text('Sem gestor definido'),
                    onChanged: (v) => setState(() => _managerId = v),
                    items: [
                      const DropdownMenuItem<int?>(
                        value: null,
                        child: Text('Sem gestor definido'),
                      ),
                      ...managers.map(
                        (m) => DropdownMenuItem<int?>(value: m.id, child: Text(m.fullName)),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            if (managersAsync.valueOrNull?.isEmpty ?? false)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  'Nenhum gestor disponível ainda. Defina o papel "Gestor" para '
                  'alguém em Colaboradores.',
                  style: TextStyle(fontSize: 11.5, color: context.textMutedColor),
                ),
              ),
            if (_isEdit) ...[
              const SizedBox(height: AppSpacing.sm),
              SwitchListTile(
                value: _isActive,
                onChanged: (v) => setState(() => _isActive = v),
                contentPadding: EdgeInsets.zero,
                dense: true,
                title: Text(
                  'Setor ativo',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: context.textPrimaryColor,
                  ),
                ),
                subtitle: Text(
                  'Setor inativo não aparece em novos cadastros, mas preserva o histórico.',
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
              text: _isEdit ? 'Salvar alterações' : 'Criar setor',
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
