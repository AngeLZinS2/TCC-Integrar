"""
Controle de acesso baseado em papéis (RBAC).

Duas peças:

  1. CATÁLOGO — todas as permissões que existem no sistema, no formato
     `recurso.ação`. É a lista canônica: se não está aqui, não existe.

  2. REGISTRY — o mapa papel → conjunto de permissões.

Por que um registry em Python e não tabelas Role/Permission no banco:
nenhuma empresa pode customizar papéis nesta fase, então tabelas seriam
complexidade sem uso — e custariam uma query a cada requisição. A troca
para papéis configuráveis no banco depois é trocar o corpo de
`permissions_for_role()`, mantendo `user.has_perm_code()` intacto: nenhuma
view, serializer ou teste precisa mudar.

O escopo (QUAIS registros o papel alcança) NÃO mora aqui — mora nos
querysets e em `apps/users/scopes.py`. Este módulo responde apenas "pode
executar esta ação?", nunca "sobre quais dados?".
"""

# ── Catálogo de permissões ───────────────────────────────────────────────────

EMPLOYEES_READ = "employees.read"
EMPLOYEES_CREATE = "employees.create"
EMPLOYEES_UPDATE = "employees.update"
EMPLOYEES_ACTIVATE = "employees.activate"
EMPLOYEES_DEACTIVATE = "employees.deactivate"

DEPARTMENTS_READ = "departments.read"
DEPARTMENTS_CREATE = "departments.create"
DEPARTMENTS_UPDATE = "departments.update"
DEPARTMENTS_DELETE = "departments.delete"

POSITIONS_READ = "positions.read"
POSITIONS_CREATE = "positions.create"
POSITIONS_UPDATE = "positions.update"
POSITIONS_DELETE = "positions.delete"

TRAINING_READ = "training.read"
TRAINING_CREATE = "training.create"
TRAINING_UPDATE = "training.update"
TRAINING_DELETE = "training.delete"

MATERIALS_READ = "materials.read"
MATERIALS_CREATE = "materials.create"
MATERIALS_UPDATE = "materials.update"
MATERIALS_DELETE = "materials.delete"

ONBOARDING_READ = "onboarding.read"
ONBOARDING_MANAGE = "onboarding.manage"

COMPANY_READ = "company.read"
COMPANY_UPDATE = "company.update"

DASHBOARD_READ = "dashboard.read"

# Integração com o banco de origem da empresa (P4). Fora do alcance do RH:
# um mapeamento errado não erra um registro — reescreve o cadastro inteiro
# na próxima sincronização. É decisão de estrutura, mesmo critério já
# aplicado a Unidades e Automações.
INTEGRATION_READ = "integration.read"
INTEGRATION_MANAGE = "integration.manage"
INTEGRATION_SYNC = "integration.sync"
INTEGRATION_CREDENTIALS = "integration.credentials"

AUDIT_READ = "audit.read"

# Permissões exclusivas do dono da plataforma — administram o SaaS, nunca
# os dados operacionais de uma empresa cliente.
PLATFORM_COMPANIES_READ = "platform.companies.read"
PLATFORM_COMPANIES_MANAGE = "platform.companies.manage"

ALL_PERMISSIONS = frozenset(
    {
        EMPLOYEES_READ, EMPLOYEES_CREATE, EMPLOYEES_UPDATE,
        EMPLOYEES_ACTIVATE, EMPLOYEES_DEACTIVATE,
        DEPARTMENTS_READ, DEPARTMENTS_CREATE, DEPARTMENTS_UPDATE, DEPARTMENTS_DELETE,
        POSITIONS_READ, POSITIONS_CREATE, POSITIONS_UPDATE, POSITIONS_DELETE,
        TRAINING_READ, TRAINING_CREATE, TRAINING_UPDATE, TRAINING_DELETE,
        MATERIALS_READ, MATERIALS_CREATE, MATERIALS_UPDATE, MATERIALS_DELETE,
        ONBOARDING_READ, ONBOARDING_MANAGE,
        COMPANY_READ, COMPANY_UPDATE,
        DASHBOARD_READ,
        AUDIT_READ,
        INTEGRATION_READ, INTEGRATION_MANAGE,
        INTEGRATION_SYNC, INTEGRATION_CREDENTIALS,
        PLATFORM_COMPANIES_READ, PLATFORM_COMPANIES_MANAGE,
    }
)


# ── Papéis ───────────────────────────────────────────────────────────────────

ROLE_OWNER = "owner"
ROLE_COMPANY_ADMIN = "company_admin"
ROLE_RH_ADMIN = "rh_admin"
ROLE_GESTOR = "gestor"
ROLE_COLABORADOR = "colaborador"

# Papéis que administram a empresa e enxergam todos os colaboradores dela.
COMPANY_MANAGEMENT_ROLES = frozenset({ROLE_COMPANY_ADMIN, ROLE_RH_ADMIN})


# ── Registry: papel → permissões ─────────────────────────────────────────────

# Base comum a todo mundo dentro de uma empresa.
#
# Inclui leitura da estrutura organizacional: qualquer colaborador precisa
# enxergar setores e cargos para o diretório, o próprio perfil e os filtros
# de treinamento funcionarem. Ler a estrutura da própria empresa é baseline;
# alterá-la é que exige permissão.
_TENANT_BASE = {
    DEPARTMENTS_READ,
    POSITIONS_READ,
    TRAINING_READ,
    MATERIALS_READ,
    ONBOARDING_READ,
    COMPANY_READ,
}

# O que o RH faz no dia a dia de pessoas.
_RH_PERMISSIONS = _TENANT_BASE | {
    EMPLOYEES_READ, EMPLOYEES_CREATE, EMPLOYEES_UPDATE,
    EMPLOYEES_ACTIVATE, EMPLOYEES_DEACTIVATE,
    DEPARTMENTS_READ, DEPARTMENTS_CREATE, DEPARTMENTS_UPDATE, DEPARTMENTS_DELETE,
    POSITIONS_READ, POSITIONS_CREATE, POSITIONS_UPDATE, POSITIONS_DELETE,
    TRAINING_CREATE, TRAINING_UPDATE, TRAINING_DELETE,
    MATERIALS_CREATE, MATERIALS_UPDATE, MATERIALS_DELETE,
    ONBOARDING_MANAGE,
    DASHBOARD_READ,
}

ROLE_PERMISSIONS = {
    # Dono da plataforma: administra tenants e métricas agregadas.
    # Não recebe NENHUMA permissão sobre dados operacionais de empresa —
    # é o que impede acesso a dados pessoais de colaboradores.
    ROLE_OWNER: frozenset({PLATFORM_COMPANIES_READ, PLATFORM_COMPANIES_MANAGE}),

    # Admin da empresa: tudo que o RH faz + configurar a empresa + auditoria.
    ROLE_COMPANY_ADMIN: frozenset(
        _RH_PERMISSIONS
        | {COMPANY_UPDATE, AUDIT_READ}
        # A integração é exclusiva do admin da empresa: a seção 2 da P4 a
        # lista como responsabilidade dele, e não do RH.
        | {
            INTEGRATION_READ, INTEGRATION_MANAGE,
            INTEGRATION_SYNC, INTEGRATION_CREDENTIALS,
        }
    ),

    ROLE_RH_ADMIN: frozenset(_RH_PERMISSIONS),

    # Gestor: enxerga e acompanha a própria equipe, e publica conteúdo do
    # setor que gerencia. Não cadastra nem desativa ninguém — isso é do RH.
    ROLE_GESTOR: frozenset(
        _TENANT_BASE | {
            EMPLOYEES_READ,
            DEPARTMENTS_READ,
            POSITIONS_READ,
            TRAINING_CREATE, TRAINING_UPDATE,
            MATERIALS_CREATE, MATERIALS_UPDATE,
            DASHBOARD_READ,
        }
    ),

    ROLE_COLABORADOR: frozenset(_TENANT_BASE),
}


def permissions_for_role(role: str) -> frozenset:
    """
    Permissões de um papel. Papel desconhecido não recebe nada — falha
    fechada, nunca aberta.

    Ponto de troca para papéis configuráveis por tenant: basta esta função
    passar a consultar o banco.
    """
    return ROLE_PERMISSIONS.get(role, frozenset())


def role_has_permission(role: str, permission: str) -> bool:
    return permission in permissions_for_role(role)
