class Announcement {
  final int id;
  final String title;
  final String content;
  final bool isUrgent;
  final List<int> targetSectors;
  final List<int> targetPositions;
  final int? author;
  final Map<String, dynamic>? authorDetails;
  final String createdAt;
  final bool isRead;
  final int readCount;

  Announcement({
    required this.id,
    required this.title,
    required this.content,
    required this.isUrgent,
    this.targetSectors = const [],
    this.targetPositions = const [],
    this.author,
    this.authorDetails,
    required this.createdAt,
    this.isRead = false,
    this.readCount = 0,
  });

  factory Announcement.fromJson(Map<String, dynamic> json) {
    return Announcement(
      id: json['id'],
      title: json['title'] ?? '',
      content: json['content'] ?? '',
      isUrgent: json['is_urgent'] ?? false,
      targetSectors: List<int>.from(json['target_sectors'] ?? []),
      targetPositions: List<int>.from(json['target_positions'] ?? []),
      author: json['author'],
      authorDetails: json['author_details'],
      createdAt: json['created_at'] ?? '',
      isRead: json['is_read'] ?? false,
      readCount: json['read_count'] ?? 0,
    );
  }
}
