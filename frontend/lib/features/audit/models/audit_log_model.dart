class AuditLogModel {
  final int id;
  final int? actorId;
  final String actorName;
  final String action;
  final String actionDisplay;
  final String resourceType;
  final int? resourceId;
  final String resourceLabel;

  /// Frase pronta montada pelo backend — evita o app remontar a gramática.
  final String summary;

  final Map<String, dynamic> metadata;
  final DateTime? createdAt;

  const AuditLogModel({
    required this.id,
    this.actorId,
    this.actorName = '',
    required this.action,
    this.actionDisplay = '',
    this.resourceType = '',
    this.resourceId,
    this.resourceLabel = '',
    this.summary = '',
    this.metadata = const {},
    this.createdAt,
  });

  factory AuditLogModel.fromJson(Map<String, dynamic> json) {
    return AuditLogModel(
      id: json['id'] as int,
      actorId: json['actor'] as int?,
      actorName: json['actor_name'] as String? ?? '',
      action: json['action'] as String? ?? '',
      actionDisplay: json['action_display'] as String? ?? '',
      resourceType: json['resource_type'] as String? ?? '',
      resourceId: json['resource_id'] as int?,
      resourceLabel: json['resource_label'] as String? ?? '',
      summary: json['summary'] as String? ?? '',
      metadata: (json['metadata'] as Map?)?.cast<String, dynamic>() ?? const {},
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String)
          : null,
    );
  }
}

class AuditFilterOption {
  final String value;
  final String label;

  const AuditFilterOption({required this.value, required this.label});

  factory AuditFilterOption.fromJson(Map<String, dynamic> json) {
    return AuditFilterOption(
      value: json['value'] as String,
      label: json['label'] as String,
    );
  }
}
