"""
Tasks assíncronas de notificação.

Retry (Módulo 31): e-mail falha por motivo transitório o tempo todo — SMTP
fora do ar, timeout, limite do provedor. Três tentativas com espera
crescente, e depois desiste registrando o erro. Nunca em laço infinito.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,      # 1s, 2s, 4s… em vez de martelar o provedor
    retry_backoff_max=300,
    retry_jitter=True,       # espalha os retries quando muitos falham juntos
    max_retries=3,
    ignore_result=True,
)
def send_email_notification(self, user_ids: list[int], subject: str, body: str) -> int:
    """
    Envia um e-mail para cada destinatário.

    Um envio por destinatário, e não uma mensagem com todos em cópia: um
    e-mail interno não deve revelar a lista de quem mais recebeu.
    """
    from apps.users.models import User

    destinatarios = list(
        User.objects.filter(pk__in=user_ids, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    if not destinatarios:
        return 0

    enviados = 0
    for email in destinatarios:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        enviados += 1

    logger.info("E-mail '%s' enviado para %d destinatário(s).", subject, enviados)
    return enviados


@shared_task(ignore_result=True)
def notify_users_async(
    user_ids: list[int],
    title: str,
    message: str,
    category: str = "system",
    email: bool = False,
    link: str = "",
) -> int:
    """
    Notificação em massa fora do request.

    Usada quando o volume é grande — publicar um comunicado numa empresa de
    milhares de pessoas não pode acontecer dentro da requisição do RH.
    """
    from apps.users.models import User

    from .channels import notify

    usuarios = list(User.objects.filter(pk__in=user_ids, is_active=True))
    return notify(
        usuarios, title, message, category=category, email=email, link=link
    )
