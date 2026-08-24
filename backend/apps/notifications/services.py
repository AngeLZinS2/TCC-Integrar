"""
Criação de notificações automáticas do sistema.

Centraliza a escrita de notificações para que os signals fiquem apenas
com a regra de "quando notificar", sem repetir o "como notificar".
"""

from django.db.models import Q

from .models import Notification


def notify(user, title, message):
    """Cria uma notificação para um único usuário. Ignora usuário inválido."""
    if user is None or not user.pk:
        return None
    return Notification.objects.create(user=user, title=title, message=message)


def notify_many(users, title, message):
    """
    Cria a mesma notificação para vários usuários em uma única query.
    Retorna a quantidade de notificações criadas.
    """
    notifications = [
        Notification(user=user, title=title, message=message) for user in users
    ]
    if not notifications:
        return 0
    Notification.objects.bulk_create(notifications)
    return len(notifications)


def eligible_courses_for(user):
    """
    Treinamentos visíveis para um colaborador — espelha exatamente a regra
    de `CourseViewSet.get_queryset`: geral (sem setor) ou do setor dele,
    sem cargo definido ou do cargo dele, e endereçado à unidade dele. As
    duas precisam concordar — se divergirem, o aviso de "novo treinamento"
    chega para quem não consegue abrir o treinamento.
    """
    from apps.courses.models import Course

    if not user.company_id:
        return Course.objects.none()

    sector_filter = Q(sector__isnull=True)
    if user.sector_id:
        sector_filter |= Q(sector_id=user.sector_id)

    position_filter = Q(position__isnull=True)
    if user.position_id:
        position_filter |= Q(position_id=user.position_id)

    from apps.common.segmentation import narrow_to_user

    queryset = Course.objects.filter(company_id=user.company_id).filter(
        sector_filter & position_filter
    )
    return narrow_to_user(
        queryset,
        user,
        [(Course.target_units, "unit_id", "course_id", user.unit_id, "unidade")],
    )


def eligible_checklist_items_for(user):
    """
    Itens de checklist visíveis para um colaborador — espelha a regra de
    `ChecklistViewSet.get_queryset`: geral (sem setor) ou do setor dele.
    """
    from apps.checklist.models import ChecklistItem

    if not user.company_id:
        return ChecklistItem.objects.none()

    sector_filter = Q(sector__isnull=True)
    if user.sector_id:
        sector_filter |= Q(sector_id=user.sector_id)

    return ChecklistItem.objects.filter(company_id=user.company_id).filter(sector_filter)


def colaboradores_for_scope(company_id, sector_id=None, position_id=None):
    """
    Colaboradores ativos de uma empresa que enxergam um conteúdo com o
    escopo informado. `sector_id`/`position_id` nulos significam "geral",
    ou seja, todo mundo da empresa vê.
    """
    from apps.users.models import User

    users = User.objects.filter(
        company_id=company_id, role="colaborador", is_active=True
    )
    if sector_id:
        users = users.filter(sector_id=sector_id)
    if position_id:
        users = users.filter(position_id=position_id)
    return users
