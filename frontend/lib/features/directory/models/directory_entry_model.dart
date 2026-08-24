class DirectoryEntryModel {
  final int id;
  final String fullName;
  final String email;
  final String role; // 'colaborador' ou 'rh_admin'
  final int? sectorId;
  final String? sectorName;
  final int? positionId;
  final String? positionName;

  const DirectoryEntryModel({
    required this.id,
    required this.fullName,
    required this.email,
    required this.role,
    this.sectorId,
    this.sectorName,
    this.positionId,
    this.positionName,
  });

  bool get isRHAdmin => role == 'rh_admin';

  factory DirectoryEntryModel.fromJson(Map<String, dynamic> json) {
    return DirectoryEntryModel(
      id: json['id'] as int,
      fullName: json['full_name'] as String,
      email: json['email'] as String,
      role: json['role'] as String,
      sectorId: json['sector'] as int?,
      sectorName: json['sector_name'] as String?,
      positionId: json['position'] as int?,
      positionName: json['position_name'] as String?,
    );
  }
}
