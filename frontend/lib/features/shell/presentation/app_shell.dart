import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../auth/providers/auth_provider.dart';
import 'widgets/app_header.dart';
import 'widgets/app_sidebar.dart';

class AppShell extends ConsumerWidget {
  final Widget child;
  final String location;

  const AppShell({
    super.key,
    required this.child,
    required this.location,
  });

  int _calculateSelectedIndex(String loc, bool isOwner, bool isRHAdmin) {
    if (isOwner) {
      if (loc.startsWith('/owner/companies')) return 1;
      if (loc.startsWith('/profile')) return 2;
      return 0; // /owner/dashboard (Painel)
    }
    if (isRHAdmin) {
      if (loc.startsWith('/rh/dashboard')) return 1;
      if (loc.startsWith('/rh/collaborators')) return 2;
      if (loc.startsWith('/notifications')) return 3;
      if (loc.startsWith('/directory')) return 4;
      if (loc.startsWith('/profile')) return 5;
      return 0; // /onboarding (Início)
    }
    if (loc.startsWith('/courses')) return 1;
    if (loc.startsWith('/checklist')) return 2;
    if (loc.startsWith('/materials')) return 3;
    if (loc.startsWith('/directory')) return 4;
    if (loc.startsWith('/profile')) return 5;
    return 0; // /onboarding (Início)
  }

  void _onBottomNavTapped(BuildContext context, int index, bool isOwner, bool isRHAdmin) {
    if (isOwner) {
      switch (index) {
        case 0:
          context.go('/owner/dashboard');
        case 1:
          context.go('/owner/companies');
        case 2:
          context.go('/profile');
      }
      return;
    }
    if (isRHAdmin) {
      switch (index) {
        case 0:
          context.go('/onboarding');
        case 1:
          context.go('/rh/dashboard');
        case 2:
          context.go('/rh/collaborators');
        case 3:
          context.go('/notifications');
        case 4:
          context.go('/directory');
        case 5:
          context.go('/profile');
      }
      return;
    }
    switch (index) {
      case 0:
        context.go('/onboarding');
        break;
      case 1:
        context.go('/courses');
        break;
      case 2:
        context.go('/checklist');
        break;
      case 3:
        context.go('/materials');
        break;
      case 4:
        context.go('/directory');
        break;
      case 5:
        context.go('/profile');
        break;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final width = MediaQuery.of(context).size.width;
    final isDesktop = width >= 900;
    final user = ref.watch(authNotifierProvider).user;
    final isOwner = user?.isOwner == true;
    final isRHAdmin = user?.isRHAdmin == true;
    final selectedIndex = _calculateSelectedIndex(location, isOwner, isRHAdmin);
    final isDark = context.isDark;

    if (isDesktop) {
      return Scaffold(
        backgroundColor: context.scaffoldBg,
        body: Row(
          children: [
            AppSidebar(currentRoute: location),
            Expanded(
              child: Column(
                children: [
                  const AppHeader(isMobile: false),
                  Expanded(
                    child: SelectionArea(child: child),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    // Mobile / Tablet layout
    return Scaffold(
      backgroundColor: context.scaffoldBg,
      appBar: const AppHeader(isMobile: true),
      body: child,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: context.surfaceColor,
          border: Border(
            top: BorderSide(color: context.borderColor, width: 1),
          ),
        ),
        child: BottomNavigationBar(
          currentIndex: selectedIndex,
          onTap: (idx) => _onBottomNavTapped(context, idx, isOwner, isRHAdmin),
          type: BottomNavigationBarType.fixed,
          backgroundColor: context.surfaceColor,
          selectedItemColor: isDark ? AppColors.primary400 : AppColors.primary,
          unselectedItemColor: isDark ? AppColors.darkTextMuted : AppColors.slate400,
          selectedFontSize: 11,
          unselectedFontSize: 11,
          selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w700),
          unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500),
          elevation: 0,
          items: isOwner
              ? const [
                  BottomNavigationBarItem(
                    icon: Icon(Icons.dashboard_outlined),
                    label: 'Painel',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.apartment_outlined),
                    label: 'Empresas',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.person_outline_rounded),
                    label: 'Perfil',
                  ),
                ]
              : isRHAdmin
                  ? const [
                      BottomNavigationBarItem(
                        icon: Icon(Icons.grid_view_rounded),
                        label: 'Início',
                      ),
                      BottomNavigationBarItem(
                        icon: Icon(Icons.dashboard_outlined),
                        label: 'Painel',
                      ),
                      BottomNavigationBarItem(
                        icon: Icon(Icons.groups_outlined),
                        label: 'Colaboradores',
                      ),
                      BottomNavigationBarItem(
                        icon: Icon(Icons.notifications_none_rounded),
                        label: 'Notificações',
                      ),
                      BottomNavigationBarItem(
                        icon: Icon(Icons.groups_2_outlined),
                        label: 'Equipe',
                      ),
                      BottomNavigationBarItem(
                        icon: Icon(Icons.person_outline_rounded),
                        label: 'Perfil',
                      ),
                    ]
                  : const [
                  BottomNavigationBarItem(
                    icon: Icon(Icons.grid_view_rounded),
                    label: 'Início',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.school_rounded),
                    label: 'Treinamentos',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.task_alt_rounded),
                    label: 'Checklist',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.folder_open_rounded),
                    label: 'Biblioteca',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.groups_2_outlined),
                    label: 'Equipe',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.person_outline_rounded),
                    label: 'Perfil',
                  ),
                ],
        ),
      ),
    );
  }
}
