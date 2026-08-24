import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../app/theme.dart';
import '../../../../core/widgets/app_avatar.dart';
import '../../../../core/widgets/theme_toggle_button.dart';
import '../../../auth/providers/auth_provider.dart';
import '../../../notifications/providers/notification_provider.dart';

class AppHeader extends ConsumerWidget implements PreferredSizeWidget {
  final bool isMobile;

  const AppHeader({
    super.key,
    this.isMobile = false,
  });

  @override
  Size get preferredSize => const Size.fromHeight(68.0);

  String _getGreeting() {
    final hour = DateTime.now().hour;
    if (hour >= 5 && hour < 12) return 'Bom dia';
    if (hour >= 12 && hour < 18) return 'Boa tarde';
    return 'Boa noite';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final user = authState.user;
    final unreadCount = ref.watch(unreadNotificationsCountProvider);

    final firstName = user?.fullName.split(' ').first ?? 'Colaborador';
    final greeting = '${_getGreeting()}, $firstName 👋';

    return Container(
      height: 68,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xxl),
      decoration: BoxDecoration(
        color: context.surfaceColor,
        border: Border(
          bottom: BorderSide(color: context.borderColor, width: 1),
        ),
      ),
      child: Row(
        children: [
          // ── Greeting Title (Desktop/Tablet) ───────────────────────────
          if (!isMobile)
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    greeting,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: context.textPrimaryColor,
                      letterSpacing: -0.3,
                    ),
                  ),
                  Text(
                    'Vamos continuar sua jornada de integração corporativa.',
                    style: TextStyle(
                      fontSize: 12,
                      color: context.textSecondaryColor,
                    ),
                  ),
                ],
              ),
            )
          else
            Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(AppRadius.sm),
                  ),
                  child: const Icon(Icons.rocket_launch_rounded, color: Colors.white, size: 18),
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  'Onboarding',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: context.textPrimaryColor,
                  ),
                ),
              ],
            ),

          if (isMobile) const Spacer(),

          // ── Action Buttons (Theme Toggle + Notifications + Avatar Menu)
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Theme Toggle Button
              const ThemeToggleButton(compact: true),
              const SizedBox(width: AppSpacing.sm),

              // Notification Bell
              Stack(
                alignment: Alignment.topRight,
                children: [
                  IconButton(
                    icon: Icon(
                      Icons.notifications_outlined,
                      size: 22,
                      color: context.isDark ? AppColors.darkTextSecondary : AppColors.slate700,
                    ),
                    tooltip: 'Notificações',
                    onPressed: () => context.go('/notifications'),
                  ),
                  if (unreadCount > 0)
                    Positioned(
                      top: 8,
                      right: 8,
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: const BoxDecoration(
                          color: AppColors.primary,
                          shape: BoxShape.circle,
                        ),
                        constraints: const BoxConstraints(
                          minWidth: 8,
                          minHeight: 8,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(width: AppSpacing.sm),

              // Profile Avatar Menu
              if (user != null)
                InkWell(
                  borderRadius: BorderRadius.circular(AppRadius.pill),
                  onTap: () => context.go('/profile'),
                  child: Padding(
                    padding: const EdgeInsets.all(4.0),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        AppAvatar(name: user.fullName, size: 34),
                        if (!isMobile) ...[
                          const SizedBox(width: AppSpacing.sm),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 120),
                            child: Text(
                              firstName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: context.textPrimaryColor,
                              ),
                            ),
                          ),
                          Icon(
                            Icons.keyboard_arrow_down_rounded,
                            size: 16,
                            color: context.isDark ? AppColors.darkTextMuted : AppColors.slate400,
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
