import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../providers/company_provider.dart';

class NewCompanyScreen extends ConsumerStatefulWidget {
  const NewCompanyScreen({super.key});

  @override
  ConsumerState<NewCompanyScreen> createState() => _NewCompanyScreenState();
}

class _NewCompanyScreenState extends ConsumerState<NewCompanyScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _adminEmailController = TextEditingController();
  final _adminNameController = TextEditingController();
  final _adminPasswordController = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _nameController.dispose();
    _adminEmailController.dispose();
    _adminNameController.dispose();
    _adminPasswordController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);

    try {
      await ref.read(companiesListProvider.notifier).createCompany(
            name: _nameController.text.trim(),
            adminEmail: _adminEmailController.text.trim(),
            adminFullName: _adminNameController.text.trim(),
            adminPassword: _adminPasswordController.text,
          );
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
    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        backgroundColor: context.surfaceColor,
        foregroundColor: context.textPrimaryColor,
        elevation: 0,
        title: const Text('Nova Empresa'),
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
                    'Cadastrar nova empresa',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: context.textPrimaryColor),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    'Cria a empresa e o primeiro usuário RH admin dela.',
                    style: TextStyle(fontSize: 13, color: context.textSecondaryColor),
                  ),
                  const SizedBox(height: AppSpacing.xxl),
                  CustomTextField(
                    controller: _nameController,
                    label: 'Nome da empresa',
                    hint: 'Ex: Acme Ltda.',
                    prefixIcon: Icons.apartment_outlined,
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Informe o nome da empresa.' : null,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  Text(
                    'Primeiro RH admin',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: context.textPrimaryColor),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  CustomTextField(
                    controller: _adminNameController,
                    label: 'Nome completo',
                    hint: 'Nome do RH responsável',
                    prefixIcon: Icons.person_outline_rounded,
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Informe o nome.' : null,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  CustomTextField(
                    controller: _adminEmailController,
                    label: 'E-mail',
                    hint: 'rh@empresa.com',
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
                    controller: _adminPasswordController,
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
                  const SizedBox(height: AppSpacing.xxl),
                  AppButton(
                    text: 'Cadastrar Empresa',
                    icon: Icons.add_business_rounded,
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
