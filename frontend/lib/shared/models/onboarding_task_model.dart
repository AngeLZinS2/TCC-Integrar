// Tarefas e templates de integração.
//
// `employee` é de quem é a integração; `assignedTo` é quem executa. São
// quase sempre pessoas diferentes, e a tela precisa mostrar as duas — é o
// que responde "quem está devendo o quê".

class TaskPerson {
  final int id;
  final String fullName;
  final String? positionName;

  const TaskPerson({
    required this.id,
    required this.fullName,
    this.positionName,
  });

  factory TaskPerson.fromJson(Map<String, dynamic> json) {
    return TaskPerson(
      id: json['id'] ?? 0,
      fullName: json['full_name'] ?? '',
      positionName: json['position_name'],
    );
  }
}

class OnboardingTaskModel {
  final int id;
  final String title;
  final String description;
  final int employeeId;
  final TaskPerson? employee;
  final int? assignedToId;
  final TaskPerson? assignedTo;
  final String? dueDate;
  final String priority;
  final String priorityDisplay;
  final String status;
  final String statusDisplay;
  final bool isOverdue;
  final int daysLate;
  final int commentCount;
  final int attachmentCount;
  final String? completedAt;
  final List<TaskComment> comments;

  const OnboardingTaskModel({
    required this.id,
    required this.title,
    required this.description,
    required this.employeeId,
    this.employee,
    this.assignedToId,
    this.assignedTo,
    this.dueDate,
    required this.priority,
    required this.priorityDisplay,
    required this.status,
    required this.statusDisplay,
    required this.isOverdue,
    required this.daysLate,
    this.commentCount = 0,
    this.attachmentCount = 0,
    this.completedAt,
    this.comments = const [],
  });

  bool get isDone => status == 'completed';
  bool get isOpen => status == 'pending' || status == 'in_progress';

  factory OnboardingTaskModel.fromJson(Map<String, dynamic> json) {
    return OnboardingTaskModel(
      id: json['id'],
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      employeeId: json['employee'] ?? 0,
      employee: json['employee_detail'] != null
          ? TaskPerson.fromJson(json['employee_detail'])
          : null,
      assignedToId: json['assigned_to'],
      assignedTo: json['assigned_to_detail'] != null
          ? TaskPerson.fromJson(json['assigned_to_detail'])
          : null,
      dueDate: json['due_date'],
      priority: json['priority'] ?? 'normal',
      priorityDisplay: json['priority_display'] ?? '',
      status: json['status'] ?? 'pending',
      statusDisplay: json['status_display'] ?? '',
      isOverdue: json['is_overdue'] ?? false,
      daysLate: json['days_late'] ?? 0,
      commentCount: json['comment_count'] ?? 0,
      attachmentCount: json['attachment_count'] ?? 0,
      completedAt: json['completed_at'],
      comments: (json['comments'] as List<dynamic>? ?? const [])
          .map((e) => TaskComment.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class TaskComment {
  final int id;
  final String message;
  final bool isInternal;
  final String authorName;
  final String createdAt;

  const TaskComment({
    required this.id,
    required this.message,
    required this.isInternal,
    required this.authorName,
    required this.createdAt,
  });

  factory TaskComment.fromJson(Map<String, dynamic> json) {
    return TaskComment(
      id: json['id'],
      message: json['message'] ?? '',
      isInternal: json['is_internal'] ?? false,
      authorName: json['author_name'] ?? '',
      createdAt: json['created_at'] ?? '',
    );
  }
}

/// Resumo da integração de uma pessoa.
class OnboardingProgress {
  final int total;
  final int completed;
  final int pending;
  final int overdue;
  final int percent;

  const OnboardingProgress({
    required this.total,
    required this.completed,
    required this.pending,
    required this.overdue,
    required this.percent,
  });

  factory OnboardingProgress.fromJson(Map<String, dynamic> json) {
    return OnboardingProgress(
      total: json['total'] ?? 0,
      completed: json['completed'] ?? 0,
      pending: json['pending'] ?? 0,
      overdue: json['overdue'] ?? 0,
      percent: json['percent'] ?? 0,
    );
  }
}

class MyOnboarding {
  final OnboardingProgress progress;
  final List<OnboardingTaskModel> tasks;

  const MyOnboarding({required this.progress, required this.tasks});

  factory MyOnboarding.fromJson(Map<String, dynamic> json) {
    return MyOnboarding(
      progress: OnboardingProgress.fromJson(json['progress'] ?? const {}),
      tasks: (json['tasks'] as List<dynamic>? ?? const [])
          .map((e) => OnboardingTaskModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

// ── Templates ───────────────────────────────────────────────────────────────

class TemplateTaskModel {
  final int? id;
  final String title;
  final String description;
  final int daysOffset;
  final String responsible;
  final String responsibleDisplay;
  final String priority;
  final int order;

  const TemplateTaskModel({
    this.id,
    required this.title,
    this.description = '',
    required this.daysOffset,
    required this.responsible,
    this.responsibleDisplay = '',
    this.priority = 'normal',
    this.order = 0,
  });

  factory TemplateTaskModel.fromJson(Map<String, dynamic> json) {
    return TemplateTaskModel(
      id: json['id'],
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      daysOffset: json['days_offset'] ?? 0,
      responsible: json['responsible'] ?? 'employee',
      responsibleDisplay: json['responsible_display'] ?? '',
      priority: json['priority'] ?? 'normal',
      order: json['order'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'title': title,
        'description': description,
        'days_offset': daysOffset,
        'responsible': responsible,
        'priority': priority,
        'order': order,
      };
}

class OnboardingTemplateModel {
  final int id;
  final String name;
  final String description;
  final int? sector;
  final String? sectorName;
  final int? position;
  final String? positionName;
  final bool isActive;
  final bool applyAutomatically;
  final int taskCount;
  final List<TemplateTaskModel> tasks;

  const OnboardingTemplateModel({
    required this.id,
    required this.name,
    this.description = '',
    this.sector,
    this.sectorName,
    this.position,
    this.positionName,
    this.isActive = true,
    this.applyAutomatically = true,
    this.taskCount = 0,
    this.tasks = const [],
  });

  /// Como o roteiro aparece resumido na lista.
  String get scopeLabel {
    if (positionName != null) return '$sectorName · $positionName';
    if (sectorName != null) return sectorName!;
    return 'Todos os setores';
  }

  factory OnboardingTemplateModel.fromJson(Map<String, dynamic> json) {
    return OnboardingTemplateModel(
      id: json['id'],
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      sector: json['sector'],
      sectorName: json['sector_name'],
      position: json['position'],
      positionName: json['position_name'],
      isActive: json['is_active'] ?? true,
      applyAutomatically: json['apply_automatically'] ?? true,
      taskCount: json['task_count'] ?? 0,
      tasks: (json['tasks'] as List<dynamic>? ?? const [])
          .map((e) => TemplateTaskModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
