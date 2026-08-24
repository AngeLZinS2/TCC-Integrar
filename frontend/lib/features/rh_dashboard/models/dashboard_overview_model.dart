class CourseStatusDistribution {
  final int notStarted;
  final int inProgress;
  final int completed;

  const CourseStatusDistribution({
    required this.notStarted,
    required this.inProgress,
    required this.completed,
  });

  int get total => notStarted + inProgress + completed;

  factory CourseStatusDistribution.fromJson(Map<String, dynamic> json) {
    return CourseStatusDistribution(
      notStarted: json['not_started'] as int? ?? 0,
      inProgress: json['in_progress'] as int? ?? 0,
      completed: json['completed'] as int? ?? 0,
    );
  }
}

class SectorBreakdown {
  final int sectorId;
  final String sectorName;
  final int collaborators;
  final double avgCoursePercent;
  final double avgChecklistPercent;

  const SectorBreakdown({
    required this.sectorId,
    required this.sectorName,
    required this.collaborators,
    required this.avgCoursePercent,
    required this.avgChecklistPercent,
  });

  factory SectorBreakdown.fromJson(Map<String, dynamic> json) {
    return SectorBreakdown(
      sectorId: json['sector_id'] as int,
      sectorName: json['sector_name'] as String,
      collaborators: json['collaborators'] as int,
      avgCoursePercent: (json['avg_course_percent'] as num).toDouble(),
      avgChecklistPercent: (json['avg_checklist_percent'] as num).toDouble(),
    );
  }
}

class DashboardOverviewModel {
  final int totalCollaborators;
  final int activeCollaborators;
  final int inactiveCollaborators;
  final int hiredLast30Days;
  final int onboardingCompleted;
  final int onboardingInProgress;
  final int onboardingOverdue;
  final int onboardingNotStarted;
  final double onboardingPercent;
  final int activeLast30Days;
  final int neverLoggedIn;
  final double avgCourseCompletionPercent;
  final double avgChecklistCompletionPercent;
  final int fullyCompletedCount;
  final int overdueCollaboratorsCount;
  final CourseStatusDistribution courseStatusDistribution;
  final List<SectorBreakdown> bySector;

  const DashboardOverviewModel({
    required this.totalCollaborators,
    this.activeCollaborators = 0,
    this.inactiveCollaborators = 0,
    this.hiredLast30Days = 0,
    this.onboardingCompleted = 0,
    this.onboardingInProgress = 0,
    this.onboardingOverdue = 0,
    this.onboardingNotStarted = 0,
    this.onboardingPercent = 0,
    required this.activeLast30Days,
    required this.neverLoggedIn,
    required this.avgCourseCompletionPercent,
    required this.avgChecklistCompletionPercent,
    required this.fullyCompletedCount,
    required this.overdueCollaboratorsCount,
    required this.courseStatusDistribution,
    required this.bySector,
  });

  factory DashboardOverviewModel.fromJson(Map<String, dynamic> json) {
    return DashboardOverviewModel(
      totalCollaborators: json['total_collaborators'] as int,
      activeCollaborators: json['active_collaborators'] as int? ?? 0,
      inactiveCollaborators: json['inactive_collaborators'] as int? ?? 0,
      hiredLast30Days: json['hired_last_30_days'] as int? ?? 0,
      onboardingCompleted: json['onboarding_completed'] as int? ?? 0,
      onboardingInProgress: json['onboarding_in_progress'] as int? ?? 0,
      onboardingOverdue: json['onboarding_overdue'] as int? ?? 0,
      onboardingNotStarted: json['onboarding_not_started'] as int? ?? 0,
      onboardingPercent: (json['onboarding_percent'] as num?)?.toDouble() ?? 0,
      activeLast30Days: json['active_last_30_days'] as int,
      neverLoggedIn: json['never_logged_in'] as int,
      avgCourseCompletionPercent: (json['avg_course_completion_percent'] as num).toDouble(),
      avgChecklistCompletionPercent: (json['avg_checklist_completion_percent'] as num).toDouble(),
      fullyCompletedCount: json['fully_completed_count'] as int,
      overdueCollaboratorsCount: json['overdue_collaborators_count'] as int? ?? 0,
      courseStatusDistribution: CourseStatusDistribution.fromJson(
        json['course_status_distribution'] as Map<String, dynamic>,
      ),
      bySector: (json['by_sector'] as List<dynamic>)
          .map((e) => SectorBreakdown.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
