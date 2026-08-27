import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../app/theme.dart';
import '../../../../app/theme_provider.dart';
import '../../../../core/widgets/app_avatar.dart';
import '../../../../core/widgets/app_badge.dart';
import '../../../auth/providers/auth_provider.dart';
import '../../../notifications/providers/notification_provider.dart';

class AppSidebar extends ConsumerWidget {
  final String currentRoute;

  const AppSidebar({
    super.key,
    required this.currentRoute,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final user = authState.user;
    final unreadCount = ref.watch(unreadNotificationsCountProvider);
    final isDark = context.isDark;

    return Container(
      width: 260,
      decoration: BoxDecoration(
        color: context.surfaceColor,
        border: Border(
          right: BorderSide(color: context.borderColor, width: 1),
        ),
      ),
      child: Column(
        children: [
          // ── App Brand Header ──────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl, vertical: AppSpacing.xxl),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [AppColors.primary, Color(0xFF3B82F6)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    boxShadow: AppShadows.primaryGlow,
                  ),
                  child: const Icon(Icons.rocket_launch_rounded, color: Colors.white, size: 22),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Onboarding',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: context.textPrimaryColor,
                          letterSpacing: -0.3,
                        ),
                      ),
                      Text(
                        'Portal Corporativo',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                          color: context.textMutedColor,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Divider(height: 1, color: context.borderColor),
          const SizedBox(height: AppSpacing.md),

          // ── Navigation Items ──────────────────────────────────────────
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
              children: user?.isOwner == true
                  ? [
                      // Dono do sistema não tem trilha pessoal — nav dedicado.
                      _SidebarItem(
                        icon: Icons.dashboard_outlined,
                        label: 'Painel',
                        isSelected: currentRoute == '/owner/dashboard',
                        onTap: () => context.go('/owner/dashboard'),
                      ),
                      _SidebarItem(
                        icon: Icons.apartment_outlined,
                        label: 'Empresas',
                        isSelected: currentRoute.startsWith('/owner/companies'),
                        onTap: () => context.go('/owner/companies'),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Divider(height: 1, color: context.borderColor),
                      const SizedBox(height: AppSpacing.sm),
                      _SidebarItem(
                        icon: Icons.person_outline_rounded,
                        label: 'Meu Perfil',
                        isSelected: currentRoute == '/profile',
                        onTap: () => context.go('/profile'),
                      ),
                    ]
                  : [
                      _SidebarItem(
                        icon: Icons.grid_view_rounded,
                        label: 'Início',
                        isSelected: currentRoute == '/onboarding',
                        onTap: () => context.go('/onboarding'),
                      ),
                      // Cada item é liberado pela PERMISSÃO, não pelo papel —
                      // assim adicionar um papel novo no backend não exige
                      // mexer nesta lista. A autorização real segue no servidor.
                      if (user?.canViewDashboard == true)
                        _SidebarItem(
                          icon: Icons.dashboard_outlined,
                          label: 'Painel',
                          isSelected: currentRoute == '/rh/dashboard',
                          onTap: () => context.go('/rh/dashboard'),
                        ),
                      if (user?.canViewEmployees == true)
                        _SidebarItem(
                          icon: Icons.groups_outlined,
                          label: user?.isGestor == true ? 'Minha Equipe' : 'Colaboradores',
                          isSelected: currentRoute.startsWith('/rh/collaborators'),
                          onTap: () => context.go('/rh/collaborators'),
                        ),
                      if (user?.canManageOrg == true) ...[
                        _SidebarItem(
                          icon: Icons.corporate_fare_outlined,
                          label: 'Setores',
                          isSelected: currentRoute == '/org/sectors',
                          onTap: () => context.go('/org/sectors'),
                        ),
                        _SidebarItem(
                          icon: Icons.work_outline_rounded,
                          label: 'Cargos',
                          isSelected: currentRoute == '/org/positions',
                          onTap: () => context.go('/org/positions'),
                        ),
                      ],
                      if (user?.canViewAudit == true)
                        _SidebarItem(
                          icon: Icons.history_rounded,
                          label: 'Auditoria',
                          isSelected: currentRoute == '/audit',
                          onTap: () => context.go('/audit'),
                        ),
                      // Unidades e Automações seguem `canEditCompany`, e não
                      // `managesCompany`: uma unidade errada reetiqueta todo
                      // mundo lotado nela, e uma automação dispara e-mail para
                      // a empresa inteira. É decisão de estrutura, não rotina
                      // de RH — e o backend recusa do mesmo jeito.
                      if (user?.canEditCompany == true) ...[
                        _SidebarItem(
                          icon: Icons.apartment_outlined,
                          label: 'Unidades',
                          isSelected: currentRoute.startsWith('/units'),
                          onTap: () => context.go('/units'),
                        ),
                        _SidebarItem(
                          icon: Icons.bolt_outlined,
                          label: 'Automações',
                          isSelected: currentRoute.startsWith('/automations'),
                          onTap: () => context.go('/automations'),
                        ),
                        _SidebarItem(
                          icon: Icons.cable_outlined,
                          label: 'Integração',
                          isSelected: currentRoute.startsWith('/integrations'),
                          onTap: () => context.go('/integrations'),
                        ),
                      ],
                      if (user?.managesCompany == true)
                        _SidebarItem(
                          icon: Icons.settings_outlined,
                          label: 'Configurações',
                          isSelected: currentRoute == '/company/settings',
                          onTap: () => context.go('/company/settings'),
                        ),
                      if (user?.canViewDashboard == true ||
                          user?.canViewEmployees == true ||
                          user?.canManageOrg == true) ...[
                        const SizedBox(height: AppSpacing.sm),
                        Divider(height: 1, color: context.borderColor),
                        const SizedBox(height: AppSpacing.sm),
                      ],
                      _SidebarItem(
                        icon: Icons.school_rounded,
                        label: 'Meus Treinamentos',
                        isSelected: currentRoute.startsWith('/courses'),
                        onTap: () => context.go('/courses'),
                      ),
                      _SidebarItem(
                        icon: Icons.task_alt_rounded,
                        label: 'Checklist',
                        isSelected: currentRoute == '/checklist',
                        onTap: () => context.go('/checklist'),
                      ),
                      _SidebarItem(
                        icon: Icons.checklist_rounded,
                        label: 'Tarefas',
                        isSelected: currentRoute.startsWith('/onboarding/tasks'),
                        onTap: () => context.go('/onboarding/tasks'),
                      ),
                      _SidebarItem(
                        icon: Icons.campaign_outlined,
                        label: 'Comunicados',
                        isSelected: currentRoute.startsWith('/communications'),
                        onTap: () => context.go('/communications'),
                      ),
                      _SidebarItem(
                        icon: Icons.event_available,
                        label: 'Eventos',
                        isSelected: currentRoute.startsWith('/events'),
                        onTap: () => context.go('/events'),
                      ),
                      _SidebarItem(
                        icon: Icons.folder_shared_outlined,
                        label: 'Documentos',
                        isSelected: currentRoute.startsWith('/documents'),
                        onTap: () => context.go('/documents'),
                      ),
                      _SidebarItem(
                        icon: Icons.forum_outlined,
                        label: 'Solicitações',
                        isSelected: currentRoute.startsWith('/requests'),
                        onTap: () => context.go('/requests'),
                      ),
                      _SidebarItem(
                        icon: Icons.folder_open_rounded,
                        label: 'Materiais',
                        isSelected: currentRoute == '/materials',
                        onTap: () => context.go('/materials'),
                      ),
                      _SidebarItem(
                        icon: Icons.notifications_none_rounded,
                        label: 'Notificações',
                        badgeCount: unreadCount,
                        isSelected: currentRoute == '/notifications',
                        onTap: () => context.go('/notifications'),
                      ),
                      _SidebarItem(
                        icon: Icons.groups_2_outlined,
                        label: 'Equipe',
                        isSelected: currentRoute == '/directory',
                        onTap: () => context.go('/directory'),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Divider(height: 1, color: context.borderColor),
                      const SizedBox(height: AppSpacing.sm),
                      _SidebarItem(
                        icon: Icons.person_outline_rounded,
                        label: 'Meu Perfil',
                        isSelected: currentRoute == '/profile',
                        onTap: () => context.go('/profile'),
                      ),
                    ],
            ),
          ),

          // ── Theme Switcher Row ────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.xs),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 8),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E293B) : AppColors.slate50,
                borderRadius: BorderRadius.circular(AppRadius.md),
                border: Border.all(color: context.borderColor),
              ),
              child: Row(
                children: [
                  Icon(
                    isDark ? Icons.dark_mode_rounded : Icons.light_mode_rounded,
                    size: 16,
                    color: isDark ? const Color(0xFFFBBF24) : AppColors.slate600,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      isDark ? 'Modo Escuro' : 'Modo Claro',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: context.textPrimaryColor,
                      ),
                    ),
                  ),
                  Switch(
                    value: isDark,
                    activeThumbColor: AppColors.primary,
                    activeTrackColor: const Color(0xFF1E3A8A),
                    inactiveThumbColor: AppColors.slate400,
                    inactiveTrackColor: AppColors.slate200,
                    onChanged: (_) {
                      ref.read(themeNotifierProvider.notifier).toggleTheme(context);
                    },
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                ],
              ),
            ),
          ),

          // ── User Footer ───────────────────────────────────────────────
          if (user != null) ...[
            Divider(height: 1, color: context.borderColor),
            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Container(
                padding: const EdgeInsets.all(AppSpacing.sm),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E293B) : AppColors.slate50,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  border: Border.all(color: context.borderColor),
                ),
                child: Row(
                  children: [
                    AppAvatar(name: user.fullName, size: 36),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            user.fullName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: context.textPrimaryColor,
                            ),
                          ),
                          const SizedBox(height: 2),
                          AppBadge(
                            label: user.isOwner
                                ? 'Dono do Sistema'
                                : user.isRHAdmin
                                    ? 'RH Admin'
                                    : (user.sectorName ?? 'Colaborador'),
                            variant: user.isOwner
                                ? AppBadgeVariant.warning
                                : user.isRHAdmin
                                    ? AppBadgeVariant.purple
                                    : AppBadgeVariant.primary,
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: Icon(
                        Icons.logout_rounded,
                        size: 18,
                        color: context.isDark ? AppColors.darkTextMuted : AppColors.slate400,
                      ),
                      tooltip: 'Sair da conta',
                      onPressed: () {
                        ref.read(authNotifierProvider.notifier).logout();
                      },
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SidebarItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isSelected;
  final VoidCallback onTap;
  final int badgeCount;

  const _SidebarItem({
    required this.icon,
    required this.label,
    required this.isSelected,
    required this.onTap,
    this.badgeCount = 0,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    final selectedBg = isDark ? const Color(0xFF1E3A8A).withValues(alpha: 0.4) : AppColors.primary50;
    final selectedFg = isDark ? AppColors.primary300 : AppColors.primary700;
    final unselectedFg = isDark ? AppColors.darkTextSecondary : AppColors.slate700;
    final unselectedIcon = isDark ? AppColors.darkTextMuted : AppColors.slate500;

    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadius.md),
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 11),
            decoration: BoxDecoration(
              color: isSelected ? selectedBg : Colors.transparent,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: isSelected && isDark
                  ? Border.all(color: const Color(0xFF1D4ED8).withValues(alpha: 0.4), width: 1)
                  : null,
            ),
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 20,
                  color: isSelected ? (isDark ? AppColors.primary400 : AppColors.primary) : unselectedIcon,
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                      color: isSelected ? selectedFg : unselectedFg,
                    ),
                  ),
                ),
                if (badgeCount > 0)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      borderRadius: BorderRadius.circular(AppRadius.pill),
                    ),
                    child: Text(
                      badgeCount > 9 ? '9+' : '$badgeCount',
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
