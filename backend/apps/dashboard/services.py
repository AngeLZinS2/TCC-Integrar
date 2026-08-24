"""
Camada de agregação de estatísticas para o Painel RH.

Todas as consultas são feitas em lote (poucas queries no total, independente
do número de colaboradores) para evitar N+1: as tabelas de Course e
ChecklistItem são pequenas e carregadas inteiras uma única vez, e o
progresso de cada colaborador é buscado com `.values()` e indexado em
dicionários para lookup O(1).

Elegibilidade de curso/checklist reproduz exatamente as mesmas regras já
usadas em `CourseViewSet.get_queryset` e `ChecklistViewSet.get_queryset`.
"""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.checklist.models import ChecklistItem, ChecklistProgress
from apps.courses.models import Course, CourseProgress
from apps.sectors.models import Sector
from apps.users.models import User

# Prazo real em dias corridos após a contratação, por categoria de prazo.
DEADLINE_OFFSET_DAYS = {"day1": 1, "week1": 7, "month1": 30}


def _due_date(hire_date, deadline_code):
    """Data real de vencimento, ou None se não houver data de contratação/prazo definido."""
    if hire_date is None or not deadline_code:
        return None
    return hire_date + timedelta(days=DEADLINE_OFFSET_DAYS[deadline_code])


def _eligible_course_ids(user, courses):
    return {
        c["id"]
        for c in courses
        if (c["sector_id"] is None or c["sector_id"] == user.sector_id)
        and (c["position_id"] is None or c["position_id"] == user.position_id)
    }


def _eligible_checklist_ids(user, checklist_items):
    return {
        i["id"]
        for i in checklist_items
        if i["sector_id"] is None or i["sector_id"] == user.sector_id
    }


def _percent(completed, total):
    """Colaborador sem itens elegíveis é considerado 100% em dia."""
    if total == 0:
        return 100
    return round(completed / total * 100)


def _load_lookups(users, company):
    courses = list(Course.objects.filter(company=company).values("id", "sector_id", "position_id", "deadline"))
    checklist_items = list(
        ChecklistItem.objects.filter(company=company).values("id", "sector_id", "deadline")
    )

    course_status = {
        (row["user_id"], row["course_id"]): row["status"]
        for row in CourseProgress.objects.filter(user__in=users).values("user_id", "course_id", "status")
    }
    checklist_completed = {
        (row["user_id"], row["item_id"])
        for row in ChecklistProgress.objects.filter(user__in=users, completed=True).values("user_id", "item_id")
    }
    return courses, checklist_items, course_status, checklist_completed


def _collaborator_row(user, courses, checklist_items, course_status, checklist_completed):
    eligible_course_ids = _eligible_course_ids(user, courses)
    eligible_item_ids = _eligible_checklist_ids(user, checklist_items)

    courses_completed = sum(
        1 for cid in eligible_course_ids if course_status.get((user.id, cid)) == "completed"
    )
    checklist_completed_count = sum(
        1 for iid in eligible_item_ids if (user.id, iid) in checklist_completed
    )

    courses_total = len(eligible_course_ids)
    checklist_total = len(eligible_item_ids)
    courses_percent = _percent(courses_completed, courses_total)
    checklist_percent = _percent(checklist_completed_count, checklist_total)

    today = timezone.localdate()
    course_deadline_by_id = {c["id"]: c["deadline"] for c in courses}
    item_deadline_by_id = {i["id"]: i["deadline"] for i in checklist_items}

    overdue_count = 0
    for cid in eligible_course_ids:
        if course_status.get((user.id, cid)) == "completed":
            continue
        due = _due_date(user.hire_date, course_deadline_by_id.get(cid))
        if due is not None and due < today:
            overdue_count += 1
    for iid in eligible_item_ids:
        if (user.id, iid) in checklist_completed:
            continue
        due = _due_date(user.hire_date, item_deadline_by_id.get(iid))
        if due is not None and due < today:
            overdue_count += 1

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "sector_name": user.sector.name if user.sector_id else None,
        "position_name": user.position.name if user.position_id else None,
        "is_active": user.is_active,
        "is_sector_leader": user.is_sector_leader,
        "last_login": user.last_login,
        "hire_date": user.hire_date,
        "courses_total": courses_total,
        "courses_completed": courses_completed,
        "courses_percent": courses_percent,
        "checklist_total": checklist_total,
        "checklist_completed": checklist_completed_count,
        "checklist_percent": checklist_percent,
        "overall_percent": round((courses_percent + checklist_percent) / 2),
        "overdue_count": overdue_count,
        # Campos internos (não expostos pelos serializers, usados só nesta camada)
        "_eligible_course_ids": eligible_course_ids,
        "_eligible_item_ids": eligible_item_ids,
        "_sector_id": user.sector_id,
    }


def get_collaborators_list(
    company,
    search=None,
    sector_id=None,
    position_id=None,
    is_active=None,
    hired_from=None,
    hired_to=None,
):
    """
    Lista completa (sem paginação) de colaboradores de uma empresa com
    estatísticas.

    A empresa vem sempre do chamador, que a resolve do usuário autenticado —
    nunca de parâmetro do cliente. Os demais filtros são refinamentos
    DENTRO desse escopo, então não há como usá-los para sair do tenant.
    """
    queryset = User.objects.filter(role="colaborador", company=company).select_related("sector", "position")
    if sector_id:
        queryset = queryset.filter(sector_id=sector_id)
    if position_id:
        queryset = queryset.filter(position_id=position_id)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    if hired_from:
        queryset = queryset.filter(hire_date__gte=hired_from)
    if hired_to:
        queryset = queryset.filter(hire_date__lte=hired_to)
    if search:
        queryset = queryset.filter(Q(full_name__icontains=search) | Q(email__icontains=search))

    users = list(queryset.order_by("full_name"))
    courses, checklist_items, course_status, checklist_completed = _load_lookups(users, company)
    rows = [
        _collaborator_row(user, courses, checklist_items, course_status, checklist_completed)
        for user in users
    ]
    for row in rows:
        row.pop("_eligible_course_ids", None)
        row.pop("_eligible_item_ids", None)
        row.pop("_sector_id", None)
    return rows


def get_collaborator_detail(user):
    """Estatísticas de um colaborador + progresso individual de cada curso/item elegível."""
    courses, checklist_items, course_status, checklist_completed = _load_lookups([user], user.company)
    row = _collaborator_row(user, courses, checklist_items, course_status, checklist_completed)
    eligible_course_ids = row.pop("_eligible_course_ids")
    eligible_item_ids = row.pop("_eligible_item_ids")
    row.pop("_sector_id", None)

    course_completed_at = {
        r["course_id"]: r["completed_at"]
        for r in CourseProgress.objects.filter(user=user).values("course_id", "completed_at")
    }
    today = timezone.localdate()
    courses_qs = Course.objects.filter(id__in=eligible_course_ids).order_by("order", "title")
    row["courses"] = [
        {
            "id": course.id,
            "title": course.title,
            "status": course_status.get((user.id, course.id), "not_started"),
            "completed_at": course_completed_at.get(course.id),
            "due_date": (due := _due_date(user.hire_date, course.deadline)),
            "is_overdue": (
                due is not None
                and course_status.get((user.id, course.id)) != "completed"
                and due < today
            ),
        }
        for course in courses_qs
    ]

    checklist_completed_at = {
        r["item_id"]: r["completed_at"]
        for r in ChecklistProgress.objects.filter(user=user, completed=True).values("item_id", "completed_at")
    }
    items_qs = ChecklistItem.objects.filter(id__in=eligible_item_ids).order_by("deadline", "order")
    row["checklist_items"] = [
        {
            "id": item.id,
            "title": item.title,
            "deadline": item.deadline,
            "completed": item.id in checklist_completed_at,
            "completed_at": checklist_completed_at.get(item.id),
            "due_date": (due := _due_date(user.hire_date, item.deadline)),
            "is_overdue": due is not None and item.id not in checklist_completed_at and due < today,
        }
        for item in items_qs
    ]
    return row


def get_dashboard_overview(company):
    """Estatísticas agregadas de todos os colaboradores de uma empresa."""
    # `is_active=False` continua entrando: desligado não some do histórico,
    # e a contagem de inativos é justamente um dos indicadores.
    users = list(User.objects.filter(role="colaborador", company=company).select_related("sector", "position"))
    courses, checklist_items, course_status, checklist_completed = _load_lookups(users, company)
    rows = [
        _collaborator_row(user, courses, checklist_items, course_status, checklist_completed)
        for user in users
    ]

    total = len(users)
    now = timezone.now()
    thirty_days_ago = now - timezone.timedelta(days=30)
    active_last_30_days = sum(1 for u in users if u.last_login and u.last_login >= thirty_days_ago)
    never_logged_in = sum(1 for u in users if u.last_login is None)

    # Quadro de pessoal
    active_collaborators = sum(1 for u in users if u.is_active)
    inactive_collaborators = total - active_collaborators
    today = timezone.localdate()
    hired_last_30_days = sum(
        1 for u in users if u.hire_date and (today - u.hire_date).days <= 30
    )
    fully_completed_count = sum(
        1 for r in rows if r["courses_percent"] == 100 and r["checklist_percent"] == 100
    )
    overdue_collaborators_count = sum(1 for r in rows if r["overdue_count"] > 0)

    # Estágio da integração de cada pessoa. Categorias mutuamente exclusivas
    # para que a soma bata com o total — "atrasado" tem prioridade sobre
    # "em andamento", já que é o estado que exige ação do RH.
    onboarding_completed = fully_completed_count
    onboarding_overdue = sum(
        1
        for r in rows
        if r["overdue_count"] > 0
        and not (r["courses_percent"] == 100 and r["checklist_percent"] == 100)
    )
    onboarding_not_started = sum(
        1
        for r in rows
        if r["courses_completed"] == 0
        and r["checklist_completed"] == 0
        and r["overdue_count"] == 0
    )
    onboarding_in_progress = (
        total - onboarding_completed - onboarding_overdue - onboarding_not_started
    )

    avg_course = round(sum(r["courses_percent"] for r in rows) / total, 1) if total else 0.0
    avg_checklist = round(sum(r["checklist_percent"] for r in rows) / total, 1) if total else 0.0

    distribution = {"not_started": 0, "in_progress": 0, "completed": 0}
    for user in users:
        for course_id in _eligible_course_ids(user, courses):
            status = course_status.get((user.id, course_id), "not_started")
            distribution[status] += 1

    sector_names = {sector.id: sector.name for sector in Sector.objects.filter(company=company)}
    grouped_by_sector = {}
    for row in rows:
        sector_id = row["_sector_id"]
        if sector_id is None:
            continue
        grouped_by_sector.setdefault(sector_id, []).append(row)

    by_sector = [
        {
            "sector_id": sector_id,
            "sector_name": sector_names.get(sector_id, "—"),
            "collaborators": len(sector_rows),
            "avg_course_percent": round(sum(r["courses_percent"] for r in sector_rows) / len(sector_rows), 1),
            "avg_checklist_percent": round(
                sum(r["checklist_percent"] for r in sector_rows) / len(sector_rows), 1
            ),
        }
        for sector_id, sector_rows in grouped_by_sector.items()
    ]
    by_sector.sort(key=lambda s: s["sector_name"])

    return {
        "total_collaborators": total,
        "active_collaborators": active_collaborators,
        "inactive_collaborators": inactive_collaborators,
        "hired_last_30_days": hired_last_30_days,
        "active_last_30_days": active_last_30_days,
        "never_logged_in": never_logged_in,
        "onboarding_completed": onboarding_completed,
        "onboarding_in_progress": onboarding_in_progress,
        "onboarding_overdue": onboarding_overdue,
        "onboarding_not_started": onboarding_not_started,
        "onboarding_percent": (
            round(sum(r["overall_percent"] for r in rows) / total, 1) if total else 0.0
        ),
        "avg_course_completion_percent": avg_course,
        "avg_checklist_completion_percent": avg_checklist,
        "fully_completed_count": fully_completed_count,
        "overdue_collaborators_count": overdue_collaborators_count,
        "course_status_distribution": distribution,
        "by_sector": by_sector,
    }
