"""
Notificações automáticas disparadas por eventos do sistema.

Os receivers só registram *transições* (ex.: um treinamento que passou a
"concluído"), nunca o simples `save()` de um objeto que já estava naquele
estado — isso evita notificação duplicada quando o app reenvia o mesmo
status ou quando o seed roda de novo.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.checklist.models import ChecklistProgress
from apps.courses.models import Course, CourseProgress
from apps.materials.models import Material
from apps.users.models import User

from . import services


# ---------------------------------------------------------------------------
# Boas-vindas ao novo colaborador
# ---------------------------------------------------------------------------

@receiver(post_save, sender=User)
def notify_welcome(sender, instance, created, **kwargs):
    if not created or instance.role != "colaborador":
        return
    company_name = instance.company.name if instance.company_id else "a empresa"
    services.notify(
        instance,
        "Bem-vindo(a) ao time!",
        f"Sua integração na {company_name} começou. "
        "Acesse a aba Treinamentos para ver a sua trilha e o checklist dos primeiros dias.",
    )


# ---------------------------------------------------------------------------
# Progresso em treinamento
# ---------------------------------------------------------------------------

@receiver(pre_save, sender=CourseProgress)
def stash_previous_course_status(sender, instance, **kwargs):
    """Guarda o status anterior para o post_save saber se houve transição."""
    if instance.pk:
        instance._previous_status = (
            sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
        )
    else:
        instance._previous_status = None


@receiver(post_save, sender=CourseProgress)
def notify_course_completed(sender, instance, **kwargs):
    previous = getattr(instance, "_previous_status", None)
    if instance.status != "completed" or previous == "completed":
        return

    user = instance.user
    course = instance.course

    # Quando a conclusão veio da aprovação na avaliação, quem avisa é o
    # quiz — com nota e código do certificado. Repetir aqui daria duas
    # notificações para o mesmo fato, e a genérica é a menos informativa.
    if not getattr(instance, "concluido_por_avaliacao", False):
        services.notify(
            user,
            "Treinamento concluído",
            f'Você concluiu "{course.title}". Bom trabalho!',
        )

    completed_ids = set(
        CourseProgress.objects.filter(user=user, status="completed").values_list(
            "course_id", flat=True
        )
    )

    # Trilha inteira concluída?
    eligible_ids = set(services.eligible_courses_for(user).values_list("id", flat=True))
    if eligible_ids and eligible_ids.issubset(completed_ids):
        services.notify(
            user,
            "Trilha de treinamentos concluída!",
            "Você concluiu todos os treinamentos da sua trilha de integração. Parabéns!",
        )

    # Treinamentos que este destravou
    unlocked = (
        services.eligible_courses_for(user)
        .filter(prerequisite_id=course.id)
        .exclude(id__in=completed_ids)
    )
    for unlocked_course in unlocked:
        services.notify(
            user,
            "Novo treinamento desbloqueado",
            f'"{unlocked_course.title}" foi liberado porque você concluiu o pré-requisito.',
        )


# ---------------------------------------------------------------------------
# Progresso no checklist
# ---------------------------------------------------------------------------

@receiver(pre_save, sender=ChecklistProgress)
def stash_previous_checklist_state(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_completed = (
            sender.objects.filter(pk=instance.pk).values_list("completed", flat=True).first()
        )
    else:
        instance._previous_completed = None


@receiver(post_save, sender=ChecklistProgress)
def notify_checklist_completed(sender, instance, **kwargs):
    previous = getattr(instance, "_previous_completed", None)
    if not instance.completed or previous is True:
        return

    user = instance.user
    eligible_ids = set(
        services.eligible_checklist_items_for(user).values_list("id", flat=True)
    )
    if not eligible_ids:
        return

    completed_ids = set(
        ChecklistProgress.objects.filter(user=user, completed=True).values_list(
            "item_id", flat=True
        )
    )
    if eligible_ids.issubset(completed_ids):
        services.notify(
            user,
            "Checklist de integração concluído!",
            "Você concluiu todos os itens do seu checklist de integração. Parabéns!",
        )


# ---------------------------------------------------------------------------
# Novo conteúdo publicado
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Course)
def notify_new_course(sender, instance, created, **kwargs):
    if not created:
        return
    users = services.colaboradores_for_scope(
        instance.company_id, instance.sector_id, instance.position_id
    )
    services.notify_many(
        users,
        "Novo treinamento disponível",
        f'"{instance.title}" foi adicionado à sua trilha de treinamentos.',
    )


@receiver(post_save, sender=Material)
def notify_new_material(sender, instance, created, **kwargs):
    if not created:
        return
    users = services.colaboradores_for_scope(instance.company_id, instance.sector_id)
    services.notify_many(
        users,
        "Novo material disponível",
        f'"{instance.title}" foi adicionado à Biblioteca de Materiais.',
    )
