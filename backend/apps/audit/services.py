"""
Escrita de registros de auditoria.

Um helper único para que as views não repitam a montagem do registro — e
para que a regra "nunca gravar valor sensível" fique num lugar só.
"""

import logging

from .models import AuditLog

logger = logging.getLogger(__name__)

# Campos cujo NOME pode ser registrado, mas cujo VALOR nunca entra no log.
SENSITIVE_FIELDS = frozenset({"password", "password_confirm", "token", "refresh", "access"})


def record(
    actor,
    action: str,
    resource_type: str,
    *,
    resource_id=None,
    resource_label: str = "",
    company=None,
    metadata: dict | None = None,
):
    """
    Registra uma ação administrativa.

    Nunca levanta exceção: auditoria com defeito não pode derrubar a
    operação que o usuário pediu. Falha é logada e seguimos adiante.

    A empresa vem do `actor` quando não informada — nunca do cliente.
    """
    try:
        resolved_company = company
        if resolved_company is None and actor is not None:
            resolved_company = getattr(actor, "company", None)

        return AuditLog.objects.create(
            company=resolved_company,
            actor=actor if (actor is not None and actor.pk) else None,
            actor_name=getattr(actor, "full_name", "") or "",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_label=(resource_label or "")[:200],
            metadata=_sanitize(metadata or {}),
        )
    except Exception:
        logger.exception("Falha ao gravar registro de auditoria.")
        return None


def _sanitize(metadata: dict) -> dict:
    """Remove qualquer valor sensível, preservando o nome do campo."""
    clean = {}
    for key, value in metadata.items():
        if key in SENSITIVE_FIELDS:
            continue
        if key == "changed_fields" and isinstance(value, (list, tuple, set)):
            clean[key] = sorted(f for f in value if f not in SENSITIVE_FIELDS)
        else:
            clean[key] = value
    return clean


def changed_field_names(validated_data: dict) -> list:
    """Nomes dos campos tocados numa edição, sem os valores."""
    return sorted(k for k in validated_data.keys() if k not in SENSITIVE_FIELDS)
