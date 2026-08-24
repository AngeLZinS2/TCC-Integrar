import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../../shared/models/course_model.dart';
import '../../auth/providers/auth_provider.dart';
import '../../rh_dashboard/models/sector_model.dart';
import '../../rh_dashboard/providers/sector_provider.dart';
import '../providers/course_provider.dart';

const _deadlineOptions = [
  (value: null, label: 'Sem prazo'),
  (value: 'day1', label: 'Dia 1'),
  (value: 'week1', label: 'Semana 1'),
  (value: 'month1', label: 'Mês 1'),
];

class NewCourseScreen extends ConsumerStatefulWidget {
  const NewCourseScreen({super.key});

  @override
  ConsumerState<NewCourseScreen> createState() => _NewCourseScreenState();
}

class _NewCourseScreenState extends ConsumerState<NewCourseScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  int? _sectorId;
  int? _positionId;
  String? _deadline;
  int? _prerequisiteId;
  final int _order = 0;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    final user = ref.read(authNotifierProvider).user;
    if (user != null && !user.isRHAdmin && user.isSectorLeader) {
      _sectorId = user.sector;
    }
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);

    try {
      final repository = ref.read(courseRepositoryProvider);
      await repository.createCourse(
        title: _titleController.text.trim(),
        description: _descriptionController.text.trim(),
        sectorId: _sectorId,
        positionId: _positionId,
        deadline: _deadline,
        prerequisiteId: _prerequisiteId,
        order: _order,
      );
      ref.read(coursesListProvider.notifier).loadCourses();
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
    final user = ref.watch(authNotifierProvider).user;
    final isRestrictedToOwnSector = user != null && !user.isRHAdmin && user.isSectorLeader;
    final sectorsAsync = ref.watch(sectorsListProvider);
    final coursesAsync = ref.watch(coursesListProvider);

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        backgroundColor: context.surfaceColor,
        foregroundColor: context.textPrimaryColor,
        elevation: 0,
        title: const Text('Novo Treinamento'),
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
                    'Cadastrar treinamento',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: context.textPrimaryColor),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    isRestrictedToOwnSector
                        ? 'Cria um treinamento visível para o seu setor.'
                        : 'Cria um treinamento para a sua empresa.',
                    style: TextStyle(fontSize: 13, color: context.textSecondaryColor),
                  ),
                  const SizedBox(height: AppSpacing.xxl),
                  CustomTextField(
                    controller: _titleController,
                    label: 'Título',
                    hint: 'Nome do treinamento',
                    prefixIcon: Icons.school_outlined,
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Informe o título.' : null,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  CustomTextField(
                    controller: _descriptionController,
                    label: 'Descrição',
                    hint: 'Do que se trata o treinamento (opcional)',
                    prefixIcon: Icons.notes_outlined,
                    maxLines: 3,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  Text(
                    'Setor',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: context.textSecondaryColor),
                  ),
                  const SizedBox(height: 6),
                  if (isRestrictedToOwnSector)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 14),
                      decoration: BoxDecoration(
                        border: Border.all(color: context.borderColor),
                        borderRadius: BorderRadius.circular(AppRadius.md),
                        color: context.scaffoldBg,
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.lock_outline_rounded, size: 18, color: context.textMutedColor),
                          const SizedBox(width: AppSpacing.sm),
                          Text(
                            user.sectorName ?? 'Seu setor',
                            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: context.textPrimaryColor),
                          ),
                        ],
                      ),
                    )
                  else
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
                  ],
                  const SizedBox(height: AppSpacing.lg),
                  Text(
                    'Prazo',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: context.textSecondaryColor),
                  ),
                  const SizedBox(height: 6),
                  _DeadlineDropdown(
                    value: _deadline,
                    onChanged: (v) => setState(() => _deadline = v),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  Text(
                    'Pré-requisito',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: context.textSecondaryColor),
                  ),
                  const SizedBox(height: 6),
                  coursesAsync.when(
                    loading: () => const LinearProgressIndicator(),
                    error: (_, __) => Text(
                      'Não foi possível carregar os treinamentos existentes.',
                      style: TextStyle(fontSize: 12, color: context.textMutedColor),
                    ),
                    data: (courses) {
                      final scoped = isRestrictedToOwnSector
                          ? courses.where((c) => c.sector == _sectorId).toList()
                          : courses;
                      return _PrerequisiteDropdown(
                        courses: scoped,
                        value: _prerequisiteId,
                        onChanged: (id) => setState(() => _prerequisiteId = id),
                      );
                    },
                  ),
                  const SizedBox(height: AppSpacing.xxl),
                  AppButton(
                    text: 'Cadastrar Treinamento',
                    icon: Icons.add_circle_outline_rounded,
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
          hint: const Text('Geral (todos os setores)'),
          onChanged: onChanged,
          items: [
            const DropdownMenuItem<int?>(value: null, child: Text('Geral (todos os setores)')),
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

class _DeadlineDropdown extends StatelessWidget {
  final String? value;
  final ValueChanged<String?> onChanged;

  const _DeadlineDropdown({required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: BoxDecoration(
        border: Border.all(color: context.borderColor),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String?>(
          value: value,
          isExpanded: true,
          onChanged: onChanged,
          items: _deadlineOptions
              .map((o) => DropdownMenuItem<String?>(value: o.value, child: Text(o.label)))
              .toList(),
        ),
      ),
    );
  }
}

class _PrerequisiteDropdown extends StatelessWidget {
  final List<CourseModel> courses;
  final int? value;
  final ValueChanged<int?> onChanged;

  const _PrerequisiteDropdown({required this.courses, required this.value, required this.onChanged});

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
          hint: const Text('Nenhum'),
          onChanged: onChanged,
          items: [
            const DropdownMenuItem<int?>(value: null, child: Text('Nenhum')),
            ...courses.map((c) => DropdownMenuItem<int?>(value: c.id, child: Text(c.title))),
          ],
        ),
      ),
    );
  }
}
