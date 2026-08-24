class EventModel {
  final int id;
  final String title;
  final String description;
  final String date;
  final int? author;
  final Map<String, dynamic>? authorDetails;

  EventModel({
    required this.id,
    required this.title,
    required this.description,
    required this.date,
    this.author,
    this.authorDetails,
  });

  factory EventModel.fromJson(Map<String, dynamic> json) {
    return EventModel(
      id: json['id'],
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      date: json['date'] ?? '',
      author: json['author'],
      authorDetails: json['author_details'],
    );
  }
}

class BirthdayModel {
  final int id;
  final String fullName;
  final String email;
  final String? avatarUrl;
  /// Já vem pronto como DD/MM. O backend nunca envia o ano —
  /// minimização de dados no painel de aniversariantes.
  final String birthday;
  final String? sectorName;
  final String? positionName;

  BirthdayModel({
    required this.id,
    required this.fullName,
    required this.email,
    this.avatarUrl,
    required this.birthday,
    this.sectorName,
    this.positionName,
  });

  factory BirthdayModel.fromJson(Map<String, dynamic> json) {
    return BirthdayModel(
      id: json['id'],
      fullName: json['full_name'] ?? '',
      email: json['email'] ?? '',
      avatarUrl: json['avatar_url'],
      birthday: json['birthday'] ?? '',
      sectorName: json['sector_name'],
      positionName: json['position_name'],
    );
  }
}
