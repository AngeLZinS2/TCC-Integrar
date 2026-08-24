class RequestComment {
  final int id;
  final String text;
  final String createdAt;
  final int author;
  final Map<String, dynamic> authorDetails;

  RequestComment({
    required this.id,
    required this.text,
    required this.createdAt,
    required this.author,
    required this.authorDetails,
  });

  factory RequestComment.fromJson(Map<String, dynamic> json) {
    return RequestComment(
      id: json['id'],
      text: json['text'] ?? '',
      createdAt: json['created_at'] ?? '',
      author: json['author'] ?? 0,
      authorDetails: json['author_details'] ?? {},
    );
  }
}

class RequestHistory {
  final int id;
  final String actionType;
  final String details;
  final String createdAt;
  final int? actor;
  final Map<String, dynamic>? actorDetails;

  RequestHistory({
    required this.id,
    required this.actionType,
    required this.details,
    required this.createdAt,
    this.actor,
    this.actorDetails,
  });

  factory RequestHistory.fromJson(Map<String, dynamic> json) {
    return RequestHistory(
      id: json['id'],
      actionType: json['action_type'] ?? '',
      details: json['details'] ?? '',
      createdAt: json['created_at'] ?? '',
      actor: json['actor'],
      actorDetails: json['actor_details'],
    );
  }
}

class HRRequest {
  final int id;
  final String number;
  final String category;
  final String subject;
  final String status;
  final String priority;
  final String createdAt;
  final String updatedAt;
  final String? resolvedAt;
  final String? closedAt;
  
  final int requester;
  final Map<String, dynamic> requesterDetails;
  
  final int? assignedTo;
  final Map<String, dynamic>? assignedToDetails;

  final String? description;
  final List<RequestHistory> history;
  final List<RequestComment> comments;

  HRRequest({
    required this.id,
    required this.number,
    required this.category,
    required this.subject,
    required this.status,
    required this.priority,
    required this.createdAt,
    required this.updatedAt,
    this.resolvedAt,
    this.closedAt,
    required this.requester,
    required this.requesterDetails,
    this.assignedTo,
    this.assignedToDetails,
    this.description,
    this.history = const [],
    this.comments = const [],
  });

  factory HRRequest.fromJson(Map<String, dynamic> json) {
    return HRRequest(
      id: json['id'],
      number: json['number'] ?? '',
      category: json['category'] ?? '',
      subject: json['subject'] ?? '',
      status: json['status'] ?? '',
      priority: json['priority'] ?? '',
      createdAt: json['created_at'] ?? '',
      updatedAt: json['updated_at'] ?? '',
      resolvedAt: json['resolved_at'],
      closedAt: json['closed_at'],
      requester: json['requester'] ?? 0,
      requesterDetails: json['requester_details'] ?? {},
      assignedTo: json['assigned_to'],
      assignedToDetails: json['assigned_to_details'],
      description: json['description'],
      history: (json['history'] as List<dynamic>?)
              ?.map((e) => RequestHistory.fromJson(e))
              .toList() ??
          [],
      comments: (json['comments'] as List<dynamic>?)
              ?.map((e) => RequestComment.fromJson(e))
              .toList() ??
          [],
    );
  }
}
