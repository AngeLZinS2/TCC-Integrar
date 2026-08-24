import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../../shared/providers/app_providers.dart';

/// Definição da nova senha, aberta pelo link enviado por e-mail.
///
/// `uid` e `token` chegam pela query string. Um link truncado ou ausente
/// cai direto no estado de erro, sem deixar o formulário aparecer.
class ResetPasswordScreen extends ConsumerStatefulWidget {
  final String uid;
  final String token;

  const ResetPasswordScreen({super.key, required this.uid, required this.token});

  @override
  ConsumerState<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();
  bool _obscure = true;
  bool _isLoading = false;
  bool _done = false;
  String? _error;

  bool get _hasValidLink => widget.uid.isNotEmpty && widget.token.isNotEmpty;

  @override
  void dispose() {
    _passwordController.dispose();
    _confirmController.dispose();
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
      await ref.read(authRepositoryProvider).confirmPasswordReset(
            uid: widget.uid,
            token: widget.token,
            newPassword: _passwordController.text,
          );
      if (mounted) setState(() => _done = true);
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
        title: const Text('Nova senha'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: AppCard(
              padding: const EdgeInsets.all(AppSpacing.xxl),
              child: !_hasValidLink
                  ? _buildBrokenLink(context)
                  : _done
                      ? _buildSuccess(context)
                      : _buildForm(context),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildForm(BuildContext context) {
    final isDark = context.isDark;
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Escolha uma nova senha',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: context.textPrimaryColor,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Use ao menos 8 caracteres. Evite senhas óbvias ou só com números.',
            style: TextStyle(fontSize: 13, height: 1.45, color: context.textSecondaryColor),
          ),
          const SizedBox(height: AppSpacing.xxl),
          CustomTextField(
            controller: _passwordController,
            label: 'Nova senha',
            hint: '••••••••',
            prefixIcon: Icons.lock_outline_rounded,
            obscureText: _obscure,
            autofocus: true,
            suffixIcon: IconButton(
              tooltip: _obscure ? 'Mostrar senha' : 'Ocultar senha',
              icon: Icon(
                _obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                size: 18,
                color: isDark ? AppColors.darkTextMuted : AppColors.slate400,
              ),
              onPressed: () => setState(() => _obscure = !_obscure),
            ),
            validator: (v) {
              if (v == null || v.isEmpty) return 'Informe a nova senha.';
              if (v.length < 8) return 'A senha deve ter ao menos 8 caracteres.';
              return null;
            },
          ),
          const SizedBox(height: AppSpacing.lg),
          CustomTextField(
            controller: _confirmController,
            label: 'Confirme a nova senha',
            hint: '••••••••',
            prefixIcon: Icons.lock_reset_rounded,
            obscureText: _obscure,
            onFieldSubmitted: (_) => _handleSubmit(),
            validator: (v) {
              if (v == null || v.isEmpty) return 'Repita a nova senha.';
              if (v != _passwordController.text) return 'As senhas não conferem.';
              return null;
            },
          ),
          if (_error != null) ...[
            const SizedBox(height: AppSpacing.md),
            _Note(message: _error!, isError: true),
          ],
          const SizedBox(height: AppSpacing.xxl),
          AppButton(
            text: 'Salvar nova senha',
            icon: Icons.check_rounded,
            isLoading: _isLoading,
            fullWidth: true,
            onPressed: _handleSubmit,
          ),
        ],
      ),
    );
  }

  Widget _buildSuccess(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          Icons.check_circle_outline_rounded,
          size: 44,
          color: context.isDark ? AppColors.successDarkText : AppColors.success,
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Senha alterada',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w800,
            color: context.textPrimaryColor,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Sua senha foi atualizada e as sessões antigas foram encerradas. '
          'Entre novamente com a nova senha.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 13, height: 1.5, color: context.textSecondaryColor),
        ),
        const SizedBox(height: AppSpacing.xxl),
        AppButton(
          text: 'Ir para o login',
          icon: Icons.login_rounded,
          fullWidth: true,
          onPressed: () => context.go('/login'),
        ),
      ],
    );
  }

  Widget _buildBrokenLink(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          Icons.link_off_rounded,
          size: 44,
          color: context.isDark ? AppColors.errorDarkText : AppColors.error,
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Link inválido',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w800,
            color: context.textPrimaryColor,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Este link de recuperação está incompleto. Solicite um novo para '
          'redefinir sua senha.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 13, height: 1.5, color: context.textSecondaryColor),
        ),
        const SizedBox(height: AppSpacing.xxl),
        AppButton(
          text: 'Solicitar novo link',
          icon: Icons.refresh_rounded,
          fullWidth: true,
          onPressed: () => context.go('/forgot-password'),
        ),
      ],
    );
  }
}

class _Note extends StatelessWidget {
  final String message;
  final bool isError;

  const _Note({required this.message, this.isError = false});

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
