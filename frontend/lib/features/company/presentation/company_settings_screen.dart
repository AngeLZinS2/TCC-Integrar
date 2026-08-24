import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_progress.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../auth/providers/auth_provider.dart';
import '../models/company_settings_model.dart';
import '../providers/company_settings_provider.dart';

/// Configurações da própria empresa + progresso da configuração inicial.
///
/// As duas coisas na mesma tela porque o checklist só faz sentido enquanto
/// a empresa está sendo montada, e some sozinho quando tudo está pronto.
class CompanySettingsScreen extends ConsumerWidget {
  const CompanySettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final companyAsync = ref.watch(myCompanyProvider);
    final user = ref.watch(authNotifierProvider).user;
    final podeEditar = user?.canEditCompany ?? false;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(myCompanyProvider);
          ref.invalidate(setupChecklistProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Align(
            alignment: Alignment.topCenter,
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  AppSectionHeader(
                    title: 'Configurações da Empresa',
                    subtitle: podeEditar
                        ? 'Dados cadastrais e progresso da configuração inicial.'
                        : 'Dados cadastrais da sua empresa. Somente o administrador pode alterá-los.',
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  const SetupChecklistCard(),
                  const SizedBox(height: AppSpacing.xl),
                  companyAsync.when(
                    loading: () => const AppSkeleton.card(height: 420),
                    error: (err, _) => AppErrorState(
                      message: 'Não foi possível carregar os dados da empresa.',
                      onRetry: () => ref.invalidate(myCompanyProvider),
                    ),
                    data: (company) =>
                        _CompanyForm(company: company, readOnly: !podeEditar),
                  ),
                  const SizedBox(height: AppSpacing.xxl),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Cartão de progresso da configuração inicial.
///
/// Público porque o painel do RH também o exibe — é lá que a empresa nova
/// cai primeiro, e uma tela vazia sem orientação era justamente a lacuna.
class SetupChecklistCard extends ConsumerWidget {
  /// Quando true, some assim que a configuração termina.
  final bool hideWhenComplete;

  const SetupChecklistCard({super.key, this.hideWhenComplete = false});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final checklistAsync = ref.watch(setupChecklistProvider);

    return checklistAsync.when(
      loading: () => const AppSkeleton.card(height: 180),
      error: (_, __) => const SizedBox.shrink(),
      data: (checklist) {
        if (checklist.isComplete && hideWhenComplete) {
          return const SizedBox.shrink();
        }
        return AppCard(
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    checklist.isComplete
                        ? Icons.verified_rounded
                        : Icons.rocket_launch_outlined,
                    size: 20,
                    color: checklist.isComplete
                        ? (context.isDark ? AppColors.successDarkText : AppColors.success)
                        : AppColors.primary,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      checklist.isComplete
                          ? 'Empresa configurada!'
                          : 'Vamos configurar sua empresa',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: context.textPrimaryColor,
                        letterSpacing: -0.3,
                      ),
                    ),
                  ),
                  Text(
                    '${checklist.completedSteps}/${checklist.totalSteps}',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: context.textSecondaryColor,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                checklist.isComplete
                    ? 'Tudo pronto. Sua empresa já pode usar a plataforma por completo.'
                    : 'Complete os passos abaixo. Você pode sair e continuar depois — '
                        'o progresso é calculado automaticamente.',
                style: TextStyle(
                  fontSize: 12.5,
                  height: 1.45,
                  color: context.textSecondaryColor,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              Semantics(
                label: 'Configuração ${checklist.percent} por cento concluída',
                child: AppProgress(
                  value: checklist.percent / 100,
                  color: checklist.isComplete ? AppColors.success : AppColors.primary,
                  height: 8,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              ...checklist.steps.map((step) => _StepRow(step: step)),
            ],
          ),
        );
      },
    );
  }
}

class _StepRow extends StatelessWidget {
  final SetupStep step;

  const _StepRow({required this.step});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    return Semantics(
      button: !step.done,
      label: '${step.title}, ${step.done ? "concluído" : "pendente"}',
      child: InkWell(
        onTap: step.done ? null : () => context.go(step.route),
        borderRadius: BorderRadius.circular(AppRadius.sm),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 7),
          child: Row(
            children: [
              Icon(
                step.done ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                size: 19,
                color: step.done
                    ? (isDark ? AppColors.successDarkText : AppColors.success)
                    : context.textMutedColor,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      step.title,
                      style: TextStyle(
                        fontSize: 13.5,
                        fontWeight: step.done ? FontWeight.w500 : FontWeight.w600,
                        color: step.done
                            ? context.textMutedColor
                            : context.textPrimaryColor,
                        decoration: step.done ? TextDecoration.lineThrough : null,
                        decorationColor: context.textMutedColor,
                      ),
                    ),
                    if (!step.done)
                      Text(
                        step.description,
                        style: TextStyle(fontSize: 11.5, color: context.textSecondaryColor),
                      ),
                  ],
                ),
              ),
              if (!step.done)
                Icon(Icons.chevron_right_rounded, size: 18, color: context.textMutedColor),
            ],
          ),
        ),
      ),
    );
  }
}

class _CompanyForm extends ConsumerStatefulWidget {
  final CompanySettingsModel company;
  final bool readOnly;

  const _CompanyForm({required this.company, required this.readOnly});

  @override
  ConsumerState<_CompanyForm> createState() => _CompanyFormState();
}

class _CompanyFormState extends ConsumerState<_CompanyForm> {
  final _formKey = GlobalKey<FormState>();
  late final Map<String, TextEditingController> _controllers;
  bool _isSaving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final c = widget.company;
    _controllers = {
      'name': TextEditingController(text: c.name),
      'legalName': TextEditingController(text: c.legalName),
      'cnpj': TextEditingController(text: c.cnpj),
      'description': TextEditingController(text: c.description),
      'phone': TextEditingController(text: c.phone),
      'email': TextEditingController(text: c.email),
      'address': TextEditingController(text: c.address),
      'logoUrl': TextEditingController(text: c.logoUrl),
    };
  }

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  String _value(String key) => _controllers[key]!.text.trim();

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isSaving = true;
      _error = null;
    });

    try {
      await ref.read(companySettingsRepositoryProvider).update(
            name: _value('name'),
            legalName: _value('legalName'),
            cnpj: _value('cnpj'),
            description: _value('description'),
            phone: _value('phone'),
            email: _value('email'),
            address: _value('address'),
            logoUrl: _value('logoUrl'),
          );
      ref.invalidate(myCompanyProvider);
      // Preencher os dados marca o primeiro passo do checklist.
      ref.invalidate(setupChecklistProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Dados da empresa atualizados.'),
          backgroundColor: AppColors.success,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.md)),
        ),
      );
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
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.xxl),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Dados cadastrais',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: context.textPrimaryColor,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              controller: _controllers['name']!,
              label: 'Nome',
              hint: 'Como a empresa aparece no sistema',
              prefixIcon: Icons.apartment_rounded,
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Informe o nome da empresa.' : null,
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              controller: _controllers['legalName']!,
              label: 'Razão social',
              hint: 'Nome jurídico completo (opcional)',
              prefixIcon: Icons.gavel_rounded,
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              controller: _controllers['cnpj']!,
              label: 'CNPJ',
              hint: '00.000.000/0000-00 (opcional)',
              prefixIcon: Icons.badge_outlined,
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              controller: _controllers['description']!,
              label: 'Descrição',
              hint: 'O que a empresa faz (opcional)',
              prefixIcon: Icons.notes_outlined,
              maxLines: 3,
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              controller: _controllers['phone']!,
              label: 'Telefone',
              hint: '(11) 3333-4444 (opcional)',
              prefixIcon: Icons.phone_outlined,
              keyboardType: TextInputType.phone,
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              controller: _controllers['email']!,
              label: 'E-mail de contato',
              hint: 'contato@empresa.com (opcional)',
              prefixIcon: Icons.email_outlined,
              keyboardType: TextInputType.emailAddress,
              validator: (v) {
                if (v == null || v.trim().isEmpty) return null;
                if (!v.contains('@') || !v.contains('.')) return 'Informe um e-mail válido.';
                return null;
              },
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              controller: _controllers['address']!,
              label: 'Endereço',
              hint: 'Rua, número, cidade (opcional)',
              prefixIcon: Icons.place_outlined,
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              controller: _controllers['logoUrl']!,
              label: 'URL da logo',
              hint: 'https://... (opcional)',
              prefixIcon: Icons.image_outlined,
              keyboardType: TextInputType.url,
              validator: (v) {
                if (v == null || v.trim().isEmpty) return null;
                final uri = Uri.tryParse(v.trim());
                if (uri == null || !uri.hasScheme) return 'Informe uma URL válida.';
                return null;
              },
            ),
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
            const SizedBox(height: AppSpacing.xl),
            if (widget.readOnly)
              Row(
                children: [
                  Icon(Icons.lock_outline_rounded, size: 16, color: context.textMutedColor),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      'Somente o administrador da empresa pode alterar estes dados.',
                      style: TextStyle(fontSize: 12, color: context.textMutedColor),
                    ),
                  ),
                ],
              )
            else
              AppButton(
                text: 'Salvar alterações',
                icon: Icons.check_rounded,
                isLoading: _isSaving,
                fullWidth: true,
                onPressed: _save,
              ),
          ],
        ),
      ),
    );
  }
}
