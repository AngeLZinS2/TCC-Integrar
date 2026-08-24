// Avaliação de treinamento e certificados.
//
// Repare no que NÃO existe aqui: `isCorrect` nas alternativas. O gabarito
// não sai do servidor para quem vai responder, e o app não tem onde
// guardá-lo mesmo que quisesse.

class QuizOption {
  final int id;
  final String text;
  final int order;

  const QuizOption({required this.id, required this.text, this.order = 0});

  factory QuizOption.fromJson(Map<String, dynamic> json) {
    return QuizOption(
      id: json['id'],
      text: json['text'] ?? '',
      order: json['order'] ?? 0,
    );
  }
}

class QuizQuestion {
  final int id;
  final String text;
  final bool allowsMultiple;
  final int order;
  final List<QuizOption> options;

  const QuizQuestion({
    required this.id,
    required this.text,
    this.allowsMultiple = false,
    this.order = 0,
    this.options = const [],
  });

  factory QuizQuestion.fromJson(Map<String, dynamic> json) {
    return QuizQuestion(
      id: json['id'],
      text: json['text'] ?? '',
      allowsMultiple: json['allows_multiple'] ?? false,
      order: json['order'] ?? 0,
      options: (json['options'] as List<dynamic>? ?? const [])
          .map((e) => QuizOption.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class QuizModel {
  final int id;
  final String title;
  final String description;
  final int passingScore;
  final int maxAttempts;
  final int? attemptsLeft;
  final bool alreadyPassed;
  final List<QuizQuestion> questions;

  const QuizModel({
    required this.id,
    required this.title,
    this.description = '',
    required this.passingScore,
    required this.maxAttempts,
    this.attemptsLeft,
    this.alreadyPassed = false,
    this.questions = const [],
  });

  bool get unlimited => maxAttempts == 0;

  factory QuizModel.fromJson(Map<String, dynamic> json) {
    return QuizModel(
      id: json['id'],
      title: json['title'] ?? 'Avaliação',
      description: json['description'] ?? '',
      passingScore: json['passing_score'] ?? 70,
      maxAttempts: json['max_attempts'] ?? 0,
      attemptsLeft: json['attempts_left'],
      alreadyPassed: json['already_passed'] ?? false,
      questions: (json['questions'] as List<dynamic>? ?? const [])
          .map((e) => QuizQuestion.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// Resultado por pergunta.
///
/// Diz SE acertou, nunca QUAL era a certa — do contrário a primeira
/// tentativa entregaria o gabarito para a segunda.
class AnswerResult {
  final int question;
  final String questionText;
  final bool isCorrect;

  const AnswerResult({
    required this.question,
    required this.questionText,
    required this.isCorrect,
  });

  factory AnswerResult.fromJson(Map<String, dynamic> json) {
    return AnswerResult(
      question: json['question'] ?? 0,
      questionText: json['question_text'] ?? '',
      isCorrect: json['is_correct'] ?? false,
    );
  }
}

class QuizAttempt {
  final int id;
  final int attemptNumber;
  final int score;
  final int correctCount;
  final int questionCount;
  final bool passed;
  final int passingScore;
  final int? attemptsLeft;
  final String? certificateCode;
  final String courseTitle;
  final List<AnswerResult> answers;

  const QuizAttempt({
    required this.id,
    required this.attemptNumber,
    required this.score,
    required this.correctCount,
    required this.questionCount,
    required this.passed,
    required this.passingScore,
    this.attemptsLeft,
    this.certificateCode,
    this.courseTitle = '',
    this.answers = const [],
  });

  factory QuizAttempt.fromJson(Map<String, dynamic> json) {
    return QuizAttempt(
      id: json['id'],
      attemptNumber: json['attempt_number'] ?? 1,
      score: json['score'] ?? 0,
      correctCount: json['correct_count'] ?? 0,
      questionCount: json['question_count'] ?? 0,
      passed: json['passed'] ?? false,
      passingScore: json['passing_score'] ?? 70,
      attemptsLeft: json['attempts_left'],
      certificateCode: json['certificate_code'],
      courseTitle: json['course_title'] ?? '',
      answers: (json['answers'] as List<dynamic>? ?? const [])
          .map((e) => AnswerResult.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class CertificateModel {
  final int id;
  final String code;
  final String userName;
  final String courseTitle;
  final String companyName;
  final int score;
  final String issuedAt;

  const CertificateModel({
    required this.id,
    required this.code,
    required this.userName,
    required this.courseTitle,
    required this.companyName,
    required this.score,
    required this.issuedAt,
  });

  factory CertificateModel.fromJson(Map<String, dynamic> json) {
    return CertificateModel(
      id: json['id'] ?? 0,
      code: json['code'] ?? '',
      userName: json['user_name'] ?? '',
      courseTitle: json['course_title'] ?? '',
      companyName: json['company_name'] ?? '',
      score: json['score'] ?? 0,
      issuedAt: json['issued_at'] ?? '',
    );
  }
}
