"""
Painéis dos módulos da P2 (Módulos 14, 15 e 16).

Separado de `services.py` de propósito: aquele alimenta o painel antigo,
que o app já consome. Misturar os dois obrigaria a mudar um contrato em
uso para acrescentar métrica nova.

Regra de construção: tudo por `aggregate`/`annotate`, nunca laço em cima
de queryset. Um painel de RH numa empresa com 500 pessoas é a tela mais
fácil de transformar em N+1 — e a mais visitada.
"""

from django.db.models import Count, Q
from django.utils import timezone

from apps.communications.models import Announcement
from apps.courses.models import Course, CourseProgress
from apps.courses.quiz_models import Certificate, QuizAttempt
from apps.documents.models import Document, DocumentAcceptance
from apps.onboarding.models import OnboardingTask
from apps.requests.models import HRRequest
from apps.users.models import User
from apps.users.scopes import managed_users_filter


def _percent(parte, total) -> int:
    return round(parte / total * 100) if total else 0


# ── Painel do RH (Módulo 14) ────────────────────────────────────────────────

def _metricas_solicitacoes(company) -> dict:
    agora = timezone.now()
    abertos = [HRRequest.Status.RECEIVED, HRRequest.Status.IN_REVIEW,
               HRRequest.Status.IN_PROGRESS]

    return HRRequest.objects.filter(company=company).aggregate(
        open=Count("id", filter=Q(status__in=abertos)),
        in_progress=Count("id", filter=Q(status=HRRequest.Status.IN_PROGRESS)),
        completed=Count("id", filter=Q(status=HRRequest.Status.COMPLETED)),
        # Atrasada é derivado do prazo, não um status gravado: um status
        # "atrasado" precisaria de uma rotina varrendo a tabela para
        # continuar verdadeiro, e qualquer falha dela deixaria o painel
        # mentindo.
        overdue=Count(
            "id", filter=Q(status__in=abertos, due_at__lt=agora, due_at__isnull=False)
        ),
    )


def _metricas_documentos(company) -> dict:
    agora = timezone.now()
    publicados = Document.objects.filter(
        company=company, status=Document.Status.PUBLISHED
    )

    obrigatorios = list(
        publicados.filter(is_required=True).values_list("id", flat=True)
    )
    # Público que precisa aceitar: colaboradores ativos da empresa.
    publico = User.objects.filter(
        company=company, is_active=True
    ).exclude(role="owner").count()

    aceites = DocumentAcceptance.objects.filter(
        document_version__document__company=company
    ).count()

    esperados = len(obrigatorios) * publico
    return {
        "required_total": len(obrigatorios),
        "acceptances": aceites,
        "pending_acceptances": max(esperados - aceites, 0),
        "acceptance_percent": _percent(aceites, esperados),
        "expired": publicados.filter(
            expires_at__lt=agora, expires_at__isnull=False
        ).count(),
        "published": publicados.count(),
        "drafts": Document.objects.filter(
            company=company, status=Document.Status.DRAFT
        ).count(),
    }


def _metricas_treinamentos(company) -> dict:
    progresso = CourseProgress.objects.filter(course__company=company).aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status="completed")),
        in_progress=Count("id", filter=Q(status="in_progress")),
    )

    # Aprovação/reprovação vêm das TENTATIVAS finalizadas, não do progresso:
    # treinamento sem avaliação não tem nota, e contá-lo distorceria a taxa.
    # Os apelidos NAO podem repetir o nome da coluna: com `passed=Count(...)`,
    # o `Q(passed=True)` de dentro passa a resolver contra o proprio apelido
    # e o Django recusa com "'passed' is an aggregate".
    tentativas = QuizAttempt.objects.filter(
        quiz__course__company=company, finished_at__isnull=False
    ).aggregate(
        total=Count("id"),
        aprovadas=Count("id", filter=Q(passed=True)),
        reprovadas=Count("id", filter=Q(passed=False)),
    )

    return {
        "assignments": progresso["total"],
        "completed": progresso["completed"],
        "in_progress": progresso["in_progress"],
        "completion_percent": _percent(progresso["completed"], progresso["total"]),
        "quiz_attempts": tentativas["total"],
        "quiz_passed": tentativas["aprovadas"],
        "quiz_failed": tentativas["reprovadas"],
        "pass_rate": _percent(tentativas["aprovadas"], tentativas["total"]),
        "certificates": Certificate.objects.filter(company=company).count(),
    }


def _metricas_onboarding(company, *, employee_ids=None) -> dict:
    tarefas = OnboardingTask.objects.filter(company=company).exclude(
        status=OnboardingTask.Status.CANCELLED
    )
    if employee_ids is not None:
        tarefas = tarefas.filter(employee_id__in=employee_ids)

    hoje = timezone.localdate()
    abertos = [OnboardingTask.Status.PENDING, OnboardingTask.Status.IN_PROGRESS]

    numeros = tarefas.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=OnboardingTask.Status.COMPLETED)),
        pending=Count("id", filter=Q(status__in=abertos)),
        overdue=Count(
            "id",
            filter=Q(status__in=abertos, due_date__lt=hoje, due_date__isnull=False),
        ),
    )
    numeros["completion_percent"] = _percent(numeros["completed"], numeros["total"])
    return numeros


def _metricas_comunicacao(company) -> dict:
    publicados = Announcement.objects.filter(
        company=company, status=Announcement.Status.PUBLISHED
    )
    total = publicados.count()

    leituras = (
        publicados.aggregate(total=Count("reads", distinct=True))["total"] or 0
    )
    publico = User.objects.filter(
        company=company, is_active=True
    ).exclude(role="owner").count()

    return {
        "published": total,
        "scheduled": Announcement.objects.filter(
            company=company, status=Announcement.Status.SCHEDULED
        ).count(),
        "drafts": Announcement.objects.filter(
            company=company, status=Announcement.Status.DRAFT
        ).count(),
        "reads": leituras,
        # Alcance médio: quantos por cento do público leram, em média. Com
        # público zero devolve 0 em vez de dividir por zero.
        "read_percent": _percent(leituras, total * publico),
    }


def painel_rh(company) -> dict:
    """Métricas dos módulos da P2 para o RH."""
    return {
        "requests": _metricas_solicitacoes(company),
        "documents": _metricas_documentos(company),
        "trainings": _metricas_treinamentos(company),
        "onboarding": _metricas_onboarding(company),
        "communication": _metricas_comunicacao(company),
    }


# ── Home do colaborador (Módulo 15) ─────────────────────────────────────────

def home_do_colaborador(user) -> dict:
    """
    O que exige AÇÃO da pessoa, primeiro.

    O spec é explícito: "o dashboard deve priorizar o que exige ação". Por
    isso a Home devolve contadores de pendência, e não um resumo do que já
    está feito.
    """
    from apps.communications.services import visible_to
    from apps.events.views import eventos_visiveis
    from apps.notifications.models import Notification
    from apps.onboarding.services import progresso_de

    agora = timezone.now()
    hoje = timezone.localdate()

    # Onboarding
    onboarding = progresso_de(user)
    minhas_tarefas = OnboardingTask.objects.filter(
        employee=user,
        status__in=[OnboardingTask.Status.PENDING, OnboardingTask.Status.IN_PROGRESS],
    )

    # Treinamentos pendentes = elegíveis que ainda não foram concluídos.
    from apps.notifications.services import eligible_courses_for

    elegiveis = list(eligible_courses_for(user).values_list("id", flat=True))
    concluidos = set(
        CourseProgress.objects.filter(
            user=user, course_id__in=elegiveis, status="completed"
        ).values_list("course_id", flat=True)
    )

    # Documentos obrigatórios aguardando aceite — a MESMA regra da
    # listagem. Contar por conta própria aqui já tinha divergido dela.
    from apps.documents.services import pendentes_de_aceite

    pendentes_documento = pendentes_de_aceite(user).count()

    return {
        "greeting_name": user.full_name.split(" ")[0],
        "onboarding": onboarding,
        "pending": {
            "onboarding_tasks": minhas_tarefas.count(),
            "overdue_tasks": minhas_tarefas.filter(
                due_date__lt=hoje, due_date__isnull=False
            ).count(),
            "trainings": len(elegiveis) - len(concluidos),
            "documents": pendentes_documento,
            "notifications": Notification.objects.filter(
                user=user, read=False
            ).count(),
        },
        "announcements": visible_to(user)[:5].count(),
        "upcoming_events": eventos_visiveis(user)
        .filter(start_at__gte=agora)
        .count(),
    }


# ── Painel do gestor (Módulo 16) ────────────────────────────────────────────

def painel_do_gestor(user) -> dict:
    """
    Só o escopo dele.

    A equipe sai de `managed_users_filter`, o mesmo filtro que governa a
    listagem de colaboradores. Duplicar a regra aqui é como o gestor
    acabaria enxergando a empresa inteira num painel enquanto a lista mostra
    só a equipe.
    """
    equipe = User.objects.filter(
        company_id=user.company_id, role="colaborador"
    ).filter(managed_users_filter(user))

    ids = list(equipe.values_list("id", flat=True))
    total = len(ids)

    progresso = CourseProgress.objects.filter(user_id__in=ids).aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status="completed")),
    )

    hoje = timezone.localdate()
    abertos = [OnboardingTask.Status.PENDING, OnboardingTask.Status.IN_PROGRESS]

    # Estágio da integração POR PESSOA (o spec pede "8 concluídos, 3 em
    # andamento, 1 atrasado" — pessoas, não tarefas).
    por_pessoa = {
        linha["employee_id"]: linha
        for linha in OnboardingTask.objects.filter(employee_id__in=ids)
        .exclude(status=OnboardingTask.Status.CANCELLED)
        .values("employee_id")
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=OnboardingTask.Status.COMPLETED)),
            overdue=Count(
                "id",
                filter=Q(status__in=abertos, due_date__lt=hoje, due_date__isnull=False),
            ),
        )
    }

    concluido = em_andamento = atrasado = sem_plano = 0
    for pessoa_id in ids:
        linha = por_pessoa.get(pessoa_id)
        if linha is None or linha["total"] == 0:
            sem_plano += 1
        elif linha["overdue"] > 0:
            # Atraso tem prioridade sobre "em andamento": é o estado que
            # exige ação do gestor. As categorias são exclusivas para a
            # soma bater com o total da equipe.
            atrasado += 1
        elif linha["completed"] == linha["total"]:
            concluido += 1
        else:
            em_andamento += 1

    return {
        "team_size": total,
        "onboarding": {
            "completed": concluido,
            "in_progress": em_andamento,
            "overdue": atrasado,
            "not_started": sem_plano,
        },
        "trainings": {
            "assignments": progresso["total"],
            "completed": progresso["completed"],
            "completion_percent": _percent(progresso["completed"], progresso["total"]),
        },
        "tasks": _metricas_onboarding(user.company, employee_ids=ids),
        "birthdays": _aniversariantes_da_equipe(equipe),
    }


def _aniversariantes_da_equipe(equipe) -> list:
    """
    Aniversariantes do mês, sem expor a data de nascimento completa.

    Devolve só dia/mês: o ano revela a idade, que não é informação que um
    painel de equipe precisa carregar.
    """
    hoje = timezone.localdate()
    aniversariantes = equipe.filter(
        birth_date__month=hoje.month, birth_date__isnull=False, is_active=True
    ).order_by("birth_date__day")

    return [
        {
            "id": pessoa.pk,
            "full_name": pessoa.full_name,
            "birthday": pessoa.birth_date.strftime("%d/%m"),
        }
        for pessoa in aniversariantes
    ]
