"""
Validação de tenant em campos de serializer.

O Módulo 38 da P2 é explícito: quando um recurso tem relacionamento, é
preciso validar o tenant de TODAS as FKs — não basta filtrar o queryset de
leitura. Sem isso, um RH consegue gravar no próprio registro uma FK
apontando para usuário/setor de outra empresa, e o nome dessa pessoa passa
a aparecer na tela — um vazamento de dado pessoal entre tenants.

Reunido aqui para que cada módulo novo não reimplemente (e esqueça) a
mesma regra.
"""

from rest_framework import serializers


def company_of(obj):
    """
    Empresa à qual um objeto pertence, direta ou indiretamente.

    Cobre os dois formatos usados no projeto: modelos com `company_id`
    próprio (User, Sector, Course…) e modelos que herdam o tenant via
    setor (Position).
    """
    if obj is None:
        return None
    if hasattr(obj, "company_id"):
        return obj.company_id
    sector = getattr(obj, "sector", None)
    return getattr(sector, "company_id", None)


def assert_same_company(obj, user, label: str):
    """
    Levanta ValidationError se `obj` não pertencer à empresa de `user`.

    Devolve o próprio objeto para encadear dentro de um `validate_<campo>`.
    """
    if obj is None:
        return obj
    if company_of(obj) != user.company_id:
        raise serializers.ValidationError(f"{label} não pertence à sua empresa.")
    return obj


def assert_all_same_company(objs, user, label: str):
    """Versão para campos ManyToMany."""
    for obj in objs or []:
        assert_same_company(obj, user, label)
    return objs


class TenantValidatedSerializerMixin:
    """
    Mixin com o acesso ao usuário autenticado, para os `validate_<campo>`.

    Quando não há request no contexto (uso interno, shell, testes de
    unidade), a validação é pulada — não há tenant contra o que comparar.
    """

    @property
    def _actor(self):
        request = self.context.get("request")
        return getattr(request, "user", None) if request else None

    def _check(self, obj, label):
        actor = self._actor
        if actor is None or not getattr(actor, "company_id", None):
            return obj
        return assert_same_company(obj, actor, label)

    def _check_many(self, objs, label):
        actor = self._actor
        if actor is None or not getattr(actor, "company_id", None):
            return objs
        return assert_all_same_company(objs, actor, label)
