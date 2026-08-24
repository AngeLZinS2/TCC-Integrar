"""
Regras da avaliação: iniciar tentativa, corrigir, aprovar e certificar.

A regra que governa o módulo: **o gabarito nunca sai do servidor**. A
correção acontece aqui, comparando o que a pessoa marcou com o que está no
banco. O app recebe só a nota e o veredito — nunca quais eram as certas,
porque isso permitiria acertar tudo na tentativa seguinte.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.notifications.channels import Category, notify

from .models import CourseProgress
from .quiz_models import AttemptAnswer, Certificate, Question, QuizAttempt

logger = logging.getLogger(__name__)


class QuizError(Exception):
    """Regra de negócio violada. A view converte em 400."""


def pode_tentar(quiz, user) -> tuple[bool, str]:
    """(pode, motivo). Motivo vazio quando pode."""
    if not quiz.is_active:
        return False, "Esta avaliação não está disponível."
    if quiz.question_count == 0:
        return False, "Esta avaliação ainda não tem perguntas."

    if ja_aprovado(quiz, user):
        return False, "Você já foi aprovado nesta avaliação."

    restantes = quiz.attempts_left_for(user)
    if restantes is not None and restantes <= 0:
        return False, "Você esgotou as tentativas desta avaliação."
    return True, ""


def ja_aprovado(quiz, user) -> bool:
    return quiz.attempts.filter(user=user, passed=True).exists()


@transaction.atomic
def iniciar_tentativa(quiz, user) -> QuizAttempt:
    """
    Abre uma tentativa.

    Registrada ao INICIAR, não ao enviar: sem isso, bastaria fechar a tela
    ao ver uma pergunta difícil para recomeçar sem gastar tentativa.

    Uma tentativa já aberta e não enviada é reaproveitada — recarregar a
    página não pode consumir outra.
    """
    pode, motivo = pode_tentar(quiz, user)
    if not pode:
        raise QuizError(motivo)

    aberta = quiz.attempts.filter(user=user, finished_at__isnull=True).first()
    if aberta:
        return aberta

    ultima = quiz.attempts.filter(user=user).order_by("-attempt_number").first()
    numero = (ultima.attempt_number + 1) if ultima else 1

    return QuizAttempt.objects.create(
        quiz=quiz, user=user, attempt_number=numero, question_count=quiz.question_count
    )


@transaction.atomic
def enviar_respostas(attempt: QuizAttempt, respostas: dict) -> QuizAttempt:
    """
    Corrige a tentativa.

    `respostas` é {question_id: [option_id, ...]}.

    Acerto exige o conjunto EXATO de alternativas corretas. Em pergunta de
    múltipla escolha, marcar duas certas de três não é acerto parcial — é
    resposta errada. Meio-certo em avaliação de compliance não comprova
    nada.
    """
    if attempt.is_finished:
        raise QuizError("Esta tentativa já foi enviada.")

    perguntas = list(
        Question.objects.filter(quiz=attempt.quiz).prefetch_related("options")
    )
    if not perguntas:
        raise QuizError("Esta avaliação não tem perguntas.")

    validas_por_pergunta = {
        p.id: {o.id for o in p.options.all()} for p in perguntas
    }

    acertos = 0
    for pergunta in perguntas:
        marcadas = set(respostas.get(pergunta.id, []) or [])

        # Ignora id de alternativa que não é desta pergunta — evita que um
        # cliente adulterado "acerte" mandando ids de outra questão.
        marcadas &= validas_por_pergunta[pergunta.id]

        correta = marcadas == pergunta.correct_option_ids and bool(marcadas)
        if correta:
            acertos += 1

        registro, _ = AttemptAnswer.objects.update_or_create(
            attempt=attempt, question=pergunta, defaults={"is_correct": correta}
        )
        registro.selected_options.set(marcadas)

    total = len(perguntas)
    nota = round(acertos / total * 100) if total else 0

    attempt.correct_count = acertos
    attempt.question_count = total
    attempt.score = nota
    attempt.passed = nota >= attempt.quiz.passing_score
    attempt.finished_at = timezone.now()
    attempt.save(
        update_fields=[
            "correct_count", "question_count", "score", "passed", "finished_at"
        ]
    )

    if attempt.passed:
        _concluir_treinamento(attempt)
    else:
        _avisar_reprovacao(attempt)

    audit.record(
        attempt.user, AuditLog.Action.UPDATE, "quiz_attempt",
        resource_id=attempt.pk,
        resource_label=attempt.quiz.course.title,
        metadata={
            "attempt": attempt.attempt_number,
            "score": nota,
            "passed": attempt.passed,
        },
    )
    return attempt


def _concluir_treinamento(attempt: QuizAttempt) -> None:
    """Aprovação fecha o curso e emite o certificado."""
    curso = attempt.quiz.course
    progresso, _ = CourseProgress.objects.get_or_create(
        user=attempt.user, course=curso
    )
    if progresso.status != "completed":
        progresso.status = "completed"
        progresso.completed_at = timezone.now()
        # Marca para o signal de CourseProgress não mandar também o
        # "Treinamento concluído" genérico: o aviso de aprovação abaixo já
        # cobre o mesmo fato, com nota e certificado.
        progresso.concluido_por_avaliacao = True
        progresso.save(update_fields=["status", "completed_at"])

    certificado = emitir_certificado(attempt)

    notify(
        attempt.user,
        f"Aprovado em {curso.title}",
        f"Nota {attempt.score}%. Seu certificado {certificado.code} já está disponível.",
        category=Category.TRAINING,
        email=True,
        link=f"/certificates/{certificado.code}",
    )


def _avisar_reprovacao(attempt: QuizAttempt) -> None:
    restantes = attempt.quiz.attempts_left_for(attempt.user)
    if restantes is None:
        complemento = "Você pode tentar novamente."
    elif restantes > 0:
        complemento = f"Você ainda tem {restantes} tentativa(s)."
    else:
        complemento = "Você esgotou as tentativas. Procure o RH."

    notify(
        attempt.user,
        f"Avaliação não aprovada: {attempt.quiz.course.title}",
        f"Nota {attempt.score}% (mínimo {attempt.quiz.passing_score}%). {complemento}",
        category=Category.TRAINING,
        link=f"/courses/{attempt.quiz.course_id}",
    )


def emitir_certificado(attempt: QuizAttempt) -> Certificate:
    """
    Emite o certificado, ou devolve o que já existe.

    Idempotente (Módulo 32): reprocessar a aprovação — por retry de task ou
    duplo clique — não pode gerar um segundo documento para a mesma pessoa
    e treinamento.
    """
    certificado, criado = Certificate.objects.get_or_create(
        user=attempt.user,
        course=attempt.quiz.course,
        defaults={
            "company": attempt.quiz.course.company,
            "attempt": attempt,
            "score": attempt.score,
        },
    )
    if criado:
        audit.record(
            attempt.user, AuditLog.Action.CREATE, "certificate",
            resource_id=certificado.pk, resource_label=certificado.code,
            metadata={"course": attempt.quiz.course.title, "score": attempt.score},
        )
    return certificado


def exige_avaliacao(curso) -> bool:
    """
    True quando o curso só pode ser concluído por aprovação.

    É o que impede o "marcar como concluído" de um treinamento avaliado.
    """
    quiz = getattr(curso, "quiz", None)
    return bool(quiz and quiz.is_active and quiz.questions.exists())
