class CompanySettingsModel {
  final int id;
  final String name;
  final String legalName;
  final String cnpj;
  final String description;
  final String phone;
  final String email;
  final String address;
  final String logoUrl;
  final bool isActive;

  const CompanySettingsModel({
    required this.id,
    required this.name,
    this.legalName = '',
    this.cnpj = '',
    this.description = '',
    this.phone = '',
    this.email = '',
    this.address = '',
    this.logoUrl = '',
    this.isActive = true,
  });

  factory CompanySettingsModel.fromJson(Map<String, dynamic> json) {
    return CompanySettingsModel(
      id: json['id'] as int,
      name: json['name'] as String,
      legalName: json['legal_name'] as String? ?? '',
      cnpj: json['cnpj'] as String? ?? '',
      description: json['description'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      email: json['email'] as String? ?? '',
      address: json['address'] as String? ?? '',
      logoUrl: json['logo_url'] as String? ?? '',
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}

/// Um passo da configuração inicial da empresa.
class SetupStep {
  final String key;
  final String title;
  final String description;
  final bool done;
  final String route;

  const SetupStep({
    required this.key,
    required this.title,
    required this.description,
    required this.done,
    required this.route,
  });

  factory SetupStep.fromJson(Map<String, dynamic> json) {
    return SetupStep(
      key: json['key'] as String,
      title: json['title'] as String,
      description: json['description'] as String? ?? '',
      done: json['done'] as bool? ?? false,
      route: json['route'] as String? ?? '/',
    );
  }
}

/// Progresso da configuração inicial.
///
/// Derivado do estado real do banco a cada consulta — não existe flag
/// "já configurei" que possa ficar dessincronizada da realidade.
class SetupChecklist {
  final List<SetupStep> steps;
  final int completedSteps;
  final int totalSteps;
  final int percent;
  final bool isComplete;

  const SetupChecklist({
    required this.steps,
    required this.completedSteps,
    required this.totalSteps,
    required this.percent,
    required this.isComplete,
  });

  /// Próximo passo pendente — o que a tela sugere fazer agora.
  SetupStep? get nextStep {
    for (final step in steps) {
      if (!step.done) return step;
    }
    return null;
  }

  factory SetupChecklist.fromJson(Map<String, dynamic> json) {
    return SetupChecklist(
      steps: (json['steps'] as List<dynamic>? ?? [])
          .map((e) => SetupStep.fromJson(e as Map<String, dynamic>))
          .toList(),
      completedSteps: json['completed_steps'] as int? ?? 0,
      totalSteps: json['total_steps'] as int? ?? 0,
      percent: json['percent'] as int? ?? 0,
      isComplete: json['is_complete'] as bool? ?? false,
    );
  }
}
