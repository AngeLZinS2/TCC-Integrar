import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../auth/providers/auth_provider.dart';
import '../../checklist/providers/checklist_provider.dart';
import '../../courses/presentation/widgets/course_card.dart';
import '../../courses/providers/course_provider.dart';
import '../../materials/providers/material_provider.dart';
import 'widgets/continue_course_card.dart';
import 'widgets/hero_progress_card.dart';

class OnboardingScreen extends ConsumerWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final user = authState.user;
    final coursesAsync = ref.watch(coursesListProvider);
    final checklistAsync = ref.watch(checklistProvider);
    final materialsAsync = ref.watch(materialsListProvider);
    final isDark = context.isDark;

    if (user == null) {
      return Scaffold(
        backgroundColor: context.scaffoldBg,
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(coursesListProvider.notifier).loadCourses();
          await ref.read(checklistProvider.notifier).loadChecklist();
          ref.invalidate(materialsListProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── 1. Hero Progress Section ─────────────────────────────
              coursesAsync.when(
                loading: () => const AppSkeleton.card(height: 180),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível calcular o progresso da integração.',
                  onRetry: () => ref.read(coursesListProvider.notifier).loadCourses(),
                ),
                data: (courses) => HeroProgressCard(user: user, courses: courses),
              ),
              const SizedBox(height: AppSpacing.xxl),

              // ── 2. Continue De Onde Parou ────────────────────────────
              coursesAsync.maybeWhen(
                data: (courses) {
                  final inProgress = courses.where((c) => c.userProgress.isInProgress).toList();
                  final nextCourse = inProgress.isNotEmpty
                      ? inProgress.first
                      : courses.where((c) => c.userProgress.isNotStarted).firstOrNull;

                  if (nextCourse != null && courses.any((c) => !c.userProgress.isCompleted)) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.xxl),
                      child: ContinueCourseCard(course: nextCourse),
                    );
                  }
                  return const SizedBox.shrink();
                },
                orElse: () => const SizedBox.shrink(),
              ),

              // ── 3. Quick Stats Grid ──────────────────────────────────
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth > 700;
                  return Row(
                    children: [
                      Expanded(
                        child: _StatCard(
                          icon: Icons.school_outlined,
                          iconColor: isDark ? AppColors.primary300 : AppColors.primary,
                          iconBgColor: isDark ? const Color(0xFF1E3A8A).withValues(alpha: 0.4) : AppColors.primary50,
                          title: 'Treinamentos',
                          value: coursesAsync.maybeWhen(
                            data: (list) => '${list.where((c) => c.userProgress.isCompleted).length}/${list.length}',
                            orElse: () => '-',
                          ),
                          subtitle: 'concluídos na trilha',
                          onTap: () => context.go('/courses'),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.lg),
                      Expanded(
                        child: _StatCard(
                          icon: Icons.task_alt_rounded,
                          iconColor: isDark ? AppColors.warningDarkText : AppColors.warning,
                          iconBgColor: isDark ? AppColors.warningDark.withValues(alpha: 0.4) : AppColors.warningLight,
                          title: 'Checklist',
                          value: checklistAsync.maybeWhen(
                            data: (list) => '${list.where((i) => i.isCompleted).length}/${list.length}',
                            orElse: () => '-',
                          ),
                          subtitle: 'tarefas realizadas',
                          onTap: () => context.go('/checklist'),
                        ),
                      ),
                      if (isWide) ...[
                        const SizedBox(width: AppSpacing.lg),
                        Expanded(
                          child: _StatCard(
                            icon: Icons.folder_open_rounded,
                            iconColor: isDark ? AppColors.purpleDarkText : AppColors.purple,
                            iconBgColor: isDark ? AppColors.purpleDark.withValues(alpha: 0.4) : AppColors.purpleLight,
                            title: 'Biblioteca',
                            value: materialsAsync.maybeWhen(
                              data: (list) => '${list.length}',
                              orElse: () => '-',
                            ),
                            subtitle: 'documentos disponíveis',
                            onTap: () => context.go('/materials'),
                          ),
                        ),
                      ],
                    ],
                  );
                },
              ),
              const SizedBox(height: AppSpacing.xxxl),

              // ── 4. Courses Grid ──────────────────────────────────────
              AppSectionHeader(
                title: 'Treinamentos Obrigatórios',
                subtitle: 'Treinamentos designados para o seu setor (${user.sectorName ?? "Geral"}) e cargo.',
                actionText: 'Ver catálogo completo →',
                onAction: () => context.go('/courses'),
              ),
              const SizedBox(height: AppSpacing.sm),

              coursesAsync.when(
                loading: () => GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 420,
                    mainAxisExtent: 220,
                    crossAxisSpacing: AppSpacing.lg,
                    mainAxisSpacing: AppSpacing.lg,
                  ),
                  itemCount: 2,
                  itemBuilder: (_, __) => const AppSkeleton.card(height: 220),
                ),
                error: (_, __) => const SizedBox.shrink(),
                data: (courses) {
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 420,
                      mainAxisExtent: 230,
                      crossAxisSpacing: AppSpacing.lg,
                      mainAxisSpacing: AppSpacing.lg,
                    ),
                    itemCount: courses.length,
                    itemBuilder: (context, index) {
                      final course = courses[index];
                      return CourseCard(
                        course: course,
                        onTap: () => context.push('/courses/${course.id}'),
                      );
                    },
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final Color iconBgColor;
  final String title;
  final String value;
  final String subtitle;
  final VoidCallback onTap;

  const _StatCard({
    required this.icon,
    required this.iconColor,
    required this.iconBgColor,
    required this.title,
    required this.value,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: onTap,
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: iconBgColor,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Icon(icon, size: 20, color: iconColor),
              ),
              const Spacer(),
              Icon(
                Icons.arrow_forward_ios_rounded,
                size: 12,
                color: context.isDark ? AppColors.darkTextMuted : AppColors.slate400,
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            value,
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: context.textPrimaryColor,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            title,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: context.textPrimaryColor,
            ),
          ),
          Text(
            subtitle,
            style: TextStyle(
              fontSize: 11,
              color: context.textMutedColor,
            ),
          ),
        ],
      ),
    );
  }
}
