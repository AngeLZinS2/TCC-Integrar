import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../models/sector_model.dart';
import '../providers/dashboard_provider.dart';
import '../providers/sector_provider.dart';

class NewCollaboratorScreen extends ConsumerStatefulWidget {
  const NewCollaboratorScreen({super.key});

  @override
  ConsumerState<NewCollaboratorScreen> createState() => _NewCollaboratorScreenState();
}

class _NewCollaboratorScreenState extends ConsumerState<NewCollaboratorScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  int? _sectorId;
  int? _positionId;
  DateTime _hireDate = DateTime.now();
  bool _isSectorLeader = false;
  bool _isLoading = false;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _pickHireDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _hireDate,
      firstDate: DateTime(2015),
      lastDate: DateTime.now().add(const Duration(days: 90)),
    );
    if (picked != null) setState(() => _hireDate = picked);
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);

    try {
      final repository = ref.read(dashboardRepositoryProvider);
      await repository.registerCollaborator(
        email: _emailController.text.trim(),
        fullName: _nameController.text.trim(),
        password: _passwordController.text,
        sectorId: _sectorId,
        positionId: _positionId,
        hireDate: _hireDate,
        isSectorLeader: _isSectorLeader,
      );
      ref.invalidate(collaboratorsListProvider);
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) {
        final message = e.toString().replaceAll('Exception: ', '');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.md)),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sectorsAsync = ref.watch(sectorsListProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        backgroundColor: context.surfaceColor,
        foregroundColor: context.textPrimaryColor,
        elevation: 0,
        title: const Text('Novo Colaborador'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: AppCard(
            padding: const EdgeInsets.all(AppSpacing.xxl),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Cadastrar colaborador',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: context.textPrimaryColor),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    'Cria o acesso do colaborador à sua empresa.',
                    style: TextStyle(fontSize: 13, color: context.textSecondaryColor),
                  ),
                  const SizedBox(height: AppSpacing.xxl),
                  CustomTextField(
                    controller: _nameController,
                    label: 'Nome completo',
                    hint: 'Nome do colaborador',
                    prefixIcon: Icons.person_outline_rounded,
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Informe o nome.' : null,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  CustomTextField(
                    controller: _emailController,
                    label: 'E-mail',
                    hint: 'colaborador@empresa.com',
                    prefixIcon: Icons.email_outlined,
                    keyboardType: TextInputType.emailAddress,
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return 'Informe o e-mail.';
                      if (!v.contains('@') || !v.contains('.')) return 'Informe um e-mail válido.';
                      return null;
                    },
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  CustomTextField(
                    controller: _passwordController,
                    label: 'Senha inicial',
                    hint: 'Mínimo 8 caracteres',
                    prefixIcon: Icons.lock_outline_rounded,
                    obscureText: true,
                    validator: (v) {
                      if (v == null || v.isEmpty) return 'Informe a senha.';
                      if (v.length < 8) return 'A senha deve ter ao menos 8 caracteres.';
                      return null;
                    },
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  Text(
                    'Data de contratação',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: context.textSecondaryColor),
                  ),
                  const SizedBox(height: 6),
                  InkWell(
                    onTap: _pickHireDate,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 14),
                      decoration: BoxDecoration(
                        border: Border.all(color: context.borderColor),
                        borderRadius: BorderRadius.circular(AppRadius.md),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.event_outlined, size: 18, color: context.textMutedColor),
                          const SizedBox(width: AppSpacing.sm),
                          Text(
                            '${_hireDate.day.toString().padLeft(2, '0')}/${_hireDate.month.toString().padLeft(2, '0')}/${_hireDate.year}',
                            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: context.textPrimaryColor),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  Text(
                    'Setor',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: context.textSecondaryColor),
                  ),
                  const SizedBox(height: 6),
                  sectorsAsync.when(
                    loading: () => const LinearProgressIndicator(),
                    error: (_, __) => Text(
                      'Não foi possível carregar os setores.',
                      style: TextStyle(fontSize: 12, color: context.textMutedColor),
                    ),
                    data: (sectors) => _SectorDropdown(
                      sectors: sectors,
                      value: _sectorId,
                      onChanged: (id) => setState(() {
                        _sectorId = id;
                        _positionId = null;
                        if (id == null) _isSectorLeader = false;
                      }),
                    ),
                  ),
                  if (_sectorId != null) ...[
                    const SizedBox(height: AppSpacing.lg),
                    Text(
                      'Cargo',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: context.textSecondaryColor),
                    ),
                    const SizedBox(height: 6),
                    Consumer(
                      builder: (context, ref, _) {
                        final positionsAsync = ref.watch(positionsBySectorProvider(_sectorId!));
                        return positionsAsync.when(
                          loading: () => const LinearProgressIndicator(),
                          error: (_, __) => Text(
                            'Não foi possível carregar os cargos.',
                            style: TextStyle(fontSize: 12, color: context.textMutedColor),
                          ),
                          data: (positions) => _PositionDropdown(
                            positions: positions,
                            value: _positionId,
                            onChanged: (id) => setState(() => _positionId = id),
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    CheckboxListTile(
                      value: _isSectorLeader,
                      onChanged: (v) => setState(() => _isSectorLeader = v ?? false),
                      controlAffinity: ListTileControlAffinity.leading,
                      contentPadding: EdgeInsets.zero,
                      dense: true,
                      title: Text(
                        'Tornar líder do setor',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: context.textPrimaryColor),
                      ),
                      subtitle: Text(
                        'Poderá cadastrar treinamentos do próprio setor.',
                        style: TextStyle(fontSize: 12, color: context.textSecondaryColor),
                      ),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.xxl),
                  AppButton(
                    text: 'Cadastrar Colaborador',
                    icon: Icons.person_add_alt_1_rounded,
                    isLoading: _isLoading,
                    fullWidth: true,
                    onPressed: _handleSubmit,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SectorDropdown extends StatelessWidget {
  final List<SectorModel> sectors;
  final int? value;
  final ValueChanged<int?> onChanged;

  const _SectorDropdown({required this.sectors, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: BoxDecoration(
        border: Border.all(color: context.borderColor),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<int?>(
          value: value,
          isExpanded: true,
          hint: const Text('Geral (sem setor)'),
          onChanged: onChanged,
          items: [
            const DropdownMenuItem<int?>(value: null, child: Text('Geral (sem setor)')),
            ...sectors.map((s) => DropdownMenuItem<int?>(value: s.id, child: Text(s.name))),
          ],
        ),
      ),
    );
  }
}

class _PositionDropdown extends StatelessWidget {
  final List<PositionModel> positions;
  final int? value;
  final ValueChanged<int?> onChanged;

  const _PositionDropdown({required this.positions, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: BoxDecoration(
        border: Border.all(color: context.borderColor),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<int?>(
          value: value,
          isExpanded: true,
          hint: const Text('Nenhum cargo específico'),
          onChanged: onChanged,
          items: [
            const DropdownMenuItem<int?>(value: null, child: Text('Nenhum cargo específico')),
            ...positions.map((p) => DropdownMenuItem<int?>(value: p.id, child: Text(p.name))),
          ],
        ),
      ),
    );
  }
}
