/// Códigos de permissão do catálogo RBAC do backend.
///
/// Usados só para decidir o que MOSTRAR. A autorização real acontece no
/// servidor, a cada requisição — esconder um botão nunca é proteção.
abstract final class Perm {
  static const employeesRead = 'employees.read';
  static const employeesCreate = 'employees.create';
  static const employeesUpdate = 'employees.update';
  static const departmentsCreate = 'departments.create';
  static const positionsCreate = 'positions.create';
  static const trainingCreate = 'training.create';
  static const materialsCreate = 'materials.create';
  static const onboardingManage = 'onboarding.manage';
  static const companyUpdate = 'company.update';
  static const dashboardRead = 'dashboard.read';
  static const auditRead = 'audit.read';
  static const platformCompaniesManage = 'platform.companies.manage';
  static const integrationRead = 'integration.read';
  static const integrationManage = 'integration.manage';
  static const integrationSync = 'integration.sync';
}

class UserModel {
  final int id;
  final String email;
  final String fullName;

  /// 'colaborador', 'gestor', 'rh_admin', 'company_admin' ou 'owner'.
  final String role;

  final int? company;
  final String? companyName;
  final int? sector;
  final String? sectorName;
  final int? position;
  final String? positionName;
  final int? manager;
  final String? managerName;
  final String phone;
  final String avatarUrl;
  final String registrationNumber;
  final DateTime? hireDate;
  final bool isActive;
  final bool isSectorLeader;

  /// Permissões efetivas, vindas do backend em `/auth/me/`.
  final List<String> permissions;

  final DateTime? createdAt;

  const UserModel({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    this.company,
    this.companyName,
    this.sector,
    this.sectorName,
    this.position,
    this.positionName,
    this.manager,
    this.managerName,
    this.phone = '',
    this.avatarUrl = '',
    this.registrationNumber = '',
    this.hireDate,
    this.isActive = true,
    this.isSectorLeader = false,
    this.permissions = const [],
    this.createdAt,
  });

  // ── Papéis ────────────────────────────────────────────────────────────
  bool get isRHAdmin => role == 'rh_admin';
  bool get isCompanyAdmin => role == 'company_admin';
  bool get isGestor => role == 'gestor';
  bool get isColaborador => role == 'colaborador';
  bool get isOwner => role == 'owner';

  /// Administra a empresa inteira — o corte usado na navegação.
  bool get managesCompany => isCompanyAdmin || isRHAdmin;

  // ── Permissões ────────────────────────────────────────────────────────
  bool can(String permission) => permissions.contains(permission);

  bool get canManageCourses => can(Perm.trainingCreate);
  bool get canManageMaterials => can(Perm.materialsCreate);
  bool get canViewEmployees => can(Perm.employeesRead);
  bool get canCreateEmployees => can(Perm.employeesCreate);
  bool get canEditEmployees => can(Perm.employeesUpdate);
  bool get canManageOrg => can(Perm.departmentsCreate);

  /// Monta plano de integração: RH e admin em toda a empresa, gestor e
  /// líder de setor só na própria equipe. O recorte por equipe é do
  /// servidor — aqui é só para decidir se o botão aparece.
  bool get canManageOnboarding =>
      managesCompany || isGestor || isSectorLeader;

  /// Configura a integração com o banco da empresa.
  ///
  /// Só o administrador da empresa: um mapeamento errado reescreve o
  /// cadastro inteiro na próxima sincronização. O servidor recusa do mesmo
  /// jeito — aqui é só para decidir se o item aparece no menu.
  bool get canManageIntegration => can(Perm.integrationManage);
  bool get canViewDashboard => can(Perm.dashboardRead);
  bool get canViewAudit => can(Perm.auditRead);
  bool get canEditCompany => can(Perm.companyUpdate);

  String get roleLabel => switch (role) {
        'owner' => 'Dono da Plataforma',
        'company_admin' => 'Administrador da Empresa',
        'rh_admin' => 'RH',
        'gestor' => 'Gestor',
        _ => 'Colaborador',
      };

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int,
      email: json['email'] as String,
      fullName: json['full_name'] as String,
      role: json['role'] as String? ?? 'colaborador',
      company: json['company'] as int?,
      companyName: json['company_name'] as String?,
      sector: json['sector'] as int?,
      sectorName: json['sector_name'] as String?,
      position: json['position'] as int?,
      positionName: json['position_name'] as String?,
      manager: json['manager'] as int?,
      managerName: json['manager_name'] as String?,
      phone: json['phone'] as String? ?? '',
      avatarUrl: json['avatar_url'] as String? ?? '',
      registrationNumber: json['registration_number'] as String? ?? '',
      hireDate: json['hire_date'] != null
          ? DateTime.tryParse(json['hire_date'] as String)
          : null,
      isActive: json['is_active'] as bool? ?? true,
      isSectorLeader: json['is_sector_leader'] as bool? ?? false,
      permissions:
          (json['permissions'] as List<dynamic>? ?? []).map((e) => e as String).toList(),
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      'role': role,
      'company': company,
      'company_name': companyName,
      'sector': sector,
      'sector_name': sectorName,
      'position': position,
      'position_name': positionName,
      'manager': manager,
      'manager_name': managerName,
      'phone': phone,
      'avatar_url': avatarUrl,
      'registration_number': registrationNumber,
      'hire_date': hireDate?.toIso8601String().split('T').first,
      'is_active': isActive,
      'is_sector_leader': isSectorLeader,
      'permissions': permissions,
      'created_at': createdAt?.toIso8601String(),
    };
  }

  UserModel copyWith({
    int? id,
    String? email,
    String? fullName,
    String? role,
    int? company,
    String? companyName,
    int? sector,
    String? sectorName,
    int? position,
    String? positionName,
    int? manager,
    String? managerName,
    String? phone,
    String? avatarUrl,
    String? registrationNumber,
    DateTime? hireDate,
    bool? isActive,
    bool? isSectorLeader,
    List<String>? permissions,
    DateTime? createdAt,
  }) {
    return UserModel(
      id: id ?? this.id,
      email: email ?? this.email,
      fullName: fullName ?? this.fullName,
      role: role ?? this.role,
      company: company ?? this.company,
      companyName: companyName ?? this.companyName,
      sector: sector ?? this.sector,
      sectorName: sectorName ?? this.sectorName,
      position: position ?? this.position,
      positionName: positionName ?? this.positionName,
      manager: manager ?? this.manager,
      managerName: managerName ?? this.managerName,
      phone: phone ?? this.phone,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      registrationNumber: registrationNumber ?? this.registrationNumber,
      hireDate: hireDate ?? this.hireDate,
      isActive: isActive ?? this.isActive,
      isSectorLeader: isSectorLeader ?? this.isSectorLeader,
      permissions: permissions ?? this.permissions,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}
