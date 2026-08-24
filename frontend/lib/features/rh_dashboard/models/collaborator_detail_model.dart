import 'collaborator_row_model.dart';

class CollaboratorCourseStatus {
  final int id;
  final String title;
  final String status; // not_started | in_progress | completed
  final DateTime? completedAt;
  final DateTime? dueDate;
  final bool isOverdue;

  const CollaboratorCourseStatus({
    required this.id,
    required this.title,
    required this.status,
    this.completedAt,
    this.dueDate,
    this.isOverdue = false,
  });

  bool get isCompleted => status == 'completed';
  bool get isInProgress => status == 'in_progress';

  factory CollaboratorCourseStatus.fromJson(Map<String, dynamic> json) {
    return CollaboratorCourseStatus(
      id: json['id'] as int,
      title: json['title'] as String,
      status: json['status'] as String,
      completedAt:
          json['completed_at'] != null ? DateTime.tryParse(json['completed_at'] as String) : null,
      dueDate: json['due_date'] != null ? DateTime.tryParse(json['due_date'] as String) : null,
      isOverdue: json['is_overdue'] as bool? ?? false,
    );
  }
}

class CollaboratorChecklistStatus {
  final int id;
  final String title;
  final String deadline; // day1 | week1 | month1
  final bool completed;
  final DateTime? completedAt;
  final DateTime? dueDate;
  final bool isOverdue;

  const CollaboratorChecklistStatus({
    required this.id,
    required this.title,
    required this.deadline,
    required this.completed,
    this.completedAt,
    this.dueDate,
    this.isOverdue = false,
  });

  factory CollaboratorChecklistStatus.fromJson(Map<String, dynamic> json) {
    return CollaboratorChecklistStatus(
      id: json['id'] as int,
      title: json['title'] as String,
      deadline: json['deadline'] as String,
      completed: json['completed'] as bool,
      completedAt:
          json['completed_at'] != null ? DateTime.tryParse(json['completed_at'] as String) : null,
      dueDate: json['due_date'] != null ? DateTime.tryParse(json['due_date'] as String) : null,
      isOverdue: json['is_overdue'] as bool? ?? false,
    );
  }
}

class CollaboratorDetailModel extends CollaboratorRowModel {
  final List<CollaboratorCourseStatus> courses;
  final List<CollaboratorChecklistStatus> checklistItems;

  const CollaboratorDetailModel({
    required super.id,
    required super.fullName,
    required super.email,
    super.sectorName,
    super.positionName,
    required super.isActive,
    super.lastLogin,
    super.hireDate,
    required super.coursesTotal,
    required super.coursesCompleted,
    required super.coursesPercent,
    required super.checklistTotal,
    required super.checklistCompleted,
    required super.checklistPercent,
    required super.overallPercent,
    required super.overdueCount,
    required this.courses,
    required this.checklistItems,
  });

  factory CollaboratorDetailModel.fromJson(Map<String, dynamic> json) {
    return CollaboratorDetailModel(
      id: json['id'] as int,
      fullName: json['full_name'] as String,
      email: json['email'] as String,
      sectorName: json['sector_name'] as String?,
      positionName: json['position_name'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      lastLogin: json['last_login'] != null ? DateTime.tryParse(json['last_login'] as String) : null,
      hireDate: json['hire_date'] != null ? DateTime.tryParse(json['hire_date'] as String) : null,
      coursesTotal: json['courses_total'] as int,
      coursesCompleted: json['courses_completed'] as int,
      coursesPercent: json['courses_percent'] as int,
      checklistTotal: json['checklist_total'] as int,
      checklistCompleted: json['checklist_completed'] as int,
      checklistPercent: json['checklist_percent'] as int,
      overallPercent: json['overall_percent'] as int,
      overdueCount: json['overdue_count'] as int? ?? 0,
      courses: (json['courses'] as List<dynamic>)
          .map((e) => CollaboratorCourseStatus.fromJson(e as Map<String, dynamic>))
          .toList(),
      checklistItems: (json['checklist_items'] as List<dynamic>)
          .map((e) => CollaboratorChecklistStatus.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
