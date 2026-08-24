"""
Métricas dos módulos novos da P2 para os três painéis (Módulos 14-16).

Separado de `services.py` (que é o painel de RH original, sobre
colaboradores/onboarding-checklist) para não misturar as duas gerações de
código. Nenhuma consulta daqui reimplementa regra de negócio — todas
reaproveitam o mesmo filtro que a respectiva view usa, para o número do
painel nunca divergir do que a tela de detalhe mostra.
"""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.users.scopes import managed_users_filter


# ── RH (Módulo 14) ───────────────────────────────────────────────────────────

def solicitacoes_metrics(company) -> dict:
    from apps.requests.models import HRRequest

    qs = HRRequest.objects.filter(company=company)
    agora = timezone.now()
    return {
        "received": qs.filter(status=HRRequest.Status.RECEIVED).count(),
        "in_progress": qs.filter(
            status__in=[HRRequest.Status.IN_REVIEW, HRRequest.Status.IN_PROGRESS]
        ).count(),
        "completed": qs.filter(status=HRRequest.Status.COMPLETED).count(),
        # Mesma condição de `HRRequest.is_overdue`, em SQL: contar em
        # Python exigiria carregar a tabela inteira na memória.
        "overdue": qs.exclude(
            status__in=[HRRequest.Status.COMPLETED, HRRequest.Status.CANCELLED]
        ).filter(due_at__lt=agora).count(),
    }


def documentos_metrics(company) -> dict:
    from apps.documents.models import Document, DocumentAcceptance

    publicados = Document.objects.filter(company=company, status=Document.Status.PUBLISHED)
    obrigatorios = publicados.filter(is_required=True)
    agora = timezone.now()

    aceites = DocumentAcceptance.objects.filter(
        document_version__document__company=company
    ).count()

    vigentes_obrigatorios = obrigatorios.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=agora)
    )
    pendentes = 0
    for documento in vigentes_obrigatorios.prefetch_related("versions__acceptances"):
        versao = documento.active_version()
        if versao is None:
            continue
        # Elegibilidade por colaborador ativo, igual ao lembrete assíncrono
        # (`avisar_documentos_obrigatorios_pendentes`) — o painel não pode
        # contar diferente do e-mail que o RH recebe sobre o mesmo dado.
        aceitaram = set(versao.acceptances.values_list("user_id", flat=True))
        from apps.users.models import User

        total_elegiveis = User.objects.filter(
            company=company, is_active=True, role="colaborador"
        ).count()
        pendentes += max(total_elegiveis - len(aceitaram), 0)

    return {
        "required_pending": pendentes,
        "acceptances": aceites,
        "expired": Document.objects.filter(
            company=company, status=Document.Status.PUBLISHED, expires_at__lte=agora
        ).count(),
    }


def treinamentos_metrics(company) -> dict:
    from apps.courses.models import CourseProgress
    from apps.courses.quiz_models import QuizAttempt

    progresso = CourseProgress.objects.filter(course__company=company)
    tentativas = QuizAttempt.objects.filter(quiz__course__company=company, finished_at__isnull=False)

    return {
        "completed": progresso.filter(status="completed").count(),
        "in_progress": progresso.filter(status="in_progress").count(),
        "quiz_approved": tentativas.filter(passed=True).count(),
        "quiz_failed": tentativas.filter(passed=False).count(),
    }


def onboarding_metrics(company) -> dict:
    from apps.onboarding.models import OnboardingTask

    qs = OnboardingTask.objects.filter(company=company).exclude(status="cancelled")
    hoje = timezone.localdate()
    return {
        "pending": qs.filter(status__in=["pending", "in_progress"]).count(),
        "completed": qs.filter(status="completed").count(),
        "overdue": qs.filter(
            due_date__lt=hoje, status__in=["pending", "in_progress"]
        ).count(),
    }


def comunicacao_metrics(company) -> dict:
    from apps.communications.models import Announcement, AnnouncementRead

    publicados = Announcement.objects.filter(company=company, status=Announcement.Status.PUBLISHED)
    return {
        "published": publicados.count(),
        "views": AnnouncementRead.objects.filter(announcement__company=company).count(),
    }


def rh_module_metrics(company) -> dict:
    """Agregado dos cinco blocos do Módulo 14, numa única resposta."""
    return {
        "requests": solicitacoes_metrics(company),
        "documents": documentos_metrics(company),
        "trainings": treinamentos_metrics(company),
        "onboarding": onboarding_metrics(company),
        "communications": comunicacao_metrics(company),
    }


# ── Colaborador (Módulo 15) ─────────────────────────────────────────────────

def minha_home(user) -> dict:
    """
    O que a Home do colaborador precisa: o que exige ação primeiro, o
    contexto da empresa depois.
    """
    from apps.communications.services import visible_to as comunicados_visiveis
    from apps.courses.models import CourseProgress
    from apps.documents.models import DocumentAcceptance
    from apps.documents.views import documentos_visiveis
    from apps.events.models import Event
    from apps.events.services import proximos_aniversariantes
    from apps.events.views import eventos_visiveis
    from apps.onboarding.models import OnboardingTask
    from apps.onboarding.services import progresso_de
    from apps.users.models import User

    agora = timezone.now()

    tarefas_pendentes = OnboardingTask.objects.filter(
        employee=user, status__in=["pending", "in_progress"]
    ).count()

    treinamentos_pendentes = CourseProgress.objects.filter(
        user=user
    ).exclude(status="completed").count()

    documentos_obrigatorios = documentos_visiveis(user).filter(is_required=True)
    ids_aceitos = set(
        DocumentAcceptance.objects.filter(
            user=user, document_version__document__in=documentos_obrigatorios
        ).values_list("document_version__document_id", flat=True)
    )
    documentos_pendentes = sum(
        1 for d in documentos_obrigatorios if d.pk not in ids_aceitos
    )

    proximos_eventos = (
        eventos_visiveis(user)
        .filter(start_at__gte=agora)
        .order_by("start_at")[:5]
    )

    colegas = User.objects.filter(
        company_id=user.company_id, is_active=True
    ).exclude(role="owner")
    aniversariantes = proximos_aniversariantes(colegas, dentro_de_dias=30)[:5]

    return {
        "onboarding_progress": progresso_de(user),
        "pending_tasks": tarefas_pendentes,
        "pending_trainings": treinamentos_pendentes,
        "pending_documents": documentos_pendentes,
        "announcements_count": comunicados_visiveis(user).count(),
        "upcoming_events": [
            {
                "id": e.id, "title": e.title,
                "start_at": e.start_at, "location": e.location,
            }
            for e in proximos_eventos
        ],
        "birthdays": [
            {"id": u.id, "full_name": u.full_name, "days_until": dias}
            for dias, u in aniversariantes
        ],
        "unread_notifications": _notificacoes_nao_lidas(user),
    }


def _notificacoes_nao_lidas(user) -> int:
    from apps.notifications.models import Notification

    return Notification.objects.filter(user=user, read=False).count()


# ── Gestor (Módulo 16) ───────────────────────────────────────────────────────

def minha_equipe(manager) -> dict:
    """
    Painel do gestor. Escopado à própria equipe — a mesma regra de
    `visible_colaboradores`, para o gestor nunca ver além do que já vê na
    lista de colaboradores.
    """
    from apps.courses.models import CourseProgress
    from apps.onboarding.models import OnboardingTask
    from apps.events.services import proximos_aniversariantes
    from apps.users.models import User

    equipe = User.objects.filter(company_id=manager.company_id, is_active=True).filter(
        managed_users_filter(manager)
    )
    ids_equipe = list(equipe.values_list("id", flat=True))
    total = len(ids_equipe)

    tarefas = OnboardingTask.objects.filter(employee_id__in=ids_equipe).exclude(
        status="cancelled"
    )
    hoje = timezone.localdate()
    onboarding = {
        "completed": tarefas.filter(status="completed").count(),
        "in_progress": tarefas.filter(status="in_progress").count(),
        "pending": tarefas.filter(status="pending").count(),
        "overdue": tarefas.filter(
            due_date__lt=hoje, status__in=["pending", "in_progress"]
        ).count(),
    }

    progresso = CourseProgress.objects.filter(user_id__in=ids_equipe)
    total_progresso = progresso.count()
    concluidos = progresso.filter(status="completed").count()
    training_percent = round(concluidos / total_progresso * 100) if total_progresso else 0

    aniversariantes = proximos_aniversariantes(equipe, dentro_de_dias=30)

    return {
        "team_size": total,
        "onboarding": onboarding,
        "training_completion_percent": training_percent,
        "pending_tasks": OnboardingTask.objects.filter(
            assigned_to=manager, status__in=["pending", "in_progress"]
        ).count(),
        "birthdays": [
            {"id": u.id, "full_name": u.full_name, "days_until": dias}
            for dias, u in aniversariantes[:5]
        ],
    }
