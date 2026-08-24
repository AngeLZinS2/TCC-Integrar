import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../../app/theme.dart';
import '../../../../core/widgets/app_progress.dart';
import '../../../../shared/models/course_model.dart';
import '../../../../shared/models/user_model.dart';

class HeroProgressCard extends StatelessWidget {
  final UserModel user;
  final List<CourseModel> courses;

  const HeroProgressCard({
    super.key,
    required this.user,
    required this.courses,
  });

  @override
  Widget build(BuildContext context) {
    final total = courses.length;
    final completed = courses.where((c) => c.userProgress.isCompleted).length;
    final progress = total > 0 ? (completed / total) : 0.0;
    final percent = (progress * 100).toInt();

    final inProgressCourses = courses.where((c) => c.userProgress.isInProgress).toList();
    final notStartedCourses = courses.where((c) => c.userProgress.isNotStarted).toList();
    final CourseModel? inProgressCourse = inProgressCourses.isNotEmpty
        ? inProgressCourses.first
        : (notStartedCourses.isNotEmpty ? notStartedCourses.first : (courses.isNotEmpty ? courses.first : null));

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.xxl),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0F172A), Color(0xFF1E293B), Color(0xFF1E3A8A)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppRadius.xl),
        boxShadow: AppShadows.md,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(AppRadius.pill),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.auto_awesome_rounded, size: 13, color: Color(0xFFFBBF24)),
                          SizedBox(width: 5),
                          Text(
                            'Jornada de Integração',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                              letterSpacing: 0.3,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      'Olá, ${user.fullName.split(' ').first} 👋',
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      percent == 100
                          ? 'Parabéns! Você concluiu todos os treinamentos da sua integração.'
                          : 'Sua integração está avançando com sucesso.',
                      style: const TextStyle(
                        fontSize: 13,
                        color: Color(0xFF94A3B8),
                      ),
                    ),
                  ],
                ),
              ),

              // Big Percentage Display
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(AppRadius.lg),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
                ),
                child: Column(
                  children: [
                    Text(
                      '$percent%',
                      style: const TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.w900,
                        color: Color(0xFF38BDF8),
                        letterSpacing: -1.0,
                      ),
                    ),
                    const Text(
                      'CONCLUÍDO',
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF94A3B8),
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xl),

          // Progress Bar
          AppProgress(
            value: progress,
            height: 8,
            color: const Color(0xFF10B981),
            backgroundColor: Colors.white.withValues(alpha: 0.15),
          ),
          const SizedBox(height: AppSpacing.md),

          // Footer Row
          Row(
            children: [
              Expanded(
                child: Text(
                  '$completed de $total etapas concluídas',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFFCBD5E1),
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              if (inProgressCourse != null && percent < 100)
                InkWell(
                  onTap: () => context.push('/courses/${inProgressCourse.id}'),
                  borderRadius: BorderRadius.circular(AppRadius.pill),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      borderRadius: BorderRadius.circular(AppRadius.pill),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Continuar treinamento',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                          ),
                        ),
                        SizedBox(width: 4),
                        Icon(Icons.arrow_forward_rounded, size: 14, color: Colors.white),
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
