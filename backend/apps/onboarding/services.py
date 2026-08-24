"""
Regras das tarefas de integração.

Duas responsabilidades: resolver QUEM executa cada tarefa e transformar um
template num plano de integração com datas reais.
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.notifications.channels import Category, notify
from apps.users import rbac

from .models import OnboardingTask, OnboardingTemplate, TemplateTask

logger = logging.getLogger(__name__)


class OnboardingError(Exception):
    """Regra de negócio violada. A view converte em 400."""


# ── Quem executa ────────────────────────────────────────────────────────────

def _rh_da_empresa(company):
    from apps.users.models import User

    return User.objects.filter(
        company=company,
        is_active=True,
        role__in=[rbac.ROLE_RH_ADMIN, rbac.ROLE_COMPANY_ADMIN],
    ).order_by("id")


def _gestor_de(employee):
    """
    Gestor do colaborador.

    Ordem: o gestor direto cadastrado nele; depois o líder do setor; depois
    alguém com papel de gestor no mesmo setor. Sem nenhum dos três, devolve
    None — a tarefa nasce sem responsável e aparece como pendência para o
    RH distribuir, o que é melhor do que cair no RH silenciosamente e
    ninguém perceber que o setor está sem gestor.
    """
    from apps.users.models import User

    if employee.manager_id:
        return employee.manager

    if not employee.sector_id:
        return None

    return (
        User.objects.filter(
            company_id=employee.company_id, sector_id=employee.sector_id, is_active=True
        )
        .filter(Q(is_sector_leader=True) | Q(role=rbac.ROLE_GESTOR))
        .order_by("-is_sector_leader", "id")
        .first()
    )


def resolver_responsavel(papel: str, employee):
    """Papel do template → pessoa concreta desta integração."""
    if papel == TemplateTask.Responsible.EMPLOYEE:
        return employee
    if papel == TemplateTask.Responsible.MANAGER:
        return _gestor_de(employee)
    if papel == TemplateTask.Responsible.HR:
        return _rh_da_empresa(employee.company).first()
    return None


# ── Templates que se aplicam ────────────────────────────────────────────────

def templates_para(employee):
    """
    Templates que valem para este colaborador, do mais específico para o
    mais genérico.

    Um template de setor+cargo descreve a integração melhor do que um
    genérico da empresa, então ele vence — aplicar os dois geraria a mesma
    tarefa duas vezes.
    """
    aplicaveis = OnboardingTemplate.objects.filter(
        company_id=employee.company_id, is_active=True, apply_automatically=True
    ).filter(
        Q(sector__isnull=True) | Q(sector_id=employee.sector_id)
    ).filter(
        Q(position__isnull=True) | Q(position_id=employee.position_id)
    )

    def especificidade(t):
        return (t.position_id is not None, t.sector_id is not None)

    ordenados = sorted(aplicaveis, key=especificidade, reverse=True)
    return ordenados[:1]


# ── Geração ─────────────────────────────────────────────────────────────────

@transaction.atomic
def aplicar_template(template: OnboardingTemplate, employee, *, criado_por=None) -> list:
    """
    Gera as tarefas do template para um colaborador.

    Idempotente por (colaborador, tarefa do template): reaplicar o template
    — por retry da task, por duplo clique, ou porque o RH aplicou de novo
    sem querer — não duplica o plano de integração.
    """
    if template.company_id != employee.company_id:
        raise OnboardingError("Template de outra empresa.")

    base = employee.hire_date or timezone.localdate()
    ja_geradas = set(
        OnboardingTask.objects.filter(
            employee=employee, template_task__template=template
        ).values_list("template_task_id", flat=True)
    )

    criadas = []
    for modelo in template.tasks.all():
        if modelo.id in ja_geradas:
            continue
        criadas.append(
            OnboardingTask(
                company_id=employee.company_id,
                employee=employee,
                assigned_to=resolver_responsavel(modelo.responsible, employee),
                title=modelo.title,
                description=modelo.description,
                due_date=base + timedelta(days=modelo.days_offset),
                priority=modelo.priority,
                order=modelo.order,
                template_task=modelo,
                created_by=criado_por,
            )
        )

    if not criadas:
        return []

    OnboardingTask.objects.bulk_create(criadas)

    audit.record(
        criado_por, AuditLog.Action.CREATE, "onboarding_plan",
        resource_id=template.pk, resource_label=template.name,
        metadata={"employee": employee.email, "tasks": len(criadas)},
    )
    _avisar_responsaveis(criadas, employee)
    return criadas


def _avisar_responsaveis(tarefas, employee) -> None:
    """
    Um aviso por pessoa, com o total — e não um por tarefa.

    Um template de dez itens mandaria dez notificações para o mesmo RH.
    Agrupar é o que mantém a caixa utilizável.
    """
    por_pessoa = {}
    for tarefa in tarefas:
        if tarefa.assigned_to_id:
            por_pessoa.setdefault(tarefa.assigned_to, []).append(tarefa)

    for pessoa, suas in por_pessoa.items():
        quantidade = len(suas)
        if pessoa.pk == employee.pk:
            titulo = "Suas tarefas de integração"
            texto = f"Você tem {quantidade} tarefa(s) para concluir sua integração."
        else:
            titulo = f"Integração de {employee.full_name}"
            texto = (
                f"{quantidade} tarefa(s) de integração foram atribuídas a você."
            )
        notify(
            pessoa, titulo, texto,
            category=Category.TASK, email=True, link="/onboarding",
        )


def aplicar_templates_automaticos(employee, *, criado_por=None) -> list:
    """Chamado quando um colaborador é cadastrado."""
    criadas = []
    for template in templates_para(employee):
        criadas += aplicar_template(template, employee, criado_por=criado_por)
    return criadas


# ── Mudança de estado ───────────────────────────────────────────────────────

def pode_concluir(tarefa: OnboardingTask, user) -> bool:
    """
    Conclui quem executa — ou quem administra a integração.

    O colaborador integrado NÃO fecha tarefa que não é dele: senão bastaria
    marcar "conferir documentação" como feita para pular a conferência do
    RH.
    """
    if user.has_perm_code(rbac.ONBOARDING_MANAGE):
        return True
    return tarefa.assigned_to_id == user.pk


@transaction.atomic
def mudar_status(tarefa: OnboardingTask, novo: str, user) -> OnboardingTask:
    if novo not in OnboardingTask.Status.values:
        raise OnboardingError("Status inválido.")
    if not pode_concluir(tarefa, user):
        raise OnboardingError("Você não é o responsável por esta tarefa.")
    if tarefa.status == novo:
        return tarefa

    anterior = tarefa.status
    tarefa.status = novo

    if novo == OnboardingTask.Status.COMPLETED:
        tarefa.completed_at = timezone.now()
        tarefa.completed_by = user
    else:
        # Reabrir limpa a marca: deixá-la faria o painel contar como
        # concluída no dia errado.
        tarefa.completed_at = None
        tarefa.completed_by = None

    tarefa.save(update_fields=["status", "completed_at", "completed_by", "updated_at"])

    audit.record(
        user, AuditLog.Action.UPDATE, "onboarding_task",
        resource_id=tarefa.pk, resource_label=tarefa.title,
        metadata={"de": anterior, "para": novo},
    )

    if novo == OnboardingTask.Status.COMPLETED:
        _avisar_conclusao(tarefa, user)
    return tarefa


def _avisar_conclusao(tarefa: OnboardingTask, user) -> None:
    """
    Avisa o colaborador quando alguém concluiu uma tarefa DELE.

    Quando ele mesmo concluiu, avisar seria falar sozinho.
    """
    if tarefa.employee_id == user.pk:
        return
    notify(
        tarefa.employee,
        "Etapa da sua integração concluída",
        f'"{tarefa.title}" foi concluída por {user.full_name}.',
        category=Category.TASK,
        link="/onboarding",
    )


def progresso_de(employee) -> dict:
    """Resumo da integração de uma pessoa."""
    tarefas = OnboardingTask.objects.filter(employee=employee).exclude(
        status=OnboardingTask.Status.CANCELLED
    )
    total = tarefas.count()
    concluidas = tarefas.filter(status=OnboardingTask.Status.COMPLETED).count()
    atrasadas = sum(1 for t in tarefas if t.is_overdue)
    return {
        "total": total,
        "completed": concluidas,
        "pending": total - concluidas,
        "overdue": atrasadas,
        "percent": round(concluidas / total * 100) if total else 0,
    }
