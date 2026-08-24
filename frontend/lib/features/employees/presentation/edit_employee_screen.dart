import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../org/providers/org_provider.dart';
import '../models/employee_model.dart';
import '../providers/employee_provider.dart';

/// Edição do cadastro de um colaborador pelo RH / admin da empresa.
class EditEmployeeScreen extends ConsumerWidget {
  final int employeeId;

  const EditEmployeeScreen({super.key, required this.employeeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final employeeAsync = ref.watch(employeeDetailProvider(employeeId));

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        backgroundColor: context.surfaceColor,
        foregroundColor: context.textPrimaryColor,
        elevation: 0,
        title: const Text('Editar Colaborador'),
      ),
      body: employeeAsync.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(AppSpacing.xxl),
          child: AppSkeleton.card(height: 400),
        ),
        error: (err, _) => AppErrorState(
          message: 'Não foi possível carregar este colaborador.',
          onRetry: () => ref.invalidate(employeeDetailProvider(employeeId)),
        ),
        data: (employee) => _EditForm(employee: employee),
      ),
    );
  }
}

class _EditForm extends ConsumerStatefulWidget {
  final EmployeeModel employee;

  const _EditForm({required this.employee});

  @override
  ConsumerState<_EditForm> createState() => _EditFormState();
}

class _EditFormState extends ConsumerState<_EditForm> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _phoneController;
  late final TextEditingController _registrationController;

  late String _role;
  int? _sectorId;
  int? _positionId;
  int? _managerId;
  DateTime? _hireDate;
  late bool _isSectorLeader;

  bool _isSaving = false;
  String? _error;

  EmployeeModel get _employee => widget.employee;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: _employee.fullName);
    _phoneController = TextEditingController(text: _employee.phone);
    _registrationController = TextEditingController(text: _employee.registrationNumber);
    _role = _employee.role;
    _sectorId = _employee.sectorId;
    _positionId = _employee.positionId;
    _managerId = _employee.managerId;
    _hireDate = _employee.hireDate;
    _isSectorLeader = _employee.isSectorLeader;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _registrationController.dispose();
    super.dispose();
  }

  Future<void> _pickHireDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _hireDate ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) setState(() => _hireDate = picked);
  }

  /// Troca de papel altera o que a pessoa enxerga e pode fazer no sistema —
  /// pede confirmação explícita antes de salvar.
  Future<bool> _confirmRoleChange(String novoLabel) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: context.surfaceColor,
        title: Text('Alterar papel?', style: TextStyle(color: context.textPrimaryColor)),
        content: Text(
          '${_employee.fullName} passará de "${_employee.roleDisplay}" para '
          '"$novoLabel".\n\nEssa alteração muda as permissões de acesso deste usuário.',
          style: TextStyle(color: context.textSecondaryColor, height: 1.45),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Confirmar alteração'),
          ),
        ],
      ),
    );
    return confirmado == true;
  }

  Future<void> _save(List<RoleOption> roles) async {
    if (!_formKey.currentState!.validate()) return;

    if (_role != _employee.role) {
      final label = roles.firstWhere(
        (r) => r.value == _role,
        orElse: () => RoleOption(value: _role, label: _role),
      ).label;
      if (!await _confirmRoleChange(label)) return;
    }

    setState(() {
      _isSaving = true;
      _error = null;
    });

    try {
      await ref.read(employeeRepositoryProvider).updateEmployee(
            _employee.id,
            fullName: _nameController.text.trim(),
            phone: _phoneController.text.trim(),
            registrationNumber: _registrationController.text.trim(),
            role: _role,
            sectorId: _sectorId,
            positionId: _positionId,
            managerId: _managerId,
            clearSector: _sectorId == null,
            clearPosition: _positionId == null,
            clearManager: _managerId == null,
            hireDate: _hireDate,
            isSectorLeader: _isSectorLeader,
          );
      ref.invalidate(employeeDetailProvider(_employee.id));
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${_nameController.text.trim()} atualizado.'),
          backgroundColor: AppColors.success,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.md)),
        ),
      );
      context.pop(true);
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceAll('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sectorsAsync = ref.watch(sectorsProvider);
    final rolesAsync = ref.watch(employeeRolesProvider);
    final managersAsync = ref.watch(employeeManagerOptionsProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.xxl),
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                AppCard(
                  padding: const EdgeInsets.all(AppSpacing.xxl),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const _GroupTitle('Identificação'),
                      const SizedBox(height: AppSpacing.lg),
                      CustomTextField(
                        controller: _nameController,
                        label: 'Nome completo',
                        prefixIcon: Icons.person_outline_rounded,
                        validator: (v) =>
                            (v == null || v.trim().isEmpty) ? 'Informe o nome.' : null,
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      _ReadOnlyField(
                        label: 'E-mail corporativo',
                        value: _employee.email,
                        hint: 'O e-mail é o login e não pode ser alterado.',
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      CustomTextField(
                        controller: _phoneController,
                        label: 'Telefone',
                        hint: '(11) 90000-0000',
                        prefixIcon: Icons.phone_outlined,
                        keyboardType: TextInputType.phone,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),

                AppCard(
                  padding: const EdgeInsets.all(AppSpacing.xxl),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const _GroupTitle('Dados profissionais'),
                      const SizedBox(height: AppSpacing.lg),
                      CustomTextField(
                        controller: _registrationController,
                        label: 'Matrícula',
                        hint: 'Identificação interna (opcional)',
                        prefixIcon: Icons.pin_outlined,
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      const _FieldLabel('Setor'),
                      sectorsAsync.when(
                        loading: () => const LinearProgressIndicator(),
                        error: (_, __) => const _LoadError('setores'),
                        data: (paged) => _Dropdown<int?>(
                          value: paged.items.any((s) => s.id == _sectorId) ? _sectorId : null,
                          hint: 'Sem setor definido',
                          onChanged: (v) => setState(() {
                            _sectorId = v;
                            _positionId = null; // cargo pertence ao setor
                            if (v == null) _isSectorLeader = false;
                          }),
                          items: [
                            const DropdownMenuItem<int?>(
                              value: null,
                              child: Text('Sem setor definido'),
                            ),
                            ...paged.items.map(
                              (s) => DropdownMenuItem<int?>(value: s.id, child: Text(s.name)),
                            ),
                          ],
                        ),
                      ),
                      if (_sectorId != null) ...[
                        const SizedBox(height: AppSpacing.lg),
                        const _FieldLabel('Cargo'),
                        Consumer(
                          builder: (context, ref, _) {
                            final positionsAsync = ref.watch(positionsProvider);
                            return positionsAsync.when(
                              loading: () => const LinearProgressIndicator(),
                              error: (_, __) => const _LoadError('cargos'),
                              data: (paged) {
                                final doSetor = paged.items
                                    .where((p) => p.sectorId == _sectorId)
                                    .toList();
                                return _Dropdown<int?>(
                                  value: doSetor.any((p) => p.id == _positionId)
                                      ? _positionId
                                      : null,
                                  hint: 'Sem cargo definido',
                                  onChanged: (v) => setState(() => _positionId = v),
                                  items: [
                                    const DropdownMenuItem<int?>(
                                      value: null,
                                      child: Text('Sem cargo definido'),
                                    ),
                                    ...doSetor.map(
                                      (p) => DropdownMenuItem<int?>(
                                        value: p.id,
                                        child: Text(p.name),
                                      ),
                                    ),
                                  ],
                                );
                              },
                            );
                          },
                        ),
                      ],
                      const SizedBox(height: AppSpacing.lg),
                      const _FieldLabel('Gestor'),
                      managersAsync.when(
                        loading: () => const LinearProgressIndicator(),
                        error: (_, __) => const _LoadError('gestores'),
                        data: (managers) => _Dropdown<int?>(
                          value: managers.any((m) => m.id == _managerId) ? _managerId : null,
                          hint: 'Sem gestor definido',
                          onChanged: (v) => setState(() => _managerId = v),
                          items: [
                            const DropdownMenuItem<int?>(
                              value: null,
                              child: Text('Sem gestor definido'),
                            ),
                            ...managers
                                .where((m) => m.id != _employee.id)
                                .map((m) => DropdownMenuItem<int?>(
                                      value: m.id,
                                      child: Text(m.fullName),
                                    )),
                          ],
                        ),
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      const _FieldLabel('Data de admissão'),
                      InkWell(
                        onTap: _pickHireDate,
                        borderRadius: BorderRadius.circular(AppRadius.md),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: AppSpacing.md,
                            vertical: 14,
                          ),
                          decoration: BoxDecoration(
                            border: Border.all(color: context.borderColor),
                            borderRadius: BorderRadius.circular(AppRadius.md),
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.event_outlined, size: 18, color: context.textMutedColor),
                              const SizedBox(width: AppSpacing.sm),
                              Text(
                                _hireDate == null
                                    ? 'Não informada'
                                    : '${_hireDate!.day.toString().padLeft(2, '0')}/'
                                        '${_hireDate!.month.toString().padLeft(2, '0')}/'
                                        '${_hireDate!.year}',
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w500,
                                  color: _hireDate == null
                                      ? context.textMutedColor
                                      : context.textPrimaryColor,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),

                AppCard(
                  padding: const EdgeInsets.all(AppSpacing.xxl),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const _GroupTitle('Acesso'),
                      const SizedBox(height: AppSpacing.lg),
                      const _FieldLabel('Papel'),
                      rolesAsync.when(
                        loading: () => const LinearProgressIndicator(),
                        error: (_, __) => const _LoadError('papéis'),
                        data: (roles) => _Dropdown<String>(
                          value: roles.any((r) => r.value == _role) ? _role : null,
                          hint: 'Escolha o papel',
                          onChanged: (v) => setState(() => _role = v ?? _role),
                          items: roles
                              .map((r) => DropdownMenuItem<String>(
                                    value: r.value,
                                    child: Text(r.label),
                                  ))
                              .toList(),
                        ),
                      ),
                      if (_role != _employee.role)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(
                                Icons.warning_amber_rounded,
                                size: 15,
                                color: context.isDark
                                    ? AppColors.warningDarkText
                                    : AppColors.warning,
                              ),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  'Essa alteração muda as permissões de acesso deste usuário.',
                                  style: TextStyle(
                                    fontSize: 11.5,
                                    height: 1.4,
                                    color: context.isDark
                                        ? AppColors.warningDarkText
                                        : AppColors.warningText,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      const SizedBox(height: AppSpacing.sm),
                      CheckboxListTile(
                        value: _isSectorLeader,
                        onChanged: _sectorId == null
                            ? null
                            : (v) => setState(() => _isSectorLeader = v ?? false),
                        controlAffinity: ListTileControlAffinity.leading,
                        contentPadding: EdgeInsets.zero,
                        dense: true,
                        title: Text(
                          'Líder do setor',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: context.textPrimaryColor,
                          ),
                        ),
                        subtitle: Text(
                          _sectorId == null
                              ? 'Defina um setor para habilitar esta opção.'
                              : 'Pode cadastrar treinamentos e materiais do próprio setor.',
                          style: TextStyle(fontSize: 11.5, color: context.textSecondaryColor),
                        ),
                      ),
                    ],
                  ),
                ),

                if (_error != null) ...[
                  const SizedBox(height: AppSpacing.lg),
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
                  text: 'Salvar alterações',
                  icon: Icons.check_rounded,
                  isLoading: _isSaving,
                  fullWidth: true,
                  size: AppButtonSize.lg,
                  onPressed: () => _save(rolesAsync.valueOrNull ?? const []),
                ),
                const SizedBox(height: AppSpacing.xxl),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Peças reutilizadas dentro do formulário ─────────────────────────────────

class _GroupTitle extends StatelessWidget {
  final String text;

  const _GroupTitle(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: TextStyle(
        fontSize: 15,
        fontWeight: FontWeight.w700,
        color: context.textPrimaryColor,
        letterSpacing: -0.2,
      ),
    );
  }
}

class _FieldLabel extends StatelessWidget {
  final String text;

  const _FieldLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: context.textSecondaryColor,
        ),
      ),
    );
  }
}

class _Dropdown<T> extends StatelessWidget {
  final T? value;
  final String hint;
  final ValueChanged<T?> onChanged;
  final List<DropdownMenuItem<T>> items;

  const _Dropdown({
    required this.value,
    required this.hint,
    required this.onChanged,
    required this.items,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: BoxDecoration(
        border: Border.all(color: context.borderColor),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<T>(
          value: value,
          isExpanded: true,
          hint: Text(hint),
          onChanged: onChanged,
          items: items,
        ),
      ),
    );
  }
}

class _ReadOnlyField extends StatelessWidget {
  final String label;
  final String value;
  final String hint;

  const _ReadOnlyField({required this.label, required this.value, required this.hint});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _FieldLabel(label),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 14),
          decoration: BoxDecoration(
            border: Border.all(color: context.borderColor),
            borderRadius: BorderRadius.circular(AppRadius.md),
            color: context.scaffoldBg,
          ),
          child: Row(
            children: [
              Icon(Icons.lock_outline_rounded, size: 17, color: context.textMutedColor),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 14, color: context.textSecondaryColor),
                ),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            hint,
            style: TextStyle(fontSize: 11.5, color: context.textMutedColor),
          ),
        ),
      ],
    );
  }
}

class _LoadError extends StatelessWidget {
  final String what;

  const _LoadError(this.what);

  @override
  Widget build(BuildContext context) {
    return Text(
      'Não foi possível carregar os $what.',
      style: TextStyle(fontSize: 12, color: context.textMutedColor),
    );
  }
}
