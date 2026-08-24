class PositionModel {
  final int id;
  final String name;
  final int sectorId;

  const PositionModel({required this.id, required this.name, required this.sectorId});

  factory PositionModel.fromJson(Map<String, dynamic> json) {
    return PositionModel(
      id: json['id'] as int,
      name: json['name'] as String,
      sectorId: json['sector'] as int,
    );
  }
}

class SectorModel {
  final int id;
  final String name;

  const SectorModel({required this.id, required this.name});

  factory SectorModel.fromJson(Map<String, dynamic> json) {
    return SectorModel(id: json['id'] as int, name: json['name'] as String);
  }
}
