import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_avatar.dart';
import '../../../core/widgets/app_badge.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/custom_text_field.dart';
import '../../../core/widgets/theme_toggle_button.dart';
import '../../auth/providers/auth_provider.dart';

/// Perfil do próprio usuário.
///
/// A tela separa visualmente o que a pessoa pode alterar do que é
/// administrado pelo RH. Não é decoração: a mesma fronteira existe no
/// backend, onde os campos administrativos são read-only em `/auth/me/`.
class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _avatarController = TextEditingController();

  bool _isEditing = false;
  bool _isSaving = false;
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _avatarController.dispose();
    super.dispose();
  }

  void _startEditing(user) {
    _nameController.text = user.fullName;
    _phoneController.text = user.phone;
    _avatarController.text = user.avatarUrl;
    setState(() {
      _isEditing = true;
      _error = null;
    });
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isSaving = true;
      _error = null;
    });

    try {
      await ref.read(authNotifierProvider.notifier).updateProfile(
            fullName: _nameController.text.trim(),
            phone: _phoneController.text.trim(),
            avatarUrl: _avatarController.text.trim(),
          );
      if (!mounted) return;
      setState(() => _isEditing = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Perfil atualizado.'),
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
    final user = ref.watch(authNotifierProvider).user;

    if (user == null) {
      return Scaffold(
        backgroundColor: context.scaffoldBg,
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 800),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AppSectionHeader(
                  title: 'Meu Perfil',
                  subtitle: 'Seus dados cadastrais, posição na empresa e preferências.',
                  trailing: _isEditing
                      ? null
                      : Semantics(
                          button: true,
                          label: 'Editar meus dados pessoais',
                          child: AppButton(
                            text: 'Editar',
                            icon: Icons.edit_outlined,
                            variant: AppButtonVariant.outline,
                            size: AppButtonSize.sm,
                            onPressed: () => _startEditing(user),
                          ),
                        ),
                ),
                const SizedBox(height: AppSpacing.lg),

                _IdentityCard(user: user),
                const SizedBox(height: AppSpacing.xxl),

                // ── Editável pelo colaborador ───────────────────────────
                const _SectionTitle(
                  title: 'Informações que você pode alterar',
                  icon: Icons.edit_outlined,
                ),
                const SizedBox(height: AppSpacing.sm),
                AppCard(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: _isEditing
                      ? _buildEditForm()
                      : Column(
                          children: [
                            _InfoRow(
                              label: 'Nome completo',
                              value: user.fullName,
                              icon: Icons.badge_outlined,
                            ),
                            const _Divider(),
                            _InfoRow(
                              label: 'Telefone',
                              value: user.phone.isEmpty ? 'Não informado' : user.phone,
                              icon: Icons.phone_outlined,
                              isEmpty: user.phone.isEmpty,
                            ),
                            const _Divider(),
                            _InfoRow(
                              label: 'Foto',
                              value: user.avatarUrl.isEmpty
                                  ? 'Nenhuma foto definida'
                                  : user.avatarUrl,
                              icon: Icons.photo_camera_outlined,
                              isEmpty: user.avatarUrl.isEmpty,
                            ),
                          ],
                        ),
                ),
                const SizedBox(height: AppSpacing.xxl),

                // ── Administrado pelo RH ────────────────────────────────
                const _SectionTitle(
                  title: 'Informações administradas pelo RH',
                  icon: Icons.lock_outline_rounded,
                ),
                const SizedBox(height: 4),
                Text(
                  'Para corrigir qualquer um destes dados, fale com o RH da sua empresa.',
                  style: TextStyle(fontSize: 12.5, color: context.textSecondaryColor),
                ),
                const SizedBox(height: AppSpacing.sm),
                AppCard(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: Column(
                    children: [
                      _InfoRow(
                        label: 'E-mail corporativo',
                        value: user.email,
                        icon: Icons.email_outlined,
                      ),
                      const _Divider(),
                      _InfoRow(
                        label: 'Matrícula',
                        value: user.registrationNumber.isEmpty
                            ? 'Não informada'
                            : user.registrationNumber,
                        icon: Icons.pin_outlined,
                        isEmpty: user.registrationNumber.isEmpty,
                      ),
                      const _Divider(),
                      _InfoRow(
                        label: 'Setor',
                        value: user.sectorName ?? 'Não atribuído',
                        icon: Icons.corporate_fare_rounded,
                        isEmpty: user.sectorName == null,
                      ),
                      const _Divider(),
                      _InfoRow(
                        label: 'Cargo',
                        value: user.positionName ?? 'Não atribuído',
                        icon: Icons.work_outline_rounded,
                        isEmpty: user.positionName == null,
                      ),
                      const _Divider(),
                      _InfoRow(
                        label: 'Gestor',
                        value: user.managerName ?? 'Não definido',
                        icon: Icons.supervisor_account_outlined,
                        isEmpty: user.managerName == null,
                      ),
                      const _Divider(),
                      _InfoRow(
                        label: 'Data de admissão',
                        value: user.hireDate == null
                            ? 'Não informada'
                            : _formatDate(user.hireDate!),
                        icon: Icons.event_outlined,
                        isEmpty: user.hireDate == null,
                      ),
                      const _Divider(),
                      _InfoRow(
                        label: 'Nível de acesso',
                        value: user.roleLabel,
                        icon: Icons.security_rounded,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.xxl),

                const _SectionTitle(title: 'Preferências', icon: Icons.tune_rounded),
                const SizedBox(height: AppSpacing.sm),
                AppCard(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: Row(
                    children: [
                      Icon(Icons.dark_mode_outlined, size: 18, color: context.textMutedColor),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: Text(
                          'Tema da interface',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: context.textPrimaryColor,
                          ),
                        ),
                      ),
                      const ThemeToggleButton(),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.xxxl),

                Semantics(
                  button: true,
                  label: 'Encerrar sessão e sair do sistema',
                  child: AppButton(
                    text: 'Encerrar Sessão',
                    icon: Icons.logout_rounded,
                    variant: AppButtonVariant.danger,
                    onPressed: () => _confirmLogout(context),
                  ),
                ),
                const SizedBox(height: AppSpacing.xxl),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildEditForm() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CustomTextField(
            controller: _nameController,
            label: 'Nome completo',
            hint: 'Como você quer ser chamado',
            prefixIcon: Icons.badge_outlined,
            validator: (v) =>
                (v == null || v.trim().isEmpty) ? 'Informe seu nome.' : null,
          ),
          const SizedBox(height: AppSpacing.lg),
          CustomTextField(
            controller: _phoneController,
            label: 'Telefone',
            hint: '(11) 90000-0000',
            prefixIcon: Icons.phone_outlined,
            keyboardType: TextInputType.phone,
          ),
          const SizedBox(height: AppSpacing.lg),
          CustomTextField(
            controller: _avatarController,
            label: 'URL da foto',
            hint: 'https://...',
            prefixIcon: Icons.photo_camera_outlined,
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
          Row(
            children: [
              Expanded(
                child: AppButton(
                  text: 'Cancelar',
                  variant: AppButtonVariant.outline,
                  fullWidth: true,
                  onPressed: () => setState(() {
                    _isEditing = false;
                    _error = null;
                  }),
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: AppButton(
                  text: 'Salvar',
                  icon: Icons.check_rounded,
                  isLoading: _isSaving,
                  fullWidth: true,
                  onPressed: _save,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _confirmLogout(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: context.surfaceColor,
        title: Text('Encerrar sessão', style: TextStyle(color: context.textPrimaryColor)),
        content: Text(
          'Você precisará entrar novamente para acessar o sistema.',
          style: TextStyle(color: context.textSecondaryColor),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              ref.read(authNotifierProvider.notifier).logout();
            },
            child: const Text('Sair', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
  }

  static String _formatDate(DateTime date) =>
      '${date.day.toString().padLeft(2, '0')}/'
      '${date.month.toString().padLeft(2, '0')}/${date.year}';
}

class _IdentityCard extends StatelessWidget {
  final dynamic user;

  const _IdentityCard({required this.user});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.xxl),
      child: Row(
        children: [
          AppAvatar(name: user.fullName, size: 72),
          const SizedBox(width: AppSpacing.xl),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  user.fullName,
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: context.textPrimaryColor,
                    letterSpacing: -0.4,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  user.email,
                  style: TextStyle(fontSize: 13, color: context.textSecondaryColor),
                ),
                const SizedBox(height: AppSpacing.sm),
                Wrap(
                  spacing: AppSpacing.xs,
                  runSpacing: 4,
                  children: [
                    AppBadge(
                      label: user.roleLabel,
                      variant: user.managesCompany
                          ? AppBadgeVariant.purple
                          : AppBadgeVariant.primary,
                    ),
                    if (user.sectorName != null)
                      AppBadge(label: user.sectorName!, variant: AppBadgeVariant.neutral),
                    AppBadge(
                      label: user.isActive ? 'Ativo' : 'Inativo',
                      variant:
                          user.isActive ? AppBadgeVariant.success : AppBadgeVariant.error,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;
  final IconData icon;

  const _SectionTitle({required this.title, required this.icon});


  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 16, color: context.textMutedColor),
        const SizedBox(width: AppSpacing.sm),
        Text(
          title,
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w700,
            color: context.textPrimaryColor,
            letterSpacing: -0.2,
          ),
        ),
      ],
    );
  }
}

class _Divider extends StatelessWidget {
  const _Divider();

  @override
  Widget build(BuildContext context) {
    return Divider(height: AppSpacing.lg, color: context.borderColor);
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final bool isEmpty;

  const _InfoRow({
    required this.label,
    required this.value,
    required this.icon,
    this.isEmpty = false,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '$label: $value',
      child: Row(
        children: [
          Icon(icon, size: 17, color: context.textMutedColor),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            flex: 2,
            child: Text(
              label,
              style: TextStyle(fontSize: 12.5, color: context.textSecondaryColor),
            ),
          ),
          Expanded(
            flex: 3,
            child: Text(
              value,
              textAlign: TextAlign.right,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 13,
                fontWeight: isEmpty ? FontWeight.w400 : FontWeight.w600,
                color: isEmpty ? context.textMutedColor : context.textPrimaryColor,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
