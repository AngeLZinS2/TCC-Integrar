class CompanyModel {
  final int id;
  final String name;
  final bool isActive;
  final DateTime? createdAt;
  final int totalCollaborators;
  final double avgCourseCompletionPercent;
  final double avgChecklistCompletionPercent;

  const CompanyModel({
    required this.id,
    required this.name,
    required this.isActive,
    this.createdAt,
    required this.totalCollaborators,
    required this.avgCourseCompletionPercent,
    required this.avgChecklistCompletionPercent,
  });

  factory CompanyModel.fromJson(Map<String, dynamic> json) {
    return CompanyModel(
      id: json['id'] as int,
      name: json['name'] as String,
      isActive: json['is_active'] as bool,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'] as String) : null,
      totalCollaborators: json['total_collaborators'] as int? ?? 0,
      avgCourseCompletionPercent: (json['avg_course_completion_percent'] as num?)?.toDouble() ?? 0.0,
      avgChecklistCompletionPercent: (json['avg_checklist_completion_percent'] as num?)?.toDouble() ?? 0.0,
    );
  }
}
