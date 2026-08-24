from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from . import rbac
from .managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    User model customizado do projeto.

    Campo de autenticação: email (não username).
    Papéis: colaborador (padrão) | rh_admin | owner.
    Setor e cargo são opcionais no cadastro inicial e atribuídos pelo RH.

    O papel "owner" é o dono do sistema (multi-tenant): não pertence a
    nenhuma empresa (company=None é válido só para este papel) e administra
    o cadastro de empresas clientes. colaborador/rh_admin sempre têm company
    preenchido.
    """

    ROLE_CHOICES = [
        ("colaborador", "Colaborador"),
        ("gestor", "Gestor"),
        ("rh_admin", "RH Admin"),
        ("company_admin", "Administrador da Empresa"),
        ("owner", "Dono do Sistema"),
    ]

    # Papéis que um administrador de empresa pode atribuir dentro do próprio
    # tenant. "owner" nunca aparece aqui: é da plataforma, não da empresa.
    ASSIGNABLE_ROLES = ["colaborador", "gestor", "rh_admin", "company_admin"]

    email = models.EmailField(
        unique=True,
        verbose_name="E-mail",
    )
    full_name = models.CharField(
        max_length=150,
        verbose_name="Nome completo",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="colaborador",
        verbose_name="Papel",
        db_index=True,
    )
    # FK com string para evitar import circular — companies ainda não está importado
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Empresa",
        help_text="Obrigatório para colaborador/rh_admin. Vazio apenas para o dono do sistema.",
    )
    # FKs com string para evitar import circular — sectors ainda não está importado
    sector = models.ForeignKey(
        "sectors.Sector",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Setor",
    )
    position = models.ForeignKey(
        "sectors.Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Cargo",
    )
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
        verbose_name="Gestor direto",
        help_text="Gestor responsável por este colaborador. Deve ser da mesma empresa.",
    )
    unit = models.ForeignKey(
        "units.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        verbose_name="Unidade",
        help_text="Filial onde o colaborador trabalha. Vazio = sem unidade definida.",
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Telefone",
    )
    registration_number = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Matrícula",
        help_text="Identificação interna do colaborador. Única dentro da empresa.",
    )
    avatar_url = models.URLField(
        blank=True,
        verbose_name="Foto",
        help_text="URL da foto de perfil. Upload de arquivo fica para uma fase posterior.",
    )
    hire_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de contratação",
        help_text="Usada para calcular prazos reais de integração (checklist/cursos). Vazio para o dono do sistema.",
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de nascimento",
        help_text="Usada para o painel de aniversariantes.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_sector_leader = models.BooleanField(
        default=False,
        verbose_name="Líder do Setor",
        help_text="Colaborador que pode cadastrar treinamentos do próprio setor. Exige setor definido.",
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["full_name"]
        constraints = [
            # Matrícula é única dentro da empresa, não globalmente — duas
            # empresas podem ter a matrícula "001" sem conflito.
            models.UniqueConstraint(
                fields=["company", "registration_number"],
                condition=~models.Q(registration_number=""),
                name="unique_registration_per_company",
            )
        ]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    # ── Atalhos de papel ────────────────────────────────────────────────────

    @property
    def is_rh_admin(self) -> bool:
        """Atalho para checar papel RH admin nas views/permissões."""
        return self.role == "rh_admin"

    @property
    def is_company_admin(self) -> bool:
        return self.role == "company_admin"

    @property
    def is_gestor(self) -> bool:
        return self.role == "gestor"

    @property
    def is_owner(self) -> bool:
        """Atalho para checar papel de dono do sistema nas views/permissões."""
        return self.role == "owner"

    @property
    def manages_company(self) -> bool:
        """
        True para quem administra a empresa inteira (company_admin ou RH).
        É o corte usado nos querysets que devem enxergar todos os
        colaboradores do tenant, em oposição ao escopo restrito do gestor.
        """
        return self.role in rbac.COMPANY_MANAGEMENT_ROLES

    # ── Permissões ──────────────────────────────────────────────────────────

    def get_permissions(self) -> frozenset:
        """
        Permissões efetivas: as do papel, mais as concedidas pela flag de
        líder de setor.

        A flag existe desde antes dos papéis e continua valendo: ela permite
        que um colaborador comum publique conteúdo do próprio setor sem
        precisar virar gestor.
        """
        permissions = set(rbac.permissions_for_role(self.role))
        if self.is_sector_leader:
            permissions |= {
                rbac.TRAINING_CREATE,
                rbac.TRAINING_UPDATE,
                rbac.MATERIALS_CREATE,
                rbac.MATERIALS_UPDATE,
            }
        return frozenset(permissions)

    def has_perm_code(self, permission: str) -> bool:
        """
        Responde apenas "pode executar esta ação?".

        O escopo — sobre QUAIS registros — é decidido pelos querysets e por
        apps/users/scopes.py, nunca por este método.
        """
        return permission in self.get_permissions()

    @property
    def can_manage_courses(self) -> bool:
        """Mantido por compatibilidade — agora derivado do catálogo RBAC."""
        return self.has_perm_code(rbac.TRAINING_CREATE)
