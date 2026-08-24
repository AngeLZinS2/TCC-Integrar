import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../app/theme.dart';
import '../../app/theme_provider.dart';

class ThemeToggleButton extends ConsumerWidget {
  final bool compact;

  const ThemeToggleButton({
    super.key,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(themeNotifierProvider);
    final isDark = context.isDark;

    return Tooltip(
      message: isDark ? 'Mudar para Modo Claro' : 'Mudar para Modo Escuro',
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(AppRadius.pill),
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadius.pill),
          onTap: () {
            ref.read(themeNotifierProvider.notifier).toggleTheme(context);
          },
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: EdgeInsets.all(compact ? 6.0 : 8.0),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E293B) : AppColors.slate100,
              shape: BoxShape.circle,
              border: Border.all(
                color: isDark ? AppColors.darkBorder : AppColors.border,
                width: 1.0,
              ),
            ),
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 260),
              transitionBuilder: (child, anim) {
                return RotationTransition(
                  turns: anim,
                  child: ScaleTransition(scale: anim, child: child),
                );
              },
              child: isDark
                  ? const Icon(
                      Icons.light_mode_rounded,
                      key: ValueKey('light_mode_icon'),
                      size: 20,
                      color: Color(0xFFFBBF24), // Warm Amber Sun
                    )
                  : const Icon(
                      Icons.dark_mode_rounded,
                      key: ValueKey('dark_mode_icon'),
                      size: 20,
                      color: AppColors.slate700, // Slate Moon
                    ),
            ),
          ),
        ),
      ),
    );
  }
}

class ThemeSelectorSegmented extends ConsumerWidget {
  const ThemeSelectorSegmented({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentMode = ref.watch(themeNotifierProvider);
    final isDark = context.isDark;

    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF0F172A) : AppColors.slate100,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: context.borderColor),
      ),
      child: Row(
        children: [
          _buildOption(
            context,
            ref,
            mode: ThemeMode.light,
            label: 'Claro',
            icon: Icons.light_mode_rounded,
            isSelected: currentMode == ThemeMode.light,
          ),
          _buildOption(
            context,
            ref,
            mode: ThemeMode.dark,
            label: 'Escuro',
            icon: Icons.dark_mode_rounded,
            isSelected: currentMode == ThemeMode.dark,
          ),
          _buildOption(
            context,
            ref,
            mode: ThemeMode.system,
            label: 'Automático',
            icon: Icons.brightness_auto_rounded,
            isSelected: currentMode == ThemeMode.system,
          ),
        ],
      ),
    );
  }

  Widget _buildOption(
    BuildContext context,
    WidgetRef ref, {
    required ThemeMode mode,
    required String label,
    required IconData icon,
    required bool isSelected,
  }) {
    final isDark = context.isDark;

    return Expanded(
      child: InkWell(
        onTap: () => ref.read(themeNotifierProvider.notifier).setThemeMode(mode),
        borderRadius: BorderRadius.circular(AppRadius.sm),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected
                ? (isDark ? AppColors.darkCard : Colors.white)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(AppRadius.sm),
            boxShadow: isSelected ? context.shadowSm : null,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 16,
                color: isSelected
                    ? (isDark ? AppColors.primary400 : AppColors.primary)
                    : (isDark ? AppColors.darkTextMuted : AppColors.slate500),
              ),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  color: isSelected
                      ? (isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)
                      : (isDark ? AppColors.darkTextMuted : AppColors.slate600),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
