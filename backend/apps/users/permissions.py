"""
Permission classes do DRF.

Todas derivam do catálogo em `rbac.py` — nenhuma checa `role ==` direto.
Trocar o que um papel pode fazer é editar o registry, não caçar `if` pelas
views.

As classes antigas (IsRHAdmin, CanManageCourses, …) continuam existindo com
o mesmo nome e o mesmo comportamento externo: elas passaram a ser apelidos
legíveis por cima do catálogo. Isso evita reescrever todas as views de uma
vez e mantém os testes existentes válidos.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from . import rbac


class HasPermission(BasePermission):
    """
    Base parametrizada por código de permissão.

    Use via `HasPermission.require("employees.create")`, que devolve uma
    classe pronta para `permission_classes`.
    """

    permission_code: str | None = None
    message = "Você não tem permissão para executar esta ação."

    @classmethod
    def require(cls, permission_code: str, message: str | None = None):
        assert permission_code in rbac.ALL_PERMISSIONS, (
            f"Permissão desconhecida: {permission_code}. "
            "Toda permissão precisa estar no catálogo de rbac.py."
        )
        attrs = {"permission_code": permission_code}
        if message:
            attrs["message"] = message
        return type(f"Has_{permission_code.replace('.', '_')}", (cls,), attrs)

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.has_perm_code(self.permission_code)


class ReadWritePermission(BasePermission):
    """
    Leitura e escrita com códigos diferentes.

    Cobre o padrão mais comum do sistema: qualquer autenticado da empresa
    lê, mas só quem tem a permissão de escrita altera.
    """

    read_code: str | None = None
    write_code: str | None = None
    message = "Você não tem permissão para executar esta ação."

    @classmethod
    def require(cls, read_code: str, write_code: str, message: str | None = None):
        assert read_code in rbac.ALL_PERMISSIONS, f"Permissão desconhecida: {read_code}"
        assert write_code in rbac.ALL_PERMISSIONS, f"Permissão desconhecida: {write_code}"
        attrs = {"read_code": read_code, "write_code": write_code}
        if message:
            attrs["message"] = message
        return type(f"RW_{write_code.replace('.', '_')}", (cls,), attrs)

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        code = self.read_code if request.method in SAFE_METHODS else self.write_code
        return user.has_perm_code(code)


# ── Apelidos por papel (compatibilidade com as views existentes) ─────────────

class IsRHAdmin(BasePermission):
    """
    Acesso restrito a quem administra pessoas na empresa.

    Passou a aceitar company_admin além de rh_admin: o admin da empresa é
    hierarquicamente superior ao RH e faz tudo que ele faz.
    """

    message = "Acesso restrito ao RH."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.manages_company)


class IsColaborador(BasePermission):
    """Permite acesso apenas a usuários com papel 'colaborador'."""

    message = "Acesso restrito a colaboradores."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.role == rbac.ROLE_COLABORADOR)


class IsOwner(BasePermission):
    """
    Acesso restrito ao dono da plataforma.

    Ancorado na permissão de plataforma, que nenhum papel de empresa possui —
    é o que garante que o Owner não vire um "RH global".
    """

    message = "Acesso restrito ao dono do sistema."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.has_perm_code(rbac.PLATFORM_COMPANIES_MANAGE)
        )


class IsRHAdminOrReadOnly(BasePermission):
    """Leitura para qualquer autenticado; escrita para quem administra a empresa."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.manages_company


class _SectorScopedWritePermission(BasePermission):
    """
    Base das permissões de conteúdo com escopo de setor.

    Leitura livre para autenticados. Escrita para quem tem a permissão de
    criação; e quem não administra a empresa inteira fica preso ao próprio
    setor — checado no objeto e reforçado no `validate()` do serializer.
    """

    create_code: str = ""

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.has_perm_code(self.create_code)

    def _sector_of(self, obj):
        raise NotImplementedError

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if user.manages_company:
            return True
        if not user.has_perm_code(self.create_code):
            return False
        sector_id = self._sector_of(obj)
        return sector_id is not None and sector_id == user.sector_id


class CanManageCourses(_SectorScopedWritePermission):
    """
    Leitura livre para qualquer autenticado. Escrita para RH/admin (qualquer
    treinamento da empresa) ou gestor/líder de setor (só do próprio setor).
    """

    message = "Apenas RH admin ou líder do setor podem gerenciar treinamentos."
    create_code = rbac.TRAINING_CREATE

    def _sector_of(self, obj):
        # Aceita tanto Course (tem sector_id) quanto Content (tem course).
        course = obj if hasattr(obj, "sector_id") else obj.course
        return course.sector_id


class CanManageMaterials(_SectorScopedWritePermission):
    """
    Leitura livre para qualquer autenticado. Escrita para RH/admin (qualquer
    material da empresa) ou gestor/líder de setor (só do próprio setor).
    """

    message = "Apenas RH admin ou líder do setor podem gerenciar materiais."
    create_code = rbac.MATERIALS_CREATE

    def _sector_of(self, obj):
        return obj.sector_id
