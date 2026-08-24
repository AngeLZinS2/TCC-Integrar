from django.conf import settings
from django.db import models


class Course(models.Model):
    """
    Curso vinculado a um setor e/ou cargo específico.
    Se sector e position forem nulos, o curso é considerado geral
    (visível para todos os colaboradores).
    """

    CONTENT_TYPE_CHOICES = [
        ("video", "Vídeo"),
        ("pdf", "PDF"),
        ("text", "Texto"),
    ]

    DEADLINE_CHOICES = [
        ("day1", "Dia 1"),
        ("week1", "Semana 1"),
        ("month1", "Mês 1"),
    ]

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="courses",
        verbose_name="Empresa",
    )
    title = models.CharField(max_length=200, verbose_name="Título")
    description = models.TextField(blank=True, verbose_name="Descrição")
    sector = models.ForeignKey(
        "sectors.Sector",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        verbose_name="Setor",
        help_text="Deixe em branco para cursos gerais (todos os setores).",
    )
    target_units = models.ManyToManyField(
        "units.Unit", blank=True, related_name="targeted_courses",
        verbose_name="Unidades",
        help_text="Vazio = todas as unidades da empresa.",
    )
    position = models.ForeignKey(
        "sectors.Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        verbose_name="Cargo",
    )
    deadline = models.CharField(
        max_length=10,
        choices=DEADLINE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Prazo",
        help_text="Opcional. Se definido, some para o cálculo de atraso do colaborador.",
    )
    prerequisite = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unlocked_by",
        verbose_name="Pré-requisito",
        help_text="Opcional. O colaborador só pode iniciar este curso após concluir o pré-requisito.",
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Ordem", db_index=True)

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ["order", "title"]

    def __str__(self) -> str:
        scope = self.sector.name if self.sector else "Geral"
        return f"[{scope}] {self.title}"


class Content(models.Model):
    """
    Conteúdo (módulo) de um curso — vídeo, PDF ou texto.
    A ordem define a sequência de exibição no app.
    """

    TYPE_CHOICES = [
        ("video", "Vídeo"),
        ("pdf", "PDF"),
        ("text", "Texto"),
    ]

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="contents",
        verbose_name="Curso",
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Tipo")
    file_url = models.URLField(verbose_name="URL do arquivo / vídeo")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordem", db_index=True)

    class Meta:
        verbose_name = "Conteúdo"
        verbose_name_plural = "Conteúdos"
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.course.title} — #{self.order} ({self.get_type_display()})"


class CourseProgress(models.Model):
    """
    Progresso de um colaborador em um curso.
    Garantia de unicidade (user, course) via unique_together.
    """

    STATUS_CHOICES = [
        ("not_started", "Não iniciado"),
        ("in_progress", "Em andamento"),
        ("completed", "Concluído"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_progresses",
        verbose_name="Usuário",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="progresses",
        verbose_name="Curso",
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="not_started",
        verbose_name="Status",
        db_index=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Concluído em")

    class Meta:
        verbose_name = "Progresso do curso"
        verbose_name_plural = "Progressos dos cursos"
        unique_together = [("user", "course")]

    def __str__(self) -> str:
        return f"{self.user} → {self.course} [{self.get_status_display()}]"


# A avaliação vive em quiz_models.py para não inchar este
# arquivo — reexportados aqui porque o Django só registra o que passa por
# models.py.
from .quiz_models import (  # noqa: E402,F401
    AttemptAnswer,
    Option,
    Question,
    Quiz,
    QuizAttempt,
)
