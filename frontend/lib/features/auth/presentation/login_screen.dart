import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../app/theme.dart';
import '../../../../core/widgets/app_button.dart';
import '../../../../core/widgets/custom_text_field.dart';
import '../../../../core/widgets/theme_toggle_button.dart';
import '../providers/auth_provider.dart';
import 'widgets/launch_badge_overlay.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController(text: 'joao@empresa.com');
  final _passwordController = TextEditingController(text: 'senha123');
  bool _obscurePassword = true;
  bool _showLaunchOverlay = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();

    final success = await ref.read(authNotifierProvider.notifier).login(
          _emailController.text,
          _passwordController.text,
        );

    if (success && mounted) {
      setState(() => _showLaunchOverlay = true);
      return;
    }

    if (!success && mounted) {
      final errorMsg = ref.read(authNotifierProvider).errorMessage ??
          'Não foi possível conectar ao servidor. Verifique sua conexão.';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.error_outline_rounded, color: Colors.white, size: 20),
              const SizedBox(width: AppSpacing.md),
              Expanded(child: Text(errorMsg)),
            ],
          ),
          backgroundColor: AppColors.error,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.md)),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);
    final width = MediaQuery.of(context).size.width;
    final isDesktop = width >= 900;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: Stack(
        children: [
          isDesktop
              ? Row(
                  children: [
                    // ── Left Branding Panel (Desktop) ──────────────────────
                    Expanded(
                      flex: 5,
                      child: Container(
                        decoration: const BoxDecoration(
                          gradient: LinearGradient(
                            colors: [Color(0xFF0B0F19), Color(0xFF0F172A), Color(0xFF1E3A8A)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                        ),
                        padding: const EdgeInsets.all(AppSpacing.huge),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Brand Logo
                            Row(
                              children: [
                                Container(
                                  width: 44,
                                  height: 44,
                                  decoration: BoxDecoration(
                                    color: AppColors.primary,
                                    borderRadius: BorderRadius.circular(AppRadius.md),
                                    boxShadow: AppShadows.primaryGlow,
                                  ),
                                  child: const Icon(Icons.rocket_launch_rounded, color: Colors.white, size: 24),
                                ),
                                const SizedBox(width: AppSpacing.md),
                                const Text(
                                  'Onboarding Corp',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w800,
                                    color: Colors.white,
                                    letterSpacing: -0.4,
                                  ),
                                ),
                              ],
                            ),
                            const Spacer(),

                            // Headline & Value Proposition
                            const Text(
                              'Sua jornada de integração começa aqui.',
                              style: TextStyle(
                                fontSize: 34,
                                fontWeight: FontWeight.w800,
                                color: Colors.white,
                                height: 1.2,
                                letterSpacing: -1.0,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.lg),
                            const Text(
                              'Acesse seus treinamentos, trilhas por setor, documentos corporativos e acompanhe cada etapa do seu desenvolvimento desde o primeiro dia.',
                              style: TextStyle(
                                fontSize: 15,
                                color: Color(0xFF94A3B8),
                                height: 1.6,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.xxl),

                            // Highlights Chips
                            const Wrap(
                              spacing: AppSpacing.sm,
                              runSpacing: AppSpacing.sm,
                              children: [
                                _FeatureChip(icon: Icons.school_rounded, label: 'Trilhas por Setor'),
                                _FeatureChip(icon: Icons.task_alt_rounded, label: 'Checklist de Prazos'),
                                _FeatureChip(icon: Icons.folder_open_rounded, label: 'Biblioteca Digital'),
                              ],
                            ),
                            const Spacer(),

                            // Footer Note
                            const Text(
                              'Plataforma oficial de integração e capacitação de colaboradores.',
                              style: TextStyle(
                                fontSize: 12,
                                color: Color(0xFF64748B),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                    // ── Right Form Panel (Desktop) ─────────────────────────
                    Expanded(
                      flex: 6,
                      child: Center(
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 32),
                          child: ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 440),
                            child: _buildLoginForm(authState.isLoading, authState.sessionNotice),
                          ),
                        ),
                      ),
                    ),
                  ],
                )
              : SafeArea(
                  child: Center(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.all(AppSpacing.xxl),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 440),
                        child: _buildLoginForm(authState.isLoading, authState.sessionNotice, isMobile: true),
                      ),
                    ),
                  ),
                ),

          // Top right theme toggle
          const Positioned(
            top: 16,
            right: 16,
            child: ThemeToggleButton(),
          ),

          // Rocket launch animation on successful login
          if (_showLaunchOverlay)
            LaunchBadgeOverlay(
              onComplete: () => ref.read(authNotifierProvider.notifier).confirmAuthenticated(),
            ),
        ],
      ),
    );
  }

  Widget _buildLoginForm(bool isLoading, String? sessionNotice, {bool isMobile = false}) {
    final isDark = context.isDark;

    return Container(
      padding: isMobile ? const EdgeInsets.all(AppSpacing.xl) : const EdgeInsets.all(AppSpacing.xxxl),
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(AppRadius.xl),
        border: Border.all(color: context.borderColor),
        boxShadow: context.shadowMd,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header Icon on Mobile
            if (isMobile) ...[
              Center(
                child: Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(AppRadius.lg),
                    boxShadow: AppShadows.primaryGlow,
                  ),
                  child: const Icon(Icons.rocket_launch_rounded, color: Colors.white, size: 28),
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
            ],

            Text(
              'Bem-vindo de volta',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: context.textPrimaryColor,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              'Informe suas credenciais corporativas para entrar.',
              style: TextStyle(
                fontSize: 13,
                color: context.textSecondaryColor,
              ),
            ),

            // Aviso de sessão encerrada pelo servidor (empresa suspensa ou
            // token expirado). Só aparece quando o usuário foi derrubado.
            if (sessionNotice != null) ...[
              const SizedBox(height: AppSpacing.lg),
              _SessionNotice(message: sessionNotice),
            ],

            const SizedBox(height: AppSpacing.xxl),

            // E-mail Input
            CustomTextField(
              controller: _emailController,
              label: 'E-mail corporativo',
              hint: 'colaborador@empresa.com',
              prefixIcon: Icons.email_outlined,
              keyboardType: TextInputType.emailAddress,
              validator: (v) {
                if (v == null || v.trim().isEmpty) return 'Informe seu e-mail.';
                if (!v.contains('@') || !v.contains('.')) return 'Informe um e-mail válido.';
                return null;
              },
            ),
            const SizedBox(height: AppSpacing.lg),

            // Password Input
            CustomTextField(
              controller: _passwordController,
              label: 'Senha de acesso',
              hint: '••••••••',
              prefixIcon: Icons.lock_outline_rounded,
              obscureText: _obscurePassword,
              onFieldSubmitted: (_) => _handleLogin(),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                  size: 18,
                  color: isDark ? AppColors.darkTextMuted : AppColors.slate400,
                ),
                onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
              ),
              validator: (v) {
                if (v == null || v.isEmpty) return 'Informe sua senha.';
                return null;
              },
            ),
            const SizedBox(height: AppSpacing.sm),

            // Esqueci minha senha
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () => context.push('/forgot-password'),
                child: const Text('Esqueci minha senha'),
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // Submit Button
            AppButton(
              text: 'Entrar no Sistema',
              icon: Icons.login_rounded,
              isLoading: isLoading,
              fullWidth: true,
              size: AppButtonSize.lg,
              onPressed: _handleLogin,
            ),
            const SizedBox(height: AppSpacing.xl),

            // Quick Demo Credentials Pill
            Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E293B) : AppColors.slate50,
                borderRadius: BorderRadius.circular(AppRadius.md),
                border: Border.all(color: context.borderColor),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.info_outline_rounded, size: 14, color: AppColors.primary),
                      const SizedBox(width: 6),
                      Text(
                        'Acesso de demonstração rápido:',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: context.textPrimaryColor,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Colaborador: joao@empresa.com / senha123\nRH Admin: rh@empresa.com / senha123',
                    style: TextStyle(
                      fontSize: 11,
                      color: context.textSecondaryColor,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Explica por que o usuário voltou para o login, sem detalhe técnico.
class _SessionNotice extends StatelessWidget {
  final String message;

  const _SessionNotice({required this.message});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: isDark ? AppColors.warningDark.withValues(alpha: 0.28) : AppColors.warningLight,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(
          color: isDark
              ? AppColors.warningDarkText.withValues(alpha: 0.35)
              : AppColors.warning.withValues(alpha: 0.35),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.info_outline_rounded,
            size: 18,
            color: isDark ? AppColors.warningDarkText : AppColors.warning,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                fontSize: 12.5,
                height: 1.45,
                color: isDark ? AppColors.warningDarkText : AppColors.warningText,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FeatureChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _FeatureChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppRadius.pill),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: AppColors.primary400),
          const SizedBox(width: 8),
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }
}
