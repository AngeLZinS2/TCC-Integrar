import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/models/paginated_response.dart';
import '../../../shared/models/quiz_model.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/quiz_repository.dart';

final quizRepositoryProvider = Provider<QuizRepository>((ref) {
  return QuizRepository(httpClient: ref.watch(httpClientProvider));
});

/// `null` quando o treinamento não tem avaliação — estado normal, não erro.
final courseQuizProvider =
    FutureProvider.autoDispose.family<QuizModel?, int>((ref, courseId) {
  return ref.watch(quizRepositoryProvider).getQuiz(courseId);
});

final myAttemptsProvider =
    FutureProvider.autoDispose<PaginatedResponse<QuizAttempt>>((ref) {
  return ref.watch(quizRepositoryProvider).getMyAttempts();
});
