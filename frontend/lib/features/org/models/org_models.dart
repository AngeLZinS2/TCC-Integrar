export '../../../shared/models/paginated_response.dart' show Paginated, PaginatedResponse;

// Modelos da estrutura organizacional (setores e cargos).
//
// Distintos dos modelos enxutos em `rh_dashboard/models/sector_model.dart`,
// que existem só para popular dropdowns. Aqui o objetivo é administrar:
// contagens, gestor responsável e status fazem parte da tela.

class SectorModel {
  final int id;
  final String name;
  final String description;
  final int? managerId;
  final String? managerName;
  final bool isActive;
  final int positionsCount;
  final int collaboratorsCount;

  const SectorModel({
    required this.id,
    required this.name,
    this.description = '',
    this.managerId,
    this.managerName,
    this.isActive = true,
    this.positionsCount = 0,
    this.collaboratorsCount = 0,
  });

  bool get hasCollaborators => collaboratorsCount > 0;

  factory SectorModel.fromJson(Map<String, dynamic> json) {
    return SectorModel(
      id: json['id'] as int,
      name: json['name'] as String,
      description: json['description'] as String? ?? '',
      managerId: json['manager'] as int?,
      managerName: json['manager_name'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      positionsCount: json['positions_count'] as int? ?? 0,
      collaboratorsCount: json['collaborators_count'] as int? ?? 0,
    );
  }
}

class PositionModel {
  final int id;
  final String name;
  final String description;
  final int sectorId;
  final String? sectorName;
  final bool isActive;
  final int collaboratorsCount;

  const PositionModel({
    required this.id,
    required this.name,
    required this.sectorId,
    this.description = '',
    this.sectorName,
    this.isActive = true,
    this.collaboratorsCount = 0,
  });

  bool get hasCollaborators => collaboratorsCount > 0;

  factory PositionModel.fromJson(Map<String, dynamic> json) {
    return PositionModel(
      id: json['id'] as int,
      name: json['name'] as String,
      description: json['description'] as String? ?? '',
      sectorId: json['sector'] as int,
      sectorName: json['sector_name'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      collaboratorsCount: json['collaborators_count'] as int? ?? 0,
    );
  }
}

/// Candidato a gestor de setor — lista enxuta, sem dados desnecessários.
class ManagerOption {
  final int id;
  final String fullName;
  final String role;

  const ManagerOption({required this.id, required this.fullName, required this.role});

  factory ManagerOption.fromJson(Map<String, dynamic> json) {
    return ManagerOption(
      id: json['id'] as int,
      fullName: json['full_name'] as String,
      role: json['role'] as String? ?? 'colaborador',
    );
  }
}

// `Paginated` foi promovido para shared/models/paginated_response.dart —
// era usado por módulos sem relação com organização. Re-exportado aqui
// para os imports existentes continuarem válidos.
