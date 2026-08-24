class ChecklistItemModel {
  final int id;
  final String title;
  final String deadline; // 'day1', 'week1', 'month1'
  final String deadlineDisplay;
  final int? sector;
  final String? sectorName;
  final int order;
  final bool isCompleted;
  final DateTime? completedAt;

  const ChecklistItemModel({
    required this.id,
    required this.title,
    required this.deadline,
    required this.deadlineDisplay,
    this.sector,
    this.sectorName,
    required this.order,
    required this.isCompleted,
    this.completedAt,
  });

  bool get isGeneral => sector == null;

  factory ChecklistItemModel.fromJson(Map<String, dynamic> json) {
    final progress = json['user_progress'] as Map<String, dynamic>? ?? {};

    return ChecklistItemModel(
      id: json['id'] as int,
      title: json['title'] as String,
      deadline: json['deadline'] as String? ?? 'day1',
      deadlineDisplay: json['deadline_display'] as String? ?? 'Dia 1',
      sector: json['sector'] as int?,
      sectorName: json['sector_name'] as String?,
      order: json['order'] as int? ?? 0,
      isCompleted: progress['completed'] as bool? ?? false,
      completedAt: progress['completed_at'] != null
          ? DateTime.tryParse(progress['completed_at'] as String)
          : null,
    );
  }

  ChecklistItemModel copyWith({
    int? id,
    String? title,
    String? deadline,
    String? deadlineDisplay,
    int? sector,
    String? sectorName,
    int? order,
    bool? isCompleted,
    DateTime? completedAt,
  }) {
    return ChecklistItemModel(
      id: id ?? this.id,
      title: title ?? this.title,
      deadline: deadline ?? this.deadline,
      deadlineDisplay: deadlineDisplay ?? this.deadlineDisplay,
      sector: sector ?? this.sector,
      sectorName: sectorName ?? this.sectorName,
      order: order ?? this.order,
      isCompleted: isCompleted ?? this.isCompleted,
      completedAt: completedAt ?? this.completedAt,
    );
  }
}
