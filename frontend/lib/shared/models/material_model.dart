class MaterialModel {
  final int id;
  final String title;
  final String fileUrl;
  final int? sector;
  final String? sectorName;
  final DateTime? createdAt;

  const MaterialModel({
    required this.id,
    required this.title,
    required this.fileUrl,
    this.sector,
    this.sectorName,
    this.createdAt,
  });

  bool get isGeneral => sector == null;

  String get fileExtension {
    try {
      final uri = Uri.parse(fileUrl);
      final path = uri.path;
      if (path.contains('.')) {
        return path.split('.').last.toUpperCase();
      }
    } catch (_) {}
    return 'DOC';
  }

  String get typeDisplay {
    final ext = fileExtension.toLowerCase();
    switch (ext) {
      case 'pdf':
        return 'Documento PDF';
      case 'doc':
      case 'docx':
        return 'Documento Word';
      case 'xls':
      case 'xlsx':
        return 'Planilha';
      case 'html':
      case 'htm':
        return 'Página Web / Guia';
      default:
        return 'Material de Apoio';
    }
  }

  factory MaterialModel.fromJson(Map<String, dynamic> json) {
    return MaterialModel(
      id: json['id'] as int,
      title: json['title'] as String,
      fileUrl: json['file_url'] as String? ?? '',
      sector: json['sector'] as int?,
      sectorName: json['sector_name'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String)
          : null,
    );
  }
}
