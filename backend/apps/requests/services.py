"""
Regras de negócio das solicitações.

Fora das views de propósito (Módulo 40): a máquina de estados e quem é
notificado em cada transição precisam ser testáveis sem HTTP, e as mesmas
regras valem para qualquer entrada — API hoje, importação ou automação
amanhã.
"""

import logging

from django.db.models import Q
from django.utils import timezone

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.notifications.channels import Category, notify

from .models import HRRequest, RequestHistory

logger = logging.getLogger(__name__)

# Para onde cada status pode ir. Fechar é terminal: uma solicitação
# concluída ou cancelada não volta — o histórico ficaria mentindo.
TRANSICOES_PERMITIDAS = {
    HRRequest.Status.RECEIVED: {
        HRRequest.Status.IN_REVIEW,
        HRRequest.Status.IN_PROGRESS,
        HRRequest.Status.COMPLETED,
        HRRequest.Status.CANCELLED,
    },
    HRRequest.Status.IN_REVIEW: {
        HRRequest.Status.IN_PROGRESS,
        HRRequest.Status.COMPLETED,
        HRRequest.Status.CANCELLED,
    },
    HRRequest.Status.IN_PROGRESS: {
        HRRequest.Status.COMPLETED,
        HRRequest.Status.CANCELLED,
    },
    HRRequest.Status.COMPLETED: set(),
    HRRequest.Status.CANCELLED: set(),
}


def visible_to(user, queryset=None):
    """
    Solicitações que `user` enxerga.

    RH/admin veem todas as da empresa. Os demais veem as próprias e as que
    estão sob sua responsabilidade — um gestor precisa acompanhar o que lhe
    foi atribuído, sem ganhar acesso à fila inteira.
    """
    queryset = queryset if queryset is not None else HRRequest.objects.all()

    if not user.is_authenticated or not user.company_id:
        return queryset.none()

    queryset = queryset.filter(company_id=user.company_id)
    if user.manages_company:
        return queryset
    return queryset.filter(Q(requester=user) | Q(assigned_to=user))


def prazo_para(prioridade: str):
    """Data limite de atendimento a partir da prioridade."""
    horas = HRRequest.SLA_HORAS.get(prioridade, 72)
    return timezone.now() + timezone.timedelta(hours=horas)


def abrir(*, company, requester, **dados) -> HRRequest:
    """
    Abre uma solicitação, registra no histórico e avisa o RH.

    Empresa e solicitante vêm sempre de quem está autenticado — nunca do
    corpo da requisição.
    """
    solicitacao = HRRequest.objects.create(
        company=company,
        requester=requester,
        due_at=prazo_para(dados.get("priority", HRRequest.Priority.NORMAL)),
        **dados,
    )

    RequestHistory.objects.create(
        request=solicitacao,
        actor=requester,
        action_type=RequestHistory.ActionType.CREATED,
        details="Solicitação aberta.",
    )

    _avisar_equipe_de_rh(
        solicitacao,
        f"Nova solicitação {solicitacao.number}",
        f"{requester.full_name} abriu: {solicitacao.subject}",
    )
    audit.record(
        requester, AuditLog.Action.CREATE, "hr_request",
        resource_id=solicitacao.pk, resource_label=solicitacao.number,
    )
    return solicitacao


def mudar_status(solicitacao: HRRequest, *, novo_status: str, actor) -> HRRequest:
    """
    Aplica uma transição de status.

    Levanta ValueError quando a transição não é permitida — quem chama
    converte em 400.
    """
    atual = solicitacao.status
    if novo_status == atual:
        return solicitacao

    if novo_status not in TRANSICOES_PERMITIDAS.get(atual, set()):
        rotulos = dict(HRRequest.Status.choices)
        raise ValueError(
            f'Não é possível mudar de "{rotulos.get(atual, atual)}" para '
            f'"{rotulos.get(novo_status, novo_status)}".'
        )

    agora = timezone.now()
    solicitacao.status = novo_status
    campos = ["status"]

    if novo_status == HRRequest.Status.COMPLETED:
        solicitacao.resolved_at = agora
        solicitacao.closed_at = agora
        campos += ["resolved_at", "closed_at"]
    elif novo_status == HRRequest.Status.CANCELLED:
        solicitacao.closed_at = agora
        campos.append("closed_at")

    solicitacao.save(update_fields=campos)

    acao = {
        HRRequest.Status.COMPLETED: RequestHistory.ActionType.CLOSED,
        HRRequest.Status.CANCELLED: RequestHistory.ActionType.CANCELLED,
    }.get(novo_status, RequestHistory.ActionType.STATUS_CHANGED)

    rotulos = dict(HRRequest.Status.choices)
    RequestHistory.objects.create(
        request=solicitacao,
        actor=actor,
        action_type=acao,
        details=f'Status alterado de "{rotulos.get(atual)}" para "{rotulos.get(novo_status)}".',
    )

    # O solicitante é avisado de qualquer mudança, menos quando foi ele
    # mesmo quem mexeu — ninguém precisa ser notificado do próprio clique.
    if solicitacao.requester_id != getattr(actor, "id", None):
        notify(
            solicitacao.requester,
            f"Solicitação {solicitacao.number}: {rotulos.get(novo_status)}",
            solicitacao.subject,
            category=Category.REQUEST,
            email=True,
            link=f"/requests/{solicitacao.pk}",
        )

    audit.record(
        actor, AuditLog.Action.UPDATE, "hr_request",
        resource_id=solicitacao.pk, resource_label=solicitacao.number,
        metadata={"from": atual, "to": novo_status},
    )
    return solicitacao


def atribuir(solicitacao: HRRequest, *, responsavel, actor) -> HRRequest:
    """Define o responsável e avisa quem assumiu."""
    solicitacao.assigned_to = responsavel
    solicitacao.save(update_fields=["assigned_to"])

    nome = responsavel.full_name if responsavel else "ninguém"
    RequestHistory.objects.create(
        request=solicitacao,
        actor=actor,
        action_type=RequestHistory.ActionType.ASSIGNED,
        details=f"Atendimento atribuído a {nome}.",
    )

    if responsavel and responsavel.id != getattr(actor, "id", None):
        notify(
            responsavel,
            f"Solicitação {solicitacao.number} atribuída a você",
            solicitacao.subject,
            category=Category.REQUEST,
            email=True,
            link=f"/requests/{solicitacao.pk}",
        )

    audit.record(
        actor, AuditLog.Action.UPDATE, "hr_request",
        resource_id=solicitacao.pk, resource_label=solicitacao.number,
        metadata={"assigned_to": getattr(responsavel, "id", None)},
    )
    return solicitacao


def comentar(solicitacao: HRRequest, *, autor, texto: str, interno: bool = False):
    """
    Registra um comentário e avisa a outra parte.

    Nota interna não notifica o solicitante — ele nem a enxerga.
    """
    from .models import RequestComment

    comentario = RequestComment.objects.create(
        request=solicitacao, author=autor, text=texto, is_internal=interno
    )

    RequestHistory.objects.create(
        request=solicitacao,
        actor=autor,
        action_type=RequestHistory.ActionType.COMMENTED,
        details="Nota interna adicionada." if interno else "Novo comentário.",
    )

    if not interno:
        # Quem comentou é o solicitante? avisa o RH. Foi o RH? avisa o
        # solicitante. Ninguém recebe aviso do próprio comentário.
        if autor.id == solicitacao.requester_id:
            _avisar_equipe_de_rh(
                solicitacao,
                f"Novo comentário em {solicitacao.number}",
                f"{autor.full_name}: {texto[:120]}",
            )
        else:
            notify(
                solicitacao.requester,
                f"Novo comentário em {solicitacao.number}",
                texto[:160],
                category=Category.REQUEST,
                link=f"/requests/{solicitacao.pk}",
            )

    audit.record(
        autor, AuditLog.Action.UPDATE, "hr_request_comment",
        resource_id=solicitacao.pk, resource_label=solicitacao.number,
        metadata={"internal": interno},
    )
    return comentario


def _avisar_equipe_de_rh(solicitacao, titulo: str, mensagem: str) -> None:
    """
    Avisa quem cuida da fila.

    Com responsável definido, só ele recebe — evita notificar a equipe
    inteira sobre algo que já tem dono.
    """
    from apps.users.models import User

    if solicitacao.assigned_to_id:
        destinatarios = [solicitacao.assigned_to]
    else:
        destinatarios = list(
            User.objects.filter(
                company_id=solicitacao.company_id,
                is_active=True,
                role__in=["rh_admin", "company_admin"],
            )
        )

    notify(
        destinatarios,
        titulo,
        mensagem,
        category=Category.REQUEST,
        link=f"/requests/{solicitacao.pk}",
    )
