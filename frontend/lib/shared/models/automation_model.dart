// Automações: gatilho + condição opcional + ação.
//
// O catálogo de eventos e ações vem da API (`/automations/catalog/`) em
// vez de ser uma cópia aqui: uma cópia desatualizada ofereceria ao usuário
// um gatilho que o backend recusa.

class CatalogOption {
  final String value;
  final String label;

  const CatalogOption({required this.value, required this.label});

  factory CatalogOption.fromJson(Map<String, dynamic> json) {
    return CatalogOption(
      value: json['value'] ?? '',
      label: json['label'] ?? '',
    );
  }
}

class AutomationCatalog {
  final List<CatalogOption> events;
  final List<CatalogOption> actions;
  final List<CatalogOption> targets;
  final List<CatalogOption> conditionFields;
  final List<CatalogOption> operators;

  const AutomationCatalog({
    required this.events,
    required this.actions,
    required this.targets,
    required this.conditionFields,
    required this.operators,
  });

  factory AutomationCatalog.fromJson(Map<String, dynamic> json) {
    List<CatalogOption> lista(String chave) =>
        (json[chave] as List<dynamic>? ?? const [])
            .map((e) => CatalogOption.fromJson(e as Map<String, dynamic>))
            .toList();

    return AutomationCatalog(
      events: lista('events'),
      actions: lista('actions'),
      targets: lista('targets'),
      conditionFields: lista('condition_fields'),
      operators: lista('operators'),
    );
  }
}

class AutomationCondition {
  final int? id;
  final String field;
  final String fieldDisplay;
  final String operator;
  final String value;

  const AutomationCondition({
    this.id,
    required this.field,
    this.fieldDisplay = '',
    required this.operator,
    required this.value,
  });

  factory AutomationCondition.fromJson(Map<String, dynamic> json) {
    return AutomationCondition(
      id: json['id'],
      field: json['field'] ?? '',
      fieldDisplay: json['field_display'] ?? '',
      operator: json['operator'] ?? 'eq',
      value: json['value'] ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'field': field,
        'operator': operator,
        'value': value,
      };
}

class AutomationAction {
  final int? id;
  final String actionType;
  final String actionTypeDisplay;
  final String target;
  final String targetDisplay;
  final Map<String, dynamic> config;
  final int order;

  const AutomationAction({
    this.id,
    required this.actionType,
    this.actionTypeDisplay = '',
    required this.target,
    this.targetDisplay = '',
    this.config = const {},
    this.order = 0,
  });

  factory AutomationAction.fromJson(Map<String, dynamic> json) {
    return AutomationAction(
      id: json['id'],
      actionType: json['action_type'] ?? '',
      actionTypeDisplay: json['action_type_display'] ?? '',
      target: json['target'] ?? 'employee',
      targetDisplay: json['target_display'] ?? '',
      config: Map<String, dynamic>.from(json['config'] ?? const {}),
      order: json['order'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'action_type': actionType,
        'target': target,
        'config': config,
        'order': order,
      };
}

class AutomationRule {
  final int id;
  final String name;
  final String description;
  final String triggerEvent;
  final String triggerEventDisplay;
  final bool isActive;
  final int runCount;
  final List<AutomationCondition> conditions;
  final List<AutomationAction> actions;

  const AutomationRule({
    required this.id,
    required this.name,
    this.description = '',
    required this.triggerEvent,
    this.triggerEventDisplay = '',
    this.isActive = true,
    this.runCount = 0,
    this.conditions = const [],
    this.actions = const [],
  });

  factory AutomationRule.fromJson(Map<String, dynamic> json) {
    return AutomationRule(
      id: json['id'],
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      triggerEvent: json['trigger_event'] ?? '',
      triggerEventDisplay: json['trigger_event_display'] ?? '',
      isActive: json['is_active'] ?? true,
      runCount: json['run_count'] ?? 0,
      conditions: (json['conditions'] as List<dynamic>? ?? const [])
          .map((e) => AutomationCondition.fromJson(e as Map<String, dynamic>))
          .toList(),
      actions: (json['actions'] as List<dynamic>? ?? const [])
          .map((e) => AutomationAction.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// Um disparo registrado.
///
/// Sem o histórico, uma automação que falha em silêncio é indistinguível
/// de uma que nunca foi acionada.
class AutomationRun {
  final int id;
  final String ruleName;
  final String status;
  final String statusDisplay;
  final String subjectLabel;
  final String detail;
  final String createdAt;

  const AutomationRun({
    required this.id,
    required this.ruleName,
    required this.status,
    required this.statusDisplay,
    required this.subjectLabel,
    required this.detail,
    required this.createdAt,
  });

  bool get failed => status == 'failed';

  factory AutomationRun.fromJson(Map<String, dynamic> json) {
    return AutomationRun(
      id: json['id'],
      ruleName: json['rule_name'] ?? '',
      status: json['status'] ?? '',
      statusDisplay: json['status_display'] ?? '',
      subjectLabel: json['subject_label'] ?? '',
      detail: json['detail'] ?? '',
      createdAt: json['created_at'] ?? '',
    );
  }
}
