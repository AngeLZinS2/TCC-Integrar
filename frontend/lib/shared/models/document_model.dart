class DocumentVersion {
  final int id;
  final int versionNumber;
  final String publishedAt;

  DocumentVersion({
    required this.id,
    required this.versionNumber,
    required this.publishedAt,
  });

  factory DocumentVersion.fromJson(Map<String, dynamic> json) {
    return DocumentVersion(
      id: json['id'],
      versionNumber: json['version_number'] ?? 1,
      publishedAt: json['published_at'] ?? '',
    );
  }
}

class DocumentModel {
  final int id;
  final String title;
  final String description;
  final int? category;
  final String? categoryName;
  final bool isRequired;
  final String createdAt;
  final DocumentVersion? activeVersion;
  final bool hasAccepted;

  DocumentModel({
    required this.id,
    required this.title,
    required this.description,
    this.category,
    this.categoryName,
    required this.isRequired,
    required this.createdAt,
    this.activeVersion,
    this.hasAccepted = false,
  });

  factory DocumentModel.fromJson(Map<String, dynamic> json) {
    return DocumentModel(
      id: json['id'],
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      category: json['category'],
      categoryName: json['category_name'],
      isRequired: json['is_required'] ?? false,
      createdAt: json['created_at'] ?? '',
      activeVersion: json['active_version'] != null
          ? DocumentVersion.fromJson(json['active_version'])
          : null,
      hasAccepted: json['has_accepted'] ?? false,
    );
  }
}
