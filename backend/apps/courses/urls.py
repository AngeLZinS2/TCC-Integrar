from django.urls import path
from rest_framework.routers import DefaultRouter

from .quiz_views import (
    CourseQuizView,
    MyAttemptsView,
    QuizAttemptView,
    QuizQuestionViewSet,
    QuizSubmitView,
)
from .views import ContentViewSet, CourseViewSet

router = DefaultRouter()
router.register(r"contents", ContentViewSet, basename="content")
router.register(r"", CourseViewSet, basename="course")

perguntas = QuizQuestionViewSet.as_view({"get": "list", "post": "create"})
pergunta = QuizQuestionViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "put": "update", "delete": "destroy"}
)

# As rotas literais vêm ANTES das do router: o detalhe do curso é /<pk>/
# com regex genérica e capturaria "my-attempts" como se fosse um id.
urlpatterns = [
    path("my-attempts/", MyAttemptsView.as_view(), name="my_quiz_attempts"),
    path("<int:course_id>/quiz/", CourseQuizView.as_view(), name="course_quiz"),
    path("<int:course_id>/quiz/questions/", perguntas, name="quiz_questions"),
    path("<int:course_id>/quiz/questions/<int:pk>/", pergunta, name="quiz_question_detail"),
    path("<int:course_id>/quiz/attempts/", QuizAttemptView.as_view(), name="quiz_attempt_start"),
    path(
        "<int:course_id>/quiz/attempts/<int:attempt_id>/submit/",
        QuizSubmitView.as_view(),
        name="quiz_attempt_submit",
    ),
] + router.urls
