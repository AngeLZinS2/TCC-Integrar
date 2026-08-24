"""
Regra de segmentação de comunicados.

Fora da view de propósito: é a regra que decide QUEM vê o quê, e precisa
ser testável isoladamente.

Semântica: os alvos NARROWED (afunilam), não somam. Um comunicado marcado
para "TI" + "Desenvolvedor" é para os desenvolvedores DE TI — não para todo
o TI mais todos os desenvolvedores da empresa. Cada dimensão vazia
significa "sem restrição nesta dimensão".

    alvo de setor vazio      → qualquer setor
    alvo de cargo vazio      → qualquer cargo
    ambos vazios             → empresa inteira
"""

from django.db.models import Q
from django.utils import timezone

from apps.common.segmentation import narrow_to_user

from .models import Announcement


def visible_to(user, queryset=None):
    """
    Restringe os comunicados ao que `user` pode ver.

    Quem administra a empresa enxerga tudo, inclusive rascunhos e
    comunicados de outros setores — precisa disso para gerenciar.
    """
    queryset = queryset if queryset is not None else Announcement.objects.all()

    if not user.is_authenticated or not user.company_id:
        return queryset.none()

    # `annotate` abaixo limpa o ordering do Meta; fixado aqui para a
    # paginação não devolver resultados inconsistentes entre páginas.
    queryset = queryset.filter(company_id=user.company_id).order_by("-created_at")

    if user.manages_company:
        # Quem gerencia ve tambem rascunho e agendado — precisa disso para
        # revisar antes de publicar.
        return queryset

    # Para os demais, so o que esta publicado e dentro da validade. Sem
    # isto, um rascunho ficaria visivel para a empresa inteira.
    agora = timezone.now()
    queryset = queryset.filter(status=Announcement.Status.PUBLISHED).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=agora)
    )

    return narrow_to_user(
        queryset,
        user,
        [
            (Announcement.target_sectors, "sector_id", "announcement_id",
             user.sector_id, "setor"),
            (Announcement.target_positions, "position_id", "announcement_id",
             user.position_id, "cargo"),
            (Announcement.target_units, "unit_id", "announcement_id",
             user.unit_id, "unidade"),
        ],
    ).order_by("-created_at")


def audience_of(announcement) -> list:
    """
    Quem este comunicado alcança.

    O espelho de `visible_to`, na direção oposta: em vez de "quais
    comunicados esta pessoa vê", responde "quais pessoas veem este
    comunicado". As duas precisam concordar, então a regra de afunilamento
    é a mesma — alvo vazio numa dimensão significa "sem restrição".
    """
    from apps.users.models import User

    destinatarios = User.objects.filter(
        company_id=announcement.company_id, is_active=True
    ).exclude(role="owner")

    setores = list(announcement.target_sectors.values_list("id", flat=True))
    if setores:
        destinatarios = destinatarios.filter(sector_id__in=setores)

    cargos = list(announcement.target_positions.values_list("id", flat=True))
    if cargos:
        destinatarios = destinatarios.filter(position_id__in=cargos)

    unidades = list(announcement.target_units.values_list("id", flat=True))
    if unidades:
        destinatarios = destinatarios.filter(unit_id__in=unidades)

    return list(destinatarios)
