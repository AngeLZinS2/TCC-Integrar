"""
Tarefas assíncronas do onboarding.

A geração do plano de integração sai da requisição por dois motivos: um
template grande cria dezenas de tarefas e dispara um e-mail por
responsável, o que faria o cadastro de colaborador demorar visivelmente; e
uma falha no e-mail não pode derrubar o cadastro, que é o que realmente
importa.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True, ignore_result=True, acks_late=True,
    autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3,
)
def gerar_onboarding_do_colaborador(self, user_id: int, criado_por_id: int | None = None):
    """
    Aplica os templates automáticos a um colaborador recém-cadastrado.

    Seguro para repetir: `aplicar_template` é idempotente por (colaborador,
    tarefa do template), então um retry não duplica o plano.
    """
    from apps.users.models import User

    from . import services

    colaborador = User.objects.filter(pk=user_id).first()
    if colaborador is None:
        logger.warning("Onboarding: colaborador %s não existe mais.", user_id)
        return 0

    criado_por = (
        User.objects.filter(pk=criado_por_id).first() if criado_por_id else None
    )
    criadas = services.aplicar_templates_automaticos(colaborador, criado_por=criado_por)
    logger.info(
        "Onboarding: %s tarefa(s) geradas para %s.", len(criadas), colaborador.email
    )
    return len(criadas)


@shared_task(ignore_result=True)
def avisar_tarefas_atrasadas() -> int:
    """
    Lembra os responsáveis por tarefas de integração vencidas.

    Idempotente por janela de 20 horas: duas execuções no mesmo dia geram
    um aviso só. A janela é menor que 24h para o lembrete não "pular" um
    dia quando o Beat atrasa alguns minutos.
    """
    from datetime import timedelta

    from apps.notifications.channels import Category, notify
    from apps.notifications.models import Notification

    from .models import OnboardingTask

    hoje = timezone.localdate()
    corte = timezone.now() - timedelta(hours=20)

    atrasadas = (
        OnboardingTask.objects.filter(
            due_date__lt=hoje,
            status__in=[OnboardingTask.Status.PENDING, OnboardingTask.Status.IN_PROGRESS],
            assigned_to__isnull=False,
            assigned_to__is_active=True,
        )
        .select_related("assigned_to", "employee")
    )

    # Agrupa por responsável: quem tem cinco tarefas vencidas recebe um
    # aviso dizendo cinco, não cinco avisos.
    por_pessoa = {}
    for tarefa in atrasadas:
        por_pessoa.setdefault(tarefa.assigned_to, []).append(tarefa)

    enviados = 0
    titulo = "Tarefas de integração atrasadas"
    for pessoa, tarefas in por_pessoa.items():
        ja_avisado = Notification.objects.filter(
            user=pessoa, title=titulo, created_at__gte=corte
        ).exists()
        if ja_avisado:
            continue

        nomes = ", ".join(t.title for t in tarefas[:3])
        resto = f" e mais {len(tarefas) - 3}" if len(tarefas) > 3 else ""
        notify(
            pessoa, titulo,
            f"{len(tarefas)} tarefa(s) passaram do prazo: {nomes}{resto}.",
            category=Category.TASK, email=True, link="/onboarding",
        )
        enviados += 1

    logger.info("Onboarding: %s responsável(is) avisados de atraso.", enviados)
    return enviados
