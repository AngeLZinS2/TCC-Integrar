"""
Tarefas periódicas de documentos (Módulo 11).

Rodam pelo Celery Beat. Todas são idempotentes: se o Beat disparar duas
vezes no mesmo dia, ninguém recebe o aviso em dobro — o controle está no
próprio estado do banco, não num contador à parte.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def avisar_documentos_obrigatorios_pendentes() -> int:
    """
    Lembra quem ainda não aceitou um documento obrigatório.

    Idempotência: procura uma notificação com o mesmo título criada nas
    últimas 20 horas antes de criar outra. Duas execuções no mesmo dia
    geram um aviso só.
    """
    from django.db.models import Q

    from apps.documents.models import Document, DocumentAcceptance
    from apps.notifications.channels import Category, notify
    from apps.notifications.models import Notification
    from apps.users.models import User

    agora = timezone.now()
    limite = agora - timezone.timedelta(hours=20)
    avisados = 0

    obrigatorios = (
        Document.objects.filter(
            is_required=True, status=Document.Status.PUBLISHED, versions__is_active=True
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=agora))
        .select_related("company")
        .prefetch_related("versions")
        .distinct()
    )

    for documento in obrigatorios:
        versao = documento.active_version()
        if versao is None:
            continue

        ja_aceitaram = set(
            DocumentAcceptance.objects.filter(document_version=versao).values_list(
                "user_id", flat=True
            )
        )
        pendentes = User.objects.filter(
            company_id=documento.company_id, is_active=True, role="colaborador"
        ).exclude(pk__in=ja_aceitaram)

        titulo = f"Documento pendente: {documento.title}"
        ja_avisados = set(
            Notification.objects.filter(
                user__in=pendentes, title=titulo, created_at__gte=limite
            ).values_list("user_id", flat=True)
        )
        alvo = [u for u in pendentes if u.pk not in ja_avisados]
        if not alvo:
            continue

        avisados += notify(
            alvo,
            titulo,
            f'"{documento.title}" exige seu aceite. Abra a Biblioteca para ler e confirmar.',
            category=Category.DOCUMENT,
            email=True,
            link=f"/documents/{documento.pk}",
        )

    logger.info("Documentos obrigatórios: %d lembrete(s) enviado(s).", avisados)
    return avisados


@shared_task(ignore_result=True)
def arquivar_documentos_expirados() -> int:
    """
    Move para arquivado o que passou da validade.

    Arquivar em vez de excluir: o histórico de aceites precisa continuar
    existindo mesmo depois de o documento sair de circulação.
    """
    from apps.documents.models import Document

    expirados = Document.objects.filter(
        status=Document.Status.PUBLISHED,
        expires_at__isnull=False,
        expires_at__lte=timezone.now(),
    )
    quantidade = expirados.update(status=Document.Status.ARCHIVED)
    if quantidade:
        logger.info("%d documento(s) expirado(s) arquivado(s).", quantidade)
    return quantidade
