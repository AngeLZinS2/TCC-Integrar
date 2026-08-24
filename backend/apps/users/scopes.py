"""
Escopo de dados por papel.

O RBAC (`rbac.py`) responde "pode executar esta ação?". Este módulo
responde a outra pergunta, independente: "sobre QUAIS registros?".

Separar as duas evita o erro clássico de dar `employees.read` ao gestor e
ele passar a enxergar a empresa inteira. Ele tem a permissão de leitura —
o que muda é o conjunto de pessoas que a permissão alcança.
"""

from django.db.models import Q


def managed_users_filter(user) -> Q:
    """
    Filtro dos colaboradores sob responsabilidade de um gestor.

    A equipe de um gestor é a união de dois caminhos, porque a empresa pode
    modelar a hierarquia de qualquer um deles:
      - quem tem este gestor como `manager` (subordinação direta);
      - quem está em um setor que este gestor administra (`Sector.manager`).
    """
    return Q(manager_id=user.id) | Q(sector__manager_id=user.id)


def visible_colaboradores(user, queryset):
    """
    Restringe um queryset de User ao que `user` pode enxergar.

    Regras, do mais amplo para o mais restrito:
      - owner: nada. Administra tenants, não pessoas (ver P0-01).
      - company_admin / rh_admin: todos os colaboradores da própria empresa.
      - gestor: apenas a própria equipe.
      - colaborador: apenas o próprio registro.
    """
    if not user.is_authenticated or user.is_owner or not user.company_id:
        return queryset.none()

    queryset = queryset.filter(company_id=user.company_id)

    if user.manages_company:
        return queryset

    if user.is_gestor:
        return queryset.filter(managed_users_filter(user))

    return queryset.filter(pk=user.pk)


def can_view_colaborador(actor, target) -> bool:
    """Versão pontual de `visible_colaboradores`, para checagem de objeto."""
    if not actor.is_authenticated or actor.is_owner or not actor.company_id:
        return False
    if actor.company_id != target.company_id:
        return False
    if actor.manages_company:
        return True
    if actor.is_gestor:
        return (
            target.manager_id == actor.id
            or (target.sector_id is not None and target.sector.manager_id == actor.id)
        )
    return actor.pk == target.pk
