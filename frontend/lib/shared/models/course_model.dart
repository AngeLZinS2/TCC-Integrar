class ContentModel {
  final int id;
  final int course;
  final String type; // 'video', 'pdf', 'text'
  final String typeDisplay;
  final String fileUrl;
  final int order;

  const ContentModel({
    required this.id,
    required this.course,
    required this.type,
    required this.typeDisplay,
    required this.fileUrl,
    required this.order,
  });

  factory ContentModel.fromJson(Map<String, dynamic> json) {
    return ContentModel(
      id: json['id'] as int,
      course: json['course'] as int,
      type: json['type'] as String,
      typeDisplay: json['type_display'] as String? ?? json['type'] as String,
      fileUrl: json['file_url'] as String,
      order: json['order'] as int? ?? 0,
    );
  }
}

class UserCourseProgress {
  final String status; // 'not_started', 'in_progress', 'completed'
  final String statusDisplay;
  final DateTime? completedAt;

  const UserCourseProgress({
    required this.status,
    required this.statusDisplay,
    this.completedAt,
  });

  bool get isCompleted => status == 'completed';
  bool get isInProgress => status == 'in_progress';
  bool get isNotStarted => status == 'not_started';

  factory UserCourseProgress.fromJson(Map<String, dynamic> json) {
    return UserCourseProgress(
      status: json['status'] as String? ?? 'not_started',
      statusDisplay: json['status_display'] as String? ?? 'Não iniciado',
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'] as String)
          : null,
    );
  }
}

class CourseModel {
  final int id;
  final String title;
  final String description;
  final int? sector;
  final String? sectorName;
  final int? position;
  final String? positionName;
  final int order;
  final int? prerequisite;
  final String? prerequisiteTitle;
  final bool isLocked;
  final List<ContentModel> contents;
  final UserCourseProgress userProgress;

  const CourseModel({
    required this.id,
    required this.title,
    required this.description,
    this.sector,
    this.sectorName,
    this.position,
    this.positionName,
    required this.order,
    this.prerequisite,
    this.prerequisiteTitle,
    this.isLocked = false,
    required this.contents,
    required this.userProgress,
  });

  bool get isGeneral => sector == null;

  factory CourseModel.fromJson(Map<String, dynamic> json) {
    final rawContents = json['contents'] as List<dynamic>? ?? [];
    final contentsList = rawContents
        .map((c) => ContentModel.fromJson(c as Map<String, dynamic>))
        .toList();

    final rawProgress = json['user_progress'] as Map<String, dynamic>? ?? {};
    final progress = UserCourseProgress.fromJson(rawProgress);

    return CourseModel(
      id: json['id'] as int,
      title: json['title'] as String,
      description: json['description'] as String? ?? '',
      sector: json['sector'] as int?,
      sectorName: json['sector_name'] as String?,
      position: json['position'] as int?,
      positionName: json['position_name'] as String?,
      order: json['order'] as int? ?? 0,
      prerequisite: json['prerequisite'] as int?,
      prerequisiteTitle: json['prerequisite_title'] as String?,
      isLocked: json['is_locked'] as bool? ?? false,
      contents: contentsList,
      userProgress: progress,
    );
  }

  CourseModel copyWith({
    int? id,
    String? title,
    String? description,
    int? sector,
    String? sectorName,
    int? position,
    String? positionName,
    int? order,
    int? prerequisite,
    String? prerequisiteTitle,
    bool? isLocked,
    List<ContentModel>? contents,
    UserCourseProgress? userProgress,
  }) {
    return CourseModel(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      sector: sector ?? this.sector,
      sectorName: sectorName ?? this.sectorName,
      position: position ?? this.position,
      positionName: positionName ?? this.positionName,
      order: order ?? this.order,
      prerequisite: prerequisite ?? this.prerequisite,
      prerequisiteTitle: prerequisiteTitle ?? this.prerequisiteTitle,
      isLocked: isLocked ?? this.isLocked,
      contents: contents ?? this.contents,
      userProgress: userProgress ?? this.userProgress,
    );
  }
}
