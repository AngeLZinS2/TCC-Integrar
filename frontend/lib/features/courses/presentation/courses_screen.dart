import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_skeleton.dart';
import '../../auth/providers/auth_provider.dart';
import '../providers/course_provider.dart';
import 'widgets/course_card.dart';
import 'widgets/course_filter_segmented.dart';

class CoursesScreen extends ConsumerStatefulWidget {
  const CoursesScreen({super.key});

  @override
  ConsumerState<CoursesScreen> createState() => _CoursesScreenState();
}

class _CoursesScreenState extends ConsumerState<CoursesScreen> {
  String _selectedFilter = 'all';
  final String _searchQuery = '';

  @override
  Widget build(BuildContext context) {
    final coursesAsync = ref.watch(coursesListProvider);
    final user = ref.watch(authNotifierProvider).user;
    final canManageCourses = user?.canManageCourses ?? false;

    return Scaffold(
      backgroundColor: context.scaffoldBg,
      body: RefreshIndicator(
        onRefresh: () => ref.read(coursesListProvider.notifier).loadCourses(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Page Header
              AppSectionHeader(
                title: 'Meus Treinamentos',
                subtitle: 'Acesse os treinamentos obrigatórios e complementares da sua trilha.',
                trailing: Wrap(
                  spacing: AppSpacing.sm,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    if (canManageCourses)
                      AppButton(
                        text: 'Novo Treinamento',
                        icon: Icons.add_circle_outline_rounded,
                        size: AppButtonSize.sm,
                        onPressed: () => context.push('/courses/new'),
                      ),
                    CourseFilterSegmented(
                      selectedFilter: _selectedFilter,
                      onFilterChanged: (filter) => setState(() => _selectedFilter = filter),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.lg),

              // Courses Grid / List
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
                  itemCount: 4,
                  itemBuilder: (_, __) => const AppSkeleton.card(height: 220),
                ),
                error: (err, _) => AppErrorState(
                  message: 'Não foi possível carregar seus treinamentos. Verifique sua conexão.',
                  onRetry: () => ref.read(coursesListProvider.notifier).loadCourses(),
                ),
                data: (courses) {
                  final filtered = courses.where((c) {
                    if (_selectedFilter == 'in_progress' && !c.userProgress.isInProgress) return false;
                    if (_selectedFilter == 'completed' && !c.userProgress.isCompleted) return false;
                    if (_searchQuery.isNotEmpty &&
                        !c.title.toLowerCase().contains(_searchQuery.toLowerCase())) {
                      return false;
                    }
                    return true;
                  }).toList();

                  if (filtered.isEmpty) {
                    return AppEmptyState(
                      icon: Icons.school_outlined,
                      title: 'Nenhum treinamento encontrado',
                      description: _selectedFilter == 'completed'
                          ? 'Você ainda não concluiu nenhum treinamento da sua trilha.'
                          : (_selectedFilter == 'in_progress'
                              ? 'Você não tem nenhum treinamento em andamento no momento.'
                              : 'Nenhum treinamento foi cadastrado para o seu setor ainda.'),
                      actionText: _selectedFilter != 'all' ? 'Ver todos os treinamentos' : null,
                      onAction: _selectedFilter != 'all'
                          ? () => setState(() => _selectedFilter = 'all')
                          : null,
                    );
                  }

                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 420,
                      mainAxisExtent: 230,
                      crossAxisSpacing: AppSpacing.lg,
                      mainAxisSpacing: AppSpacing.lg,
                    ),
                    itemCount: filtered.length,
                    itemBuilder: (context, index) {
                      final course = filtered[index];
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
