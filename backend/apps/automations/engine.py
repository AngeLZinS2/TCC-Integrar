"""
O motor: recebe um evento, encontra as regras que escutam e executa.

Duas garantias importam aqui:

  1. **Nunca derruba quem disparou.** Uma automação mal configurada não
     pode impedir o cadastro de um colaborador. Toda falha vira registro
     em `AutomationRun`, nunca exceção que sobe.

  2. **Nunca cruza tenant.** O evento carrega a empresa, e só as regras
     dela são consideradas — sempre derivada do objeto, jamais de um
     `company_id` recebido de fora.
"""

import logging

from django.db import transaction

from .models import AutomationRule, AutomationRun

logger = logging.getLogger(__name__)


def _condicoes_batem(regra, contexto) -> bool:
    """Todas as condições precisam bater — elas estreitam, não somam."""
    return all(c.matches(contexto) for c in regra.conditions.all())


def _contexto_de(evento, company, employee=None, labels=None) -> dict:
    """
    Monta o dicionário que condições e ações enxergam.

    Achatar os campos do colaborador aqui (em vez de passar o objeto) é o
    que permite manter `CONDITION_FIELDS` fechado: uma condição só alcança
    o que este dicionário expõe, nunca um atributo arbitrário.
    """
    contexto = {
        "event": evento,
        "company": company,
        "employee": employee,
        "labels": {"event": evento, **(labels or {})},
    }
    if employee is not None:
        contexto.update(
            {
                "sector_id": employee.sector_id,
                "position_id": employee.position_id,
                "unit_id": employee.unit_id,
                "role": employee.role,
            }
        )
        contexto["labels"].setdefault("employee_name", employee.full_name)
    return contexto


def disparar(evento: str, company, *, employee=None, labels=None, **extra) -> int:
    """
    Executa as automações de `evento` para `company`.

    Devolve quantas regras executaram. Chamado pelos handlers de signal e
    pode ser chamado direto de um service.
    """
    if company is None:
        return 0

    regras = (
        AutomationRule.objects.filter(
            company_id=company.pk, trigger_event=evento, is_active=True
        )
        .prefetch_related("conditions", "actions")
    )

    contexto = _contexto_de(evento, company, employee=employee, labels=labels)
    contexto.update(extra)

    executadas = 0
    for regra in regras:
        if not _condicoes_batem(regra, contexto):
            _registrar(regra, AutomationRun.Status.SKIPPED, contexto, "Condição não atendida.")
            continue
        if _executar_regra(regra, contexto):
            executadas += 1
    return executadas


def _executar_regra(regra, contexto) -> bool:
    from . import actions

    resultados = []
    houve_falha = False

    for acao in regra.actions.all():
        try:
            resultados.append(f"{acao.action_type}: {actions.executar(acao, contexto)}")
        except Exception as exc:
            # Segue para as próximas ações: um erro de configuração numa
            # delas não é motivo para a regra inteira parar. O que não pode
            # é o disparo terminar marcado como bem-sucedido — daí o
            # `houve_falha`, que o admin enxerga no histórico.
            logger.exception("Automação %s falhou na ação %s.", regra.pk, acao.pk)
            resultados.append(f"{acao.action_type}: ERRO — {exc}")
            houve_falha = True

    if houve_falha:
        _registrar(
            regra, AutomationRun.Status.FAILED, contexto, " | ".join(resultados)
        )
        return False

    _registrar(
        regra, AutomationRun.Status.SUCCESS, contexto,
        " | ".join(resultados) or "Sem ações configuradas.",
    )
    return True


def _registrar(regra, status, contexto, detalhe: str) -> None:
    colaborador = contexto.get("employee")
    try:
        AutomationRun.objects.create(
            rule=regra,
            company_id=regra.company_id,
            status=status,
            subject_label=colaborador.full_name if colaborador else "",
            detail=detalhe[:2000],
        )
    except Exception:
        # O log de execução é diagnóstico; se ele falhar, não pode levar
        # junto a operação que estava sendo registrada.
        logger.exception("Não foi possível registrar a execução da automação %s.", regra.pk)


def disparar_apos_commit(evento: str, company, **kwargs) -> None:
    """
    Versão para usar dentro de signals.

    `on_commit` porque as ações leem o banco: disparar antes do COMMIT faria
    a automação enxergar um estado que ainda não existe — e, se a transação
    for revertida, o e-mail já teria saído sobre um cadastro que não
    aconteceu.
    """
    def rodar():
        try:
            disparar(evento, company, **kwargs)
        except Exception:
            logger.exception("Falha ao disparar automações de %s.", evento)

    transaction.on_commit(rodar)
