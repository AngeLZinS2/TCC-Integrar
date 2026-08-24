import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/models/course_model.dart';
import '../../../shared/providers/app_providers.dart';
import '../data/course_repository.dart';

final courseRepositoryProvider = Provider<CourseRepository>((ref) {
  final httpClient = ref.watch(httpClientProvider);
  return CourseRepository(httpClient: httpClient);
});

class CoursesListNotifier extends StateNotifier<AsyncValue<List<CourseModel>>> {
  final CourseRepository _repository;

  CoursesListNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadCourses();
  }

  Future<void> loadCourses() async {
    state = const AsyncValue.loading();
    try {
      final courses = await _repository.fetchCourses();
      state = AsyncValue.data(courses);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> updateProgress(int courseId, String newStatus) async {
    final currentCourses = state.value;
    if (currentCourses == null) return;

    try {
      final updatedProgress = await _repository.updateProgress(
        courseId: courseId,
        status: newStatus,
      );

      state = AsyncValue.data(
        currentCourses.map((c) {
          if (c.id == courseId) {
            return c.copyWith(userProgress: updatedProgress);
          }
          return c;
        }).toList(),
      );
    } catch (_) {}
  }
}

final coursesListProvider =
    StateNotifierProvider<CoursesListNotifier, AsyncValue<List<CourseModel>>>((ref) {
  final repository = ref.watch(courseRepositoryProvider);
  return CoursesListNotifier(repository);
});

final courseDetailProvider =
    FutureProvider.family<CourseModel, int>((ref, courseId) async {
  final repository = ref.watch(courseRepositoryProvider);
  return repository.fetchCourseDetail(courseId);
});
