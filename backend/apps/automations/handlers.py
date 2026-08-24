"""
Onde os eventos do sistema entram no motor de automações.

Os receivers só reagem a TRANSIÇÕES, nunca a um `save()` que reescreve o
mesmo estado — mesma disciplina dos signals de notificação. Sem isso, cada
PATCH num documento já publicado dispararia a automação de novo, e o RH
receberia o mesmo e-mail toda vez que alguém corrigisse uma vírgula.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from . import catalog
from .engine import disparar_apos_commit

logger = logging.getLogger(__name__)


def _guardar_anterior(sender, instance, campo="status"):
    """Guarda o valor atual no banco para o post_save comparar."""
    if instance.pk:
        return (
            sender.objects.filter(pk=instance.pk)
            .values_list(campo, flat=True)
            .first()
        )
    return None


# ── Colaborador ─────────────────────────────────────────────────────────────

def _conectar_usuario():
    from apps.users.models import User

    @receiver(pre_save, sender=User, dispatch_uid="automations_user_pre")
    def _stash(sender, instance, **kwargs):
        instance._automation_was_active = _guardar_anterior(
            sender, instance, "is_active"
        )

    @receiver(post_save, sender=User, dispatch_uid="automations_user_post")
    def _disparar(sender, instance, created, **kwargs):
        if not instance.company_id:
            return

        if created:
            disparar_apos_commit(
                catalog.EMPLOYEE_CREATED, instance.company, employee=instance
            )
            return

        anterior = getattr(instance, "_automation_was_active", None)
        if anterior is None or anterior == instance.is_active:
            return

        evento = (
            catalog.EMPLOYEE_ACTIVATED
            if instance.is_active
            else catalog.EMPLOYEE_DEACTIVATED
        )
        disparar_apos_commit(evento, instance.company, employee=instance)


# ── Treinamento ─────────────────────────────────────────────────────────────

def _conectar_treinamento():
    from apps.courses.models import CourseProgress

    @receiver(pre_save, sender=CourseProgress, dispatch_uid="automations_progress_pre")
    def _stash(sender, instance, **kwargs):
        instance._automation_previous = _guardar_anterior(sender, instance, "status")

    @receiver(post_save, sender=CourseProgress, dispatch_uid="automations_progress_post")
    def _disparar(sender, instance, created, **kwargs):
        usuario = instance.user
        if not usuario.company_id:
            return

        rotulos = {"course_title": instance.course.title}

        if created:
            disparar_apos_commit(
                catalog.TRAINING_ASSIGNED, usuario.company,
                employee=usuario, labels=rotulos,
            )

        anterior = getattr(instance, "_automation_previous", None)
        if instance.status == "completed" and anterior != "completed":
            disparar_apos_commit(
                catalog.TRAINING_COMPLETED, usuario.company,
                employee=usuario, labels=rotulos,
            )


# ── Documento ───────────────────────────────────────────────────────────────

def _conectar_documento():
    from apps.documents.models import Document

    @receiver(pre_save, sender=Document, dispatch_uid="automations_doc_pre")
    def _stash(sender, instance, **kwargs):
        instance._automation_previous = _guardar_anterior(sender, instance, "status")

    @receiver(post_save, sender=Document, dispatch_uid="automations_doc_post")
    def _disparar(sender, instance, **kwargs):
        anterior = getattr(instance, "_automation_previous", None)
        if instance.status != Document.Status.PUBLISHED or anterior == Document.Status.PUBLISHED:
            return
        disparar_apos_commit(
            catalog.DOCUMENT_PUBLISHED, instance.company,
            labels={"document_title": instance.title},
        )


# ── Solicitação ─────────────────────────────────────────────────────────────

def _conectar_solicitacao():
    from apps.requests.models import HRRequest

    @receiver(pre_save, sender=HRRequest, dispatch_uid="automations_req_pre")
    def _stash(sender, instance, **kwargs):
        instance._automation_previous = _guardar_anterior(sender, instance, "status")

    @receiver(post_save, sender=HRRequest, dispatch_uid="automations_req_post")
    def _disparar(sender, instance, created, **kwargs):
        rotulos = {"request_number": instance.number, "request_subject": instance.subject}

        if created:
            disparar_apos_commit(
                catalog.REQUEST_CREATED, instance.company,
                employee=instance.requester, labels=rotulos,
            )
            return

        anterior = getattr(instance, "_automation_previous", None)
        if instance.status == HRRequest.Status.COMPLETED and anterior != HRRequest.Status.COMPLETED:
            disparar_apos_commit(
                catalog.REQUEST_COMPLETED, instance.company,
                employee=instance.requester, labels=rotulos,
            )


# ── Comunicado ──────────────────────────────────────────────────────────────

def _conectar_comunicado():
    from apps.communications.models import Announcement

    @receiver(pre_save, sender=Announcement, dispatch_uid="automations_ann_pre")
    def _stash(sender, instance, **kwargs):
        instance._automation_previous = _guardar_anterior(sender, instance, "status")

    @receiver(post_save, sender=Announcement, dispatch_uid="automations_ann_post")
    def _disparar(sender, instance, **kwargs):
        anterior = getattr(instance, "_automation_previous", None)
        if instance.status != Announcement.Status.PUBLISHED or anterior == Announcement.Status.PUBLISHED:
            return
        disparar_apos_commit(
            catalog.ANNOUNCEMENT_PUBLISHED, instance.company,
            labels={"announcement_title": instance.title},
        )


_conectar_usuario()
_conectar_treinamento()
_conectar_documento()
_conectar_solicitacao()
_conectar_comunicado()
