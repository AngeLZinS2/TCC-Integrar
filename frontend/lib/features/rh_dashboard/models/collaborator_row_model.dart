class CollaboratorRowModel {
  final int id;
  final String fullName;
  final String email;
  final String? sectorName;
  final String? positionName;
  final bool isActive;
  final bool isSectorLeader;
  final DateTime? lastLogin;
  final DateTime? hireDate;
  final int coursesTotal;
  final int coursesCompleted;
  final int coursesPercent;
  final int checklistTotal;
  final int checklistCompleted;
  final int checklistPercent;
  final int overallPercent;
  final int overdueCount;

  const CollaboratorRowModel({
    required this.id,
    required this.fullName,
    required this.email,
    this.sectorName,
    this.positionName,
    required this.isActive,
    this.isSectorLeader = false,
    this.lastLogin,
    this.hireDate,
    required this.coursesTotal,
    required this.coursesCompleted,
    required this.coursesPercent,
    required this.checklistTotal,
    required this.checklistCompleted,
    required this.checklistPercent,
    required this.overallPercent,
    required this.overdueCount,
  });

  bool get neverLoggedIn => lastLogin == null;
  bool get isOverdue => overdueCount > 0;

  factory CollaboratorRowModel.fromJson(Map<String, dynamic> json) {
    return CollaboratorRowModel(
      id: json['id'] as int,
      fullName: json['full_name'] as String,
      email: json['email'] as String,
      sectorName: json['sector_name'] as String?,
      positionName: json['position_name'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      isSectorLeader: json['is_sector_leader'] as bool? ?? false,
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
    );
  }
}
