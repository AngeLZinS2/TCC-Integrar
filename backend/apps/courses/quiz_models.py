"""
Avaliação de treinamento e certificados.

Antes da P2 a conclusão era auto-declarada: o colaborador apertava
"concluí" e o sistema acreditava. Para treinamento de compliance — LGPD,
segurança, código de conduta — isso não sustenta comprovação nenhuma.

Aqui o treinamento com quiz só fecha quando a pessoa é aprovada, e a
aprovação gera um certificado com código verificável.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Quiz(models.Model):
    """
    Avaliação de um treinamento. No máximo uma por curso.

    A existência do quiz é o que muda a regra de conclusão do curso — sem
    quiz, continua valendo o "marcar como concluído" de antes.
    """

    course = models.OneToOneField(
        "courses.Course", on_delete=models.CASCADE, related_name="quiz"
    )
    title = models.CharField(max_length=200, default="Avaliação")
    description = models.TextField(blank=True, default="")

    passing_score = models.PositiveIntegerField(
        default=70, help_text="Percentual mínimo de acerto para aprovação (0-100)."
    )
    max_attempts = models.PositiveIntegerField(
        default=3, help_text="Tentativas permitidas. 0 = ilimitado.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inativa, a avaliação para de ser exigida sem apagar o histórico.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"

    def __str__(self):
        return f"{self.title} — {self.course.title}"

    @property
    def question_count(self) -> int:
        return self.questions.count()

    def attempts_left_for(self, user) -> int | None:
        """Tentativas restantes; None quando ilimitado."""
        if not self.max_attempts:
            return None
        usadas = self.attempts.filter(user=user, finished_at__isnull=False).count()
        return max(self.max_attempts - usadas, 0)


class Question(models.Model):
    """
    Uma pergunta da avaliação.

    `allows_multiple` decide se a resposta é uma opção ou várias. O acerto
    em múltipla escolha exige o conjunto EXATO: marcar duas certas de três
    não é acerto parcial, é resposta errada — meio-certo em prova de
    compliance não comprova nada.
    """

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    allows_multiple = models.BooleanField(
        default=False, help_text="Permite marcar mais de uma alternativa."
    )
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Pergunta"
        verbose_name_plural = "Perguntas"

    def __str__(self):
        return self.text[:60]

    @property
    def correct_option_ids(self) -> set:
        return {o.id for o in self.options.all() if o.is_correct}


class Option(models.Model):
    """
    Uma alternativa.

    `is_correct` nunca é serializado para quem está respondendo — só para
    quem administra o treinamento. Ver `QuestionForTakingSerializer`.
    """

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Alternativa"
        verbose_name_plural = "Alternativas"

    def __str__(self):
        return self.text[:60]


class QuizAttempt(models.Model):
    """
    Uma tentativa de responder a avaliação.

    Registrada ao iniciar (não ao enviar) para que uma tentativa abandonada
    ainda conte — do contrário bastaria fechar a tela ao ver uma pergunta
    difícil e recomeçar sem gastar tentativa.
    """

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    attempt_number = models.PositiveIntegerField()

    score = models.PositiveIntegerField(default=0, help_text="Percentual de acerto (0-100).")
    correct_count = models.PositiveIntegerField(default=0)
    question_count = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("quiz", "user", "attempt_number")
        ordering = ["-started_at"]
        verbose_name = "Tentativa"
        verbose_name_plural = "Tentativas"
        indexes = [models.Index(fields=["user", "quiz", "-started_at"])]

    def __str__(self):
        return f"{self.user.email} — {self.quiz.course.title} (#{self.attempt_number})"

    @property
    def is_finished(self) -> bool:
        return self.finished_at is not None


class AttemptAnswer(models.Model):
    """O que a pessoa marcou em cada pergunta, guardado para conferência."""

    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_options = models.ManyToManyField(Option, blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        unique_together = ("attempt", "question")


class Certificate(models.Model):
    """
    Comprovante de conclusão, emitido na aprovação.

    O código é o que torna o certificado verificável por quem não tem
    acesso ao sistema — um RH de outra empresa, por exemplo. Por isso a
    rota de validação é pública, e devolve o mínimo: nome, treinamento,
    data. Nunca e-mail, cargo ou qualquer outro dado da pessoa.
    """

    code = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates"
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="certificates"
    )
    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="certificates"
    )
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="certificate",
    )
    score = models.PositiveIntegerField(default=0)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Um certificado por pessoa e treinamento: refazer a avaliação não
        # emite outro documento.
        unique_together = ("user", "course")
        ordering = ["-issued_at"]
        verbose_name = "Certificado"
        verbose_name_plural = "Certificados"

    def __str__(self):
        return f"{self.code} — {self.user.full_name}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._gerar_codigo()
        super().save(*args, **kwargs)

    @staticmethod
    def _gerar_codigo() -> str:
        """
        CERT-2026-A1B2C3D4.

        Aleatório, e não sequencial: o código circula fora do sistema e é
        consultado numa rota pública. Sequencial permitiria varrer os
        certificados de todo mundo somando 1, e ainda revelaria quantos a
        plataforma emitiu.
        """
        ano = timezone.localdate().year
        return f"CERT-{ano}-{uuid.uuid4().hex[:8].upper()}"
