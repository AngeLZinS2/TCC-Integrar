import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../../shared/providers/app_providers.dart';

/// Pedido de recuperação de senha.
///
/// Depois de enviar, a tela mostra sempre a mesma confirmação — o backend
/// não revela se o e-mail está cadastrado, e a interface não pode revelar
/// aquilo que a API esconde.
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  bool _isLoading = false;
  bool _sent = false;
  String? _error;

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      await ref.read(authRepositoryProvider).requestPasswordReset(_emailController.text);
      if (mounted) setState(() => _sent = true);
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
    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: AppBar(
        backgroundColor: context.surfaceColor,
        foregroundColor: context.textPrimaryColor,
        elevation: 0,
        title: const Text('Recuperar senha'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: AppCard(
              padding: const EdgeInsets.all(AppSpacing.xxl),
              child: _sent ? _buildSentState(context) : _buildForm(context),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildForm(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Esqueceu sua senha?',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: context.textPrimaryColor,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Informe o e-mail da sua conta e enviaremos um link para você '
            'escolher uma nova senha.',
            style: TextStyle(fontSize: 13, height: 1.45, color: context.textSecondaryColor),
          ),
          const SizedBox(height: AppSpacing.xxl),
          CustomTextField(
            controller: _emailController,
            label: 'E-mail corporativo',
            hint: 'colaborador@empresa.com',
            prefixIcon: Icons.email_outlined,
            keyboardType: TextInputType.emailAddress,
            autofocus: true,
            onFieldSubmitted: (_) => _handleSubmit(),
            validator: (v) {
              if (v == null || v.trim().isEmpty) return 'Informe seu e-mail.';
              if (!v.contains('@') || !v.contains('.')) return 'Informe um e-mail válido.';
              return null;
            },
          ),
          if (_error != null) ...[
            const SizedBox(height: AppSpacing.md),
            _ErrorNote(message: _error!),
          ],
          const SizedBox(height: AppSpacing.xxl),
          AppButton(
            text: 'Enviar link de recuperação',
            icon: Icons.send_rounded,
            isLoading: _isLoading,
            fullWidth: true,
            onPressed: _handleSubmit,
          ),
          const SizedBox(height: AppSpacing.md),
          TextButton(
            onPressed: () => context.go('/login'),
            child: const Text('Voltar para o login'),
          ),
        ],
      ),
    );
  }

  Widget _buildSentState(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          Icons.mark_email_read_outlined,
          size: 44,
          color: context.isDark ? AppColors.successDarkText : AppColors.success,
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Verifique seu e-mail',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w800,
            color: context.textPrimaryColor,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Se existir uma conta associada a este e-mail, enviamos as '
          'instruções para recuperação. O link vale por algumas horas e '
          'só pode ser usado uma vez.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 13, height: 1.5, color: context.textSecondaryColor),
        ),
        const SizedBox(height: AppSpacing.xxl),
        AppButton(
          text: 'Voltar para o login',
          icon: Icons.arrow_back_rounded,
          variant: AppButtonVariant.outline,
          fullWidth: true,
          onPressed: () => context.go('/login'),
        ),
      ],
    );
  }
}

class _ErrorNote extends StatelessWidget {
  final String message;

  const _ErrorNote({required this.message});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: isDark ? AppColors.errorDark.withValues(alpha: 0.25) : AppColors.errorLight,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.error_outline_rounded,
            size: 17,
            color: isDark ? AppColors.errorDarkText : AppColors.error,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                fontSize: 12.5,
                height: 1.4,
                color: isDark ? AppColors.errorDarkText : AppColors.errorText,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
