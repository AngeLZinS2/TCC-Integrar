"""
Tasks de comunicados.

Duas responsabilidades: publicar o que foi agendado e avisar o público-alvo.
As duas são idempotentes — o Beat roda a cada 5 minutos e não pode publicar
ou notificar duas vezes o mesmo comunicado.
"""

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def publicar_agendados() -> int:
    """
    Publica os comunicados cuja hora chegou.

    Idempotência: a transição só acontece a partir de `scheduled`, e a
    linha é travada durante a mudança. Duas execuções concorrentes do Beat
    não publicam o mesmo comunicado duas vezes.
    """
    from .models import Announcement

    agora = timezone.now()
    pendentes = Announcement.objects.filter(
        status=Announcement.Status.SCHEDULED, publish_at__lte=agora
    ).values_list("pk", flat=True)

    publicados = 0
    for pk in list(pendentes):
        with transaction.atomic():
            comunicado = (
                Announcement.objects.select_for_update()
                .filter(pk=pk, status=Announcement.Status.SCHEDULED)
                .first()
            )
            if comunicado is None:
                continue  # outro worker já pegou
            comunicado.status = Announcement.Status.PUBLISHED
            comunicado.published_at = agora
            comunicado.save(update_fields=["status", "published_at"])
            publicados += 1
        notificar_publico_alvo.delay(pk)

    if publicados:
        logger.info("%d comunicado(s) agendado(s) publicado(s).", publicados)
    return publicados


@shared_task(ignore_result=True)
def notificar_publico_alvo(announcement_id: int) -> int:
    """
    Avisa quem o comunicado alcança.

    Fora do request de propósito: numa empresa grande são milhares de
    linhas, e o RH não pode ficar esperando isso terminar.

    Idempotência: `notified_at` é gravado antes do envio. Se a task rodar
    de novo, encontra a marca e não reenvia.
    """
    from apps.notifications.channels import Category, notify

    from . import services
    from .models import Announcement

    with transaction.atomic():
        comunicado = (
            Announcement.objects.select_for_update()
            .filter(pk=announcement_id, notified_at__isnull=True)
            .select_related("company")
            .first()
        )
        if comunicado is None:
            return 0  # já notificado, ou não existe
        comunicado.notified_at = timezone.now()
        comunicado.save(update_fields=["notified_at"])

    if not comunicado.is_visible:
        return 0

    destinatarios = services.audience_of(comunicado)
    enviados = notify(
        destinatarios,
        f"Novo comunicado: {comunicado.title}",
        comunicado.content[:200],
        category=Category.ANNOUNCEMENT,
        email=True,
        # Urgente ignora a preferência do usuário — é o caso previsto no
        # Módulo 8 para notificação crítica.
        critical=comunicado.is_urgent,
        link=f"/communications/{comunicado.pk}",
    )
    logger.info(
        "Comunicado %s notificou %d pessoa(s).", comunicado.pk, enviados
    )
    return enviados


@shared_task(ignore_result=True)
def expirar_comunicados() -> int:
    """Tira do mural o que passou da validade."""
    from .models import Announcement

    quantidade = Announcement.objects.filter(
        status=Announcement.Status.PUBLISHED,
        expires_at__isnull=False,
        expires_at__lte=timezone.now(),
    ).update(status=Announcement.Status.EXPIRED)
    if quantidade:
        logger.info("%d comunicado(s) expirado(s).", quantidade)
    return quantidade
