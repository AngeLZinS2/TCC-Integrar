/// Colaborador visto pela administração (RH / admin da empresa).
///
/// Diferente de `CollaboratorRowModel` (rh_dashboard), que carrega
/// estatísticas de progresso. Aqui o foco é o cadastro em si.
class EmployeeModel {
  final int id;
  final String email;
  final String fullName;
  final String phone;
  final String avatarUrl;
  final String registrationNumber;
  final String role;
  final String roleDisplay;
  final int? sectorId;
  final String? sectorName;
  final int? positionId;
  final String? positionName;
  final int? managerId;
  final String? managerName;
  final DateTime? hireDate;
  final bool isActive;
  final bool isSectorLeader;
  final DateTime? lastLogin;

  const EmployeeModel({
    required this.id,
    required this.email,
    required this.fullName,
    this.phone = '',
    this.avatarUrl = '',
    this.registrationNumber = '',
    this.role = 'colaborador',
    this.roleDisplay = 'Colaborador',
    this.sectorId,
    this.sectorName,
    this.positionId,
    this.positionName,
    this.managerId,
    this.managerName,
    this.hireDate,
    this.isActive = true,
    this.isSectorLeader = false,
    this.lastLogin,
  });

  bool get neverLoggedIn => lastLogin == null;

  /// Papéis que administram a empresa — usado para avisar sobre o impacto
  /// de uma troca de papel antes de confirmar.
  bool get managesCompany => role == 'company_admin' || role == 'rh_admin';

  factory EmployeeModel.fromJson(Map<String, dynamic> json) {
    return EmployeeModel(
      id: json['id'] as int,
      email: json['email'] as String,
      fullName: json['full_name'] as String,
      phone: json['phone'] as String? ?? '',
      avatarUrl: json['avatar_url'] as String? ?? '',
      registrationNumber: json['registration_number'] as String? ?? '',
      role: json['role'] as String? ?? 'colaborador',
      roleDisplay: json['role_display'] as String? ?? 'Colaborador',
      sectorId: json['sector'] as int?,
      sectorName: json['sector_name'] as String?,
      positionId: json['position'] as int?,
      positionName: json['position_name'] as String?,
      managerId: json['manager'] as int?,
      managerName: json['manager_name'] as String?,
      hireDate: json['hire_date'] != null
          ? DateTime.tryParse(json['hire_date'] as String)
          : null,
      isActive: json['is_active'] as bool? ?? true,
      isSectorLeader: json['is_sector_leader'] as bool? ?? false,
      lastLogin: json['last_login'] != null
          ? DateTime.tryParse(json['last_login'] as String)
          : null,
    );
  }
}

/// Opção de papel atribuível, vinda do backend para não duplicar a lista.
class RoleOption {
  final String value;
  final String label;

  const RoleOption({required this.value, required this.label});

  factory RoleOption.fromJson(Map<String, dynamic> json) {
    return RoleOption(
      value: json['value'] as String,
      label: json['label'] as String,
    );
  }
}
