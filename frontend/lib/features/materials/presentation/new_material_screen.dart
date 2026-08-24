import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../auth/providers/auth_provider.dart';
import '../../rh_dashboard/models/sector_model.dart';
import '../../rh_dashboard/providers/sector_provider.dart';
import '../providers/material_provider.dart';

class NewMaterialScreen extends ConsumerStatefulWidget {
  const NewMaterialScreen({super.key});

  @override
  ConsumerState<NewMaterialScreen> createState() => _NewMaterialScreenState();
}

class _NewMaterialScreenState extends ConsumerState<NewMaterialScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _fileUrlController = TextEditingController();
  int? _sectorId;
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
    _fileUrlController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);

    try {
      final repository = ref.read(materialRepositoryProvider);
      await repository.createMaterial(
        title: _titleController.text.trim(),
        fileUrl: _fileUrlController.text.trim(),
        sectorId: _sectorId,
      );
      ref.invalidate(materialsListProvider);
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

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        backgroundColor: context.surfaceColor,
        foregroundColor: context.textPrimaryColor,
        elevation: 0,
        title: const Text('Novo Material'),
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
                    'Cadastrar material',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: context.textPrimaryColor),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    isRestrictedToOwnSector
                        ? 'Adiciona um documento visível para o seu setor.'
                        : 'Adiciona um documento à biblioteca da sua empresa.',
                    style: TextStyle(fontSize: 13, color: context.textSecondaryColor),
                  ),
                  const SizedBox(height: AppSpacing.xxl),
                  CustomTextField(
                    controller: _titleController,
                    label: 'Título',
                    hint: 'Nome do material',
                    prefixIcon: Icons.description_outlined,
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Informe o título.' : null,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  CustomTextField(
                    controller: _fileUrlController,
                    label: 'URL do arquivo',
                    hint: 'https://...',
                    prefixIcon: Icons.link_rounded,
                    keyboardType: TextInputType.url,
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return 'Informe a URL do arquivo.';
                      final uri = Uri.tryParse(v.trim());
                      if (uri == null || !uri.hasScheme) return 'Informe uma URL válida.';
                      return null;
                    },
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
                        onChanged: (id) => setState(() => _sectorId = id),
                      ),
                    ),
                  const SizedBox(height: AppSpacing.xxl),
                  AppButton(
                    text: 'Cadastrar Material',
                    icon: Icons.upload_file_rounded,
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
