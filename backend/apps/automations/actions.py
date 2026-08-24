"""
Executores das ações.

Um registry `tipo → função`. Acrescentar uma ação é escrever a função e
registrá-la aqui; nada mais no sistema precisa saber que ela existe.

Toda função recebe `(acao, contexto)` e devolve uma string curta para o
log de execução. O `contexto` é montado em `engine.py` e sempre traz pelo
menos `company` e, quando o evento é sobre uma pessoa, `employee`.
"""

import logging

from apps.notifications.channels import Category, notify

logger = logging.getLogger(__name__)

_REGISTRY = {}


def executor(tipo):
    """Registra a função que executa um tipo de ação."""
    def decorador(func):
        _REGISTRY[tipo] = func
        return func
    return decorador


def executar(acao, contexto) -> str:
    func = _REGISTRY.get(acao.action_type)
    if func is None:
        # Ação registrada no banco mas sem executor: acontece se alguém
        # remover código sem migrar os dados. Melhor registrar e seguir do
        # que derrubar as outras ações da mesma regra.
        raise ValueError(f"Ação sem executor: {acao.action_type}")
    return func(acao, contexto)


# ── Destinatários ───────────────────────────────────────────────────────────

def destinatarios(acao, contexto) -> list:
    """
    Resolve o alvo da ação em pessoas concretas.

    Guardar o PAPEL e resolver na hora — em vez de gravar o id de alguém —
    é o que faz a automação continuar funcionando quando a pessoa muda de
    função ou sai da empresa.
    """
    from apps.onboarding.services import _gestor_de, _rh_da_empresa

    from . import catalog

    colaborador = contexto.get("employee")

    if acao.target == catalog.TARGET_EMPLOYEE:
        return [colaborador] if colaborador else []

    if acao.target == catalog.TARGET_MANAGER:
        gestor = _gestor_de(colaborador) if colaborador else None
        return [gestor] if gestor else []

    if acao.target == catalog.TARGET_HR:
        return list(_rh_da_empresa(contexto["company"]))

    return []


def _texto(acao, contexto, chave, padrao):
    """
    Interpolação simples dos campos do contexto no texto configurado.

    `str.format_map` com um dicionário comum quebraria em qualquer chave
    ausente e derrubaria a automação inteira por causa de um typo no
    formulário — daí o fallback silencioso para o placeholder original.
    """
    class _Tolerante(dict):
        def __missing__(self, chave):
            return "{" + chave + "}"

    bruto = acao.config.get(chave) or padrao
    try:
        return bruto.format_map(_Tolerante(contexto.get("labels", {})))
    except (ValueError, IndexError):
        return bruto


# ── Ações ───────────────────────────────────────────────────────────────────

@executor("send_notification")
def _send_notification(acao, contexto) -> str:
    pessoas = destinatarios(acao, contexto)
    if not pessoas:
        return "Sem destinatário."

    enviados = notify(
        pessoas,
        _texto(acao, contexto, "title", "Aviso automático"),
        _texto(acao, contexto, "message", "{event}"),
        category=Category.SYSTEM,
        link=acao.config.get("link", ""),
    )
    return f"{enviados} notificação(ões) enviadas."


@executor("send_email")
def _send_email(acao, contexto) -> str:
    pessoas = destinatarios(acao, contexto)
    if not pessoas:
        return "Sem destinatário."

    # `email=True` faz o envio ir para a fila do Celery — nunca dentro da
    # requisição que disparou o gatilho (Módulo 9).
    enviados = notify(
        pessoas,
        _texto(acao, contexto, "title", "Aviso automático"),
        _texto(acao, contexto, "message", "{event}"),
        category=Category.SYSTEM,
        email=True,
        critical=True,  # e-mail configurado explicitamente não é opt-out
        link=acao.config.get("link", ""),
    )
    return f"{enviados} e-mail(s) enfileirados."


@executor("create_onboarding")
def _create_onboarding(acao, contexto) -> str:
    from apps.onboarding.models import OnboardingTemplate
    from apps.onboarding.services import aplicar_template, aplicar_templates_automaticos

    colaborador = contexto.get("employee")
    if colaborador is None:
        return "Evento sem colaborador."

    template_id = acao.config.get("template_id")
    if template_id:
        template = OnboardingTemplate.objects.filter(
            pk=template_id, company_id=contexto["company"].pk
        ).first()
        if template is None:
            # Escopado pela empresa: um id de outro tenant simplesmente não
            # é encontrado, em vez de aplicar o roteiro de outra empresa.
            #
            # Levanta em vez de devolver aviso: um template apagado deixaria
            # a regra reportando "executada" para sempre, e o log de
            # execução existe justamente para o admin notar o contrário.
            raise ValueError("Template não encontrado nesta empresa.")
        criadas = aplicar_template(template, colaborador)
    else:
        criadas = aplicar_templates_automaticos(colaborador)

    return f"{len(criadas)} tarefa(s) de onboarding criadas."


@executor("assign_training")
def _assign_training(acao, contexto) -> str:
    from apps.courses.models import Course, CourseProgress

    colaborador = contexto.get("employee")
    if colaborador is None:
        return "Evento sem colaborador."

    ids = acao.config.get("course_ids") or []
    if not ids:
        return "Nenhum treinamento configurado."

    cursos = Course.objects.filter(pk__in=ids, company_id=contexto["company"].pk)
    atribuidos = 0
    for curso in cursos:
        # `get_or_create`: reexecutar a automação não pode zerar o progresso
        # de quem já começou o treinamento.
        _, criado = CourseProgress.objects.get_or_create(
            user=colaborador, course=curso, defaults={"status": "not_started"}
        )
        if criado:
            atribuidos += 1

    if atribuidos:
        notify(
            colaborador,
            "Novo treinamento atribuído",
            f"{atribuidos} treinamento(s) foram adicionados à sua trilha.",
            category=Category.TRAINING,
            link="/courses",
        )
    return f"{atribuidos} treinamento(s) atribuídos."
