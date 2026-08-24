"""
Testes da Fase P1 — RBAC, papéis novos e escopo de dados.

Cenário multi-tenant completo, exigido pela seção 26 do P1.MD:

    Empresa A: admin_a, rh_a, gestor_a, colab_a
    Empresa B: admin_b, rh_b, gestor_b, colab_b

Cada combinação de papel × empresa é exercitada contra os endpoints novos.
"""

import pytest

from apps.companies.models import Company
from apps.sectors.models import Position, Sector
from apps.users import rbac

EMPLOYEES_URL = "/api/v1/employees/"
SECTORS_URL = "/api/v1/sectors/"
POSITIONS_URL = "/api/v1/sectors/positions/"
ME_URL = "/api/v1/auth/me/"


# ── Cenário de duas empresas ─────────────────────────────────────────────────

@pytest.fixture
def empresa_a(db):
    return Company.objects.create(name="Empresa A")


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa B")


def _user(django_user_model, email, role, company, **extra):
    return django_user_model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **extra
    )


@pytest.fixture
def setor_ti_a(db, empresa_a):
    return Sector.objects.create(name="TI", company=empresa_a)


@pytest.fixture
def setor_rh_a(db, empresa_a):
    return Sector.objects.create(name="RH", company=empresa_a)


@pytest.fixture
def setor_ops_b(db, empresa_b):
    return Sector.objects.create(name="Operações", company=empresa_b)


@pytest.fixture
def gestor_a(db, django_user_model, empresa_a, setor_ti_a):
    gestor = _user(django_user_model, "gestor-a@x.com", "gestor", empresa_a, sector=setor_ti_a)
    setor_ti_a.manager = gestor
    setor_ti_a.save()
    return gestor


@pytest.fixture
def admin_a(db, django_user_model, empresa_a):
    return _user(django_user_model, "admin-a@x.com", "company_admin", empresa_a)


@pytest.fixture
def rh_a(db, django_user_model, empresa_a):
    return _user(django_user_model, "rh-a@x.com", "rh_admin", empresa_a)


@pytest.fixture
def colab_ti_a(db, django_user_model, empresa_a, setor_ti_a):
    """Colaborador do setor que gestor_a administra — está na equipe dele."""
    return _user(django_user_model, "colab-ti-a@x.com", "colaborador", empresa_a, sector=setor_ti_a)


@pytest.fixture
def colab_rh_a(db, django_user_model, empresa_a, setor_rh_a):
    """Colaborador de OUTRO setor — fora do escopo do gestor_a."""
    return _user(django_user_model, "colab-rh-a@x.com", "colaborador", empresa_a, sector=setor_rh_a)


@pytest.fixture
def admin_b(db, django_user_model, empresa_b):
    return _user(django_user_model, "admin-b@x.com", "company_admin", empresa_b)


@pytest.fixture
def rh_b(db, django_user_model, empresa_b):
    return _user(django_user_model, "rh-b@x.com", "rh_admin", empresa_b)


@pytest.fixture
def colab_b(db, django_user_model, empresa_b, setor_ops_b):
    return _user(django_user_model, "colab-b@x.com", "colaborador", empresa_b, sector=setor_ops_b)


def as_user(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


# ══════════════════════════════════════════════════════════════════════════
# Catálogo RBAC
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCatalogoRBAC:
    def test_owner_nao_tem_nenhuma_permissao_operacional(self, owner_user):
        """
        O que impede o Owner de virar "RH global": ele não possui nenhuma
        permissão sobre dados de empresa, só sobre a plataforma.
        """
        permissoes = owner_user.get_permissions()
        assert rbac.EMPLOYEES_READ not in permissoes
        assert rbac.EMPLOYEES_CREATE not in permissoes
        assert rbac.DASHBOARD_READ not in permissoes
        assert rbac.PLATFORM_COMPANIES_MANAGE in permissoes

    def test_company_admin_faz_tudo_que_o_rh_faz(self, admin_a, rh_a):
        assert rh_a.get_permissions().issubset(admin_a.get_permissions())

    def test_company_admin_tem_permissoes_exclusivas(self, admin_a, rh_a):
        assert admin_a.has_perm_code(rbac.COMPANY_UPDATE)
        assert admin_a.has_perm_code(rbac.AUDIT_READ)
        assert not rh_a.has_perm_code(rbac.COMPANY_UPDATE)

    def test_gestor_le_mas_nao_cadastra_colaborador(self, gestor_a):
        assert gestor_a.has_perm_code(rbac.EMPLOYEES_READ)
        assert not gestor_a.has_perm_code(rbac.EMPLOYEES_CREATE)
        assert not gestor_a.has_perm_code(rbac.EMPLOYEES_DEACTIVATE)

    def test_colaborador_so_tem_a_base(self, colab_ti_a):
        assert colab_ti_a.has_perm_code(rbac.TRAINING_READ)
        assert colab_ti_a.has_perm_code(rbac.DEPARTMENTS_READ)
        assert not colab_ti_a.has_perm_code(rbac.EMPLOYEES_READ)
        assert not colab_ti_a.has_perm_code(rbac.TRAINING_CREATE)

    def test_flag_de_lider_concede_publicacao_sem_mudar_papel(self, colab_ti_a):
        """A flag antiga continua valendo — não foi substituída pelo papel."""
        assert not colab_ti_a.has_perm_code(rbac.TRAINING_CREATE)
        colab_ti_a.is_sector_leader = True
        assert colab_ti_a.has_perm_code(rbac.TRAINING_CREATE)
        assert colab_ti_a.has_perm_code(rbac.MATERIALS_CREATE)
        # Continua sem virar administrador de pessoas.
        assert not colab_ti_a.has_perm_code(rbac.EMPLOYEES_CREATE)

    def test_papel_desconhecido_nao_recebe_nada(self):
        """Falha fechada: papel fora do registry não ganha permissão alguma."""
        assert rbac.permissions_for_role("papel_inventado") == frozenset()


# ══════════════════════════════════════════════════════════════════════════
# Escopo do gestor
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestEscopoDoGestor:
    def test_gestor_ve_colaborador_do_setor_que_administra(
        self, api_client, gestor_a, colab_ti_a
    ):
        resp = as_user(api_client, gestor_a).get(EMPLOYEES_URL)
        assert resp.status_code == 200
        emails = [e["email"] for e in resp.data["results"]]
        assert colab_ti_a.email in emails

    def test_gestor_nao_ve_colaborador_de_outro_setor(
        self, api_client, gestor_a, colab_ti_a, colab_rh_a
    ):
        resp = as_user(api_client, gestor_a).get(EMPLOYEES_URL)
        emails = [e["email"] for e in resp.data["results"]]
        assert colab_rh_a.email not in emails

    def test_gestor_ve_subordinado_direto_de_outro_setor(
        self, api_client, gestor_a, colab_rh_a
    ):
        """A equipe é a união de setor gerido + subordinação direta."""
        colab_rh_a.manager = gestor_a
        colab_rh_a.save()
        resp = as_user(api_client, gestor_a).get(EMPLOYEES_URL)
        emails = [e["email"] for e in resp.data["results"]]
        assert colab_rh_a.email in emails

    def test_gestor_nao_acessa_colaborador_fora_do_escopo_por_id(
        self, api_client, gestor_a, colab_rh_a
    ):
        resp = as_user(api_client, gestor_a).get(f"{EMPLOYEES_URL}{colab_rh_a.id}/")
        assert resp.status_code == 404

    def test_gestor_nao_acessa_colaborador_de_outra_empresa(
        self, api_client, gestor_a, colab_b
    ):
        resp = as_user(api_client, gestor_a).get(f"{EMPLOYEES_URL}{colab_b.id}/")
        assert resp.status_code == 404

    def test_gestor_nao_cadastra_colaborador(self, api_client, gestor_a, setor_ti_a):
        resp = as_user(api_client, gestor_a).post(
            EMPLOYEES_URL,
            {"email": "novo@x.com", "full_name": "Novo", "role": "colaborador",
             "password": "senha@12345", "password_confirm": "senha@12345"},
            format="json",
        )
        assert resp.status_code == 403

    def test_gestor_nao_desativa_colaborador(self, api_client, gestor_a, colab_ti_a):
        resp = as_user(api_client, gestor_a).post(
            f"{EMPLOYEES_URL}{colab_ti_a.id}/toggle-active/"
        )
        assert resp.status_code == 403

    def test_colaborador_comum_so_enxerga_a_si_mesmo(
        self, api_client, colab_ti_a, colab_rh_a
    ):
        resp = as_user(api_client, colab_ti_a).get(EMPLOYEES_URL)
        assert resp.status_code == 403  # sem employees.read


# ══════════════════════════════════════════════════════════════════════════
# Isolamento multi-tenant nos endpoints novos
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIsolamentoNosEndpointsNovos:
    def test_admin_a_nao_ve_colaborador_da_empresa_b(self, api_client, admin_a, colab_b):
        resp = as_user(api_client, admin_a).get(EMPLOYEES_URL)
        emails = [e["email"] for e in resp.data["results"]]
        assert colab_b.email not in emails

    def test_admin_a_nao_acessa_colaborador_b_por_id(self, api_client, admin_a, colab_b):
        resp = as_user(api_client, admin_a).get(f"{EMPLOYEES_URL}{colab_b.id}/")
        assert resp.status_code == 404

    def test_admin_a_nao_edita_colaborador_b(self, api_client, admin_a, colab_b):
        resp = as_user(api_client, admin_a).patch(
            f"{EMPLOYEES_URL}{colab_b.id}/", {"full_name": "Invadido"}, format="json"
        )
        assert resp.status_code == 404

    def test_admin_a_nao_desativa_colaborador_b(self, api_client, admin_a, colab_b):
        resp = as_user(api_client, admin_a).post(f"{EMPLOYEES_URL}{colab_b.id}/toggle-active/")
        assert resp.status_code == 404

    def test_rh_a_nao_ve_setor_da_empresa_b(self, api_client, rh_a, setor_ops_b):
        resp = as_user(api_client, rh_a).get(SECTORS_URL)
        nomes = [s["name"] for s in resp.data["results"]]
        assert "Operações" not in nomes

    def test_rh_a_nao_edita_setor_da_empresa_b(self, api_client, rh_a, setor_ops_b):
        resp = as_user(api_client, rh_a).patch(
            f"{SECTORS_URL}{setor_ops_b.id}/", {"name": "Invadido"}, format="json"
        )
        assert resp.status_code == 404

    def test_rh_a_nao_atribui_gestor_da_empresa_b(
        self, api_client, rh_a, setor_ti_a, admin_b
    ):
        resp = as_user(api_client, rh_a).patch(
            f"{SECTORS_URL}{setor_ti_a.id}/", {"manager": admin_b.id}, format="json"
        )
        assert resp.status_code == 400

    def test_rh_a_nao_cadastra_colaborador_com_setor_da_empresa_b(
        self, api_client, rh_a, setor_ops_b
    ):
        resp = as_user(api_client, rh_a).post(
            EMPLOYEES_URL,
            {"email": "x@x.com", "full_name": "X", "role": "colaborador",
             "sector": setor_ops_b.id,
             "password": "senha@12345", "password_confirm": "senha@12345"},
            format="json",
        )
        assert resp.status_code == 400

    def test_rh_a_nao_define_gestor_da_empresa_b(self, api_client, rh_a, colab_ti_a, admin_b):
        resp = as_user(api_client, rh_a).patch(
            f"{EMPLOYEES_URL}{colab_ti_a.id}/", {"manager": admin_b.id}, format="json"
        )
        assert resp.status_code == 400

    def test_owner_nao_lista_colaboradores(self, api_client, owner_user, colab_ti_a):
        """P0-01 continua valendo depois dos endpoints novos da P1."""
        resp = as_user(api_client, owner_user).get(EMPLOYEES_URL)
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════
# CRUD de colaboradores
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCrudColaboradores:
    def test_rh_cadastra_colaborador_completo(
        self, api_client, rh_a, setor_ti_a, gestor_a
    ):
        cargo = Position.objects.create(name="Dev", sector=setor_ti_a)
        resp = as_user(api_client, rh_a).post(
            EMPLOYEES_URL,
            {
                "email": "novo@x.com", "full_name": "Novo Colaborador",
                "phone": "11999999999", "registration_number": "M-001",
                "role": "colaborador", "sector": setor_ti_a.id,
                "position": cargo.id, "manager": gestor_a.id,
                "hire_date": "2026-01-15",
                "password": "senha@12345", "password_confirm": "senha@12345",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.data

    def test_colaborador_criado_consegue_logar(self, api_client, rh_a):
        as_user(api_client, rh_a).post(
            EMPLOYEES_URL,
            {"email": "logavel@x.com", "full_name": "Logavel", "role": "colaborador",
             "password": "senha@12345", "password_confirm": "senha@12345"},
            format="json",
        )
        api_client.force_authenticate(user=None)
        resp = api_client.post(
            "/api/v1/auth/token/",
            {"email": "logavel@x.com", "password": "senha@12345"},
            format="json",
        )
        assert resp.status_code == 200

    def test_rh_edita_colaborador(self, api_client, rh_a, colab_ti_a):
        resp = as_user(api_client, rh_a).patch(
            f"{EMPLOYEES_URL}{colab_ti_a.id}/",
            {"full_name": "Nome Corrigido", "phone": "11988887777"},
            format="json",
        )
        assert resp.status_code == 200
        colab_ti_a.refresh_from_db()
        assert colab_ti_a.full_name == "Nome Corrigido"
        assert colab_ti_a.phone == "11988887777"

    def test_rh_altera_papel_do_colaborador(self, api_client, rh_a, colab_ti_a):
        resp = as_user(api_client, rh_a).patch(
            f"{EMPLOYEES_URL}{colab_ti_a.id}/", {"role": "gestor"}, format="json"
        )
        assert resp.status_code == 200
        colab_ti_a.refresh_from_db()
        assert colab_ti_a.role == "gestor"

    def test_nao_e_possivel_atribuir_papel_de_owner(self, api_client, rh_a, colab_ti_a):
        """Owner é papel de plataforma — nenhuma empresa pode concedê-lo."""
        resp = as_user(api_client, rh_a).patch(
            f"{EMPLOYEES_URL}{colab_ti_a.id}/", {"role": "owner"}, format="json"
        )
        assert resp.status_code == 400
        colab_ti_a.refresh_from_db()
        assert colab_ti_a.role == "colaborador"

    def test_cargo_precisa_pertencer_ao_setor_escolhido(
        self, api_client, rh_a, setor_ti_a, setor_rh_a, colab_ti_a
    ):
        cargo_do_rh = Position.objects.create(name="Analista RH", sector=setor_rh_a)
        resp = as_user(api_client, rh_a).patch(
            f"{EMPLOYEES_URL}{colab_ti_a.id}/",
            {"sector": setor_ti_a.id, "position": cargo_do_rh.id},
            format="json",
        )
        assert resp.status_code == 400

    def test_matricula_duplicada_na_mesma_empresa_e_rejeitada(
        self, api_client, rh_a, colab_ti_a, colab_rh_a
    ):
        colab_ti_a.registration_number = "M-100"
        colab_ti_a.save()
        resp = as_user(api_client, rh_a).patch(
            f"{EMPLOYEES_URL}{colab_rh_a.id}/", {"registration_number": "M-100"}, format="json"
        )
        assert resp.status_code == 400

    def test_mesma_matricula_em_empresas_diferentes_e_permitida(
        self, api_client, rh_a, rh_b, colab_ti_a, colab_b
    ):
        as_user(api_client, rh_a).patch(
            f"{EMPLOYEES_URL}{colab_ti_a.id}/", {"registration_number": "M-777"}, format="json"
        )
        resp = as_user(api_client, rh_b).patch(
            f"{EMPLOYEES_URL}{colab_b.id}/", {"registration_number": "M-777"}, format="json"
        )
        assert resp.status_code == 200

    def test_colaborador_nao_pode_ser_gestor_de_si_mesmo(self, api_client, rh_a, colab_ti_a):
        resp = as_user(api_client, rh_a).patch(
            f"{EMPLOYEES_URL}{colab_ti_a.id}/", {"manager": colab_ti_a.id}, format="json"
        )
        assert resp.status_code == 400

    def test_desativar_preserva_o_registro(self, api_client, rh_a, colab_ti_a):
        resp = as_user(api_client, rh_a).post(f"{EMPLOYEES_URL}{colab_ti_a.id}/toggle-active/")
        assert resp.status_code == 200
        colab_ti_a.refresh_from_db()
        assert colab_ti_a.is_active is False
        assert colab_ti_a.pk is not None  # nunca exclusão física

    def test_reativar_restaura_acesso(self, api_client, rh_a, colab_ti_a):
        colab_ti_a.is_active = False
        colab_ti_a.save()
        as_user(api_client, rh_a).post(f"{EMPLOYEES_URL}{colab_ti_a.id}/toggle-active/")
        colab_ti_a.refresh_from_db()
        assert colab_ti_a.is_active is True

    def test_nao_desativa_o_ultimo_administrador(self, api_client, admin_a):
        """admin_a está sozinho — não pode se desativar."""
        resp = as_user(api_client, admin_a).post(f"{EMPLOYEES_URL}{admin_a.id}/toggle-active/")
        assert resp.status_code == 400
        assert "último administrador" in str(resp.data)

    def test_desativa_administrador_quando_existe_outro(self, api_client, admin_a, rh_a):
        """Com rh_a ativo, admin_a pode ser desativado — a empresa não fica órfã."""
        resp = as_user(api_client, admin_a).post(f"{EMPLOYEES_URL}{rh_a.id}/toggle-active/")
        assert resp.status_code == 200

    def test_delete_nao_e_permitido(self, api_client, rh_a, colab_ti_a):
        """Desligamento é desativação, nunca exclusão física."""
        resp = as_user(api_client, rh_a).delete(f"{EMPLOYEES_URL}{colab_ti_a.id}/")
        assert resp.status_code == 405


# ══════════════════════════════════════════════════════════════════════════
# Perfil próprio
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPerfilProprio:
    def test_colaborador_edita_campos_permitidos(self, api_client, colab_ti_a):
        resp = as_user(api_client, colab_ti_a).patch(
            ME_URL,
            {"full_name": "Novo Nome", "phone": "11955554444",
             "avatar_url": "https://example.com/foto.png"},
            format="json",
        )
        assert resp.status_code == 200
        colab_ti_a.refresh_from_db()
        assert colab_ti_a.full_name == "Novo Nome"
        assert colab_ti_a.phone == "11955554444"

    @pytest.mark.parametrize(
        "campo,valor",
        [
            ("role", "rh_admin"),
            ("registration_number", "HACK-1"),
            ("hire_date", "2020-01-01"),
            ("is_active", False),
            ("is_sector_leader", True),
        ],
    )
    def test_colaborador_nao_altera_campo_administrado_pelo_rh(
        self, api_client, colab_ti_a, campo, valor
    ):
        antes = getattr(colab_ti_a, campo)
        resp = as_user(api_client, colab_ti_a).patch(ME_URL, {campo: valor}, format="json")
        assert resp.status_code == 200
        colab_ti_a.refresh_from_db()
        assert getattr(colab_ti_a, campo) == antes

    def test_colaborador_nao_altera_setor_cargo_nem_empresa(
        self, api_client, colab_ti_a, setor_rh_a, empresa_b
    ):
        antes = (colab_ti_a.sector_id, colab_ti_a.position_id, colab_ti_a.company_id)
        resp = as_user(api_client, colab_ti_a).patch(
            ME_URL,
            {"sector": setor_rh_a.id, "position": 999, "company": empresa_b.id},
            format="json",
        )
        assert resp.status_code == 200
        colab_ti_a.refresh_from_db()
        assert (colab_ti_a.sector_id, colab_ti_a.position_id, colab_ti_a.company_id) == antes

    def test_perfil_expoe_permissoes_para_montar_a_navegacao(self, api_client, rh_a):
        resp = as_user(api_client, rh_a).get(ME_URL)
        assert resp.status_code == 200
        assert rbac.EMPLOYEES_READ in resp.data["permissions"]
        assert rbac.PLATFORM_COMPANIES_MANAGE not in resp.data["permissions"]


# ══════════════════════════════════════════════════════════════════════════
# Setores e cargos
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSetoresECargos:
    def test_rh_cria_setor_com_gestor(self, api_client, rh_a, gestor_a):
        resp = as_user(api_client, rh_a).post(
            SECTORS_URL,
            {"name": "Financeiro", "description": "Contas", "manager": gestor_a.id},
            format="json",
        )
        assert resp.status_code == 201, resp.data
        assert resp.data["manager_name"] == gestor_a.full_name

    def test_nome_de_setor_duplicado_na_empresa_e_rejeitado(
        self, api_client, rh_a, setor_ti_a
    ):
        resp = as_user(api_client, rh_a).post(SECTORS_URL, {"name": "TI"}, format="json")
        assert resp.status_code == 400

    def test_mesmo_nome_de_setor_em_empresas_diferentes_e_permitido(
        self, api_client, rh_b, setor_ti_a
    ):
        resp = as_user(api_client, rh_b).post(SECTORS_URL, {"name": "TI"}, format="json")
        assert resp.status_code == 201

    def test_listagem_traz_contagem_de_colaboradores(
        self, api_client, rh_a, setor_ti_a, colab_ti_a
    ):
        resp = as_user(api_client, rh_a).get(SECTORS_URL)
        setor = next(s for s in resp.data["results"] if s["id"] == setor_ti_a.id)
        # colab_ti_a e gestor_a não; apenas quem está lotado no setor.
        assert setor["collaborators_count"] >= 1

    def test_colaborador_le_setores_mas_nao_cria(self, api_client, colab_ti_a):
        cliente = as_user(api_client, colab_ti_a)
        assert cliente.get(SECTORS_URL).status_code == 200
        assert cliente.post(SECTORS_URL, {"name": "Novo"}, format="json").status_code == 403

    def test_nao_exclui_setor_com_colaboradores(self, api_client, rh_a, setor_ti_a, colab_ti_a):
        resp = as_user(api_client, rh_a).delete(f"{SECTORS_URL}{setor_ti_a.id}/")
        assert resp.status_code == 400

    def test_exclui_setor_vazio(self, api_client, rh_a, empresa_a):
        vazio = Sector.objects.create(name="Vazio", company=empresa_a)
        resp = as_user(api_client, rh_a).delete(f"{SECTORS_URL}{vazio.id}/")
        assert resp.status_code == 204

    def test_rh_cria_cargo(self, api_client, rh_a, setor_ti_a):
        resp = as_user(api_client, rh_a).post(
            POSITIONS_URL,
            {"name": "Desenvolvedor", "sector": setor_ti_a.id, "description": "Dev"},
            format="json",
        )
        assert resp.status_code == 201, resp.data

    def test_cargo_duplicado_no_mesmo_setor_e_rejeitado(self, api_client, rh_a, setor_ti_a):
        Position.objects.create(name="Dev", sector=setor_ti_a)
        resp = as_user(api_client, rh_a).post(
            POSITIONS_URL, {"name": "Dev", "sector": setor_ti_a.id}, format="json"
        )
        assert resp.status_code == 400

    def test_cargo_com_setor_de_outra_empresa_e_rejeitado(
        self, api_client, rh_a, setor_ops_b
    ):
        resp = as_user(api_client, rh_a).post(
            POSITIONS_URL, {"name": "X", "sector": setor_ops_b.id}, format="json"
        )
        assert resp.status_code == 400

    def test_nao_exclui_cargo_com_colaboradores(
        self, api_client, rh_a, setor_ti_a, colab_ti_a
    ):
        cargo = Position.objects.create(name="Dev", sector=setor_ti_a)
        colab_ti_a.position = cargo
        colab_ti_a.save()
        resp = as_user(api_client, rh_a).delete(f"{POSITIONS_URL}{cargo.id}/")
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════
# Paginação e filtros
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPaginacaoEFiltros:
    def test_listagem_de_colaboradores_e_paginada(
        self, api_client, django_user_model, rh_a, empresa_a
    ):
        for i in range(25):
            _user(django_user_model, f"p{i}@x.com", "colaborador", empresa_a)

        resp = as_user(api_client, rh_a).get(EMPLOYEES_URL)
        assert resp.status_code == 200
        assert "count" in resp.data and "next" in resp.data
        assert len(resp.data["results"]) == 20  # PAGE_SIZE
        assert resp.data["count"] >= 26

    def test_segunda_pagina_traz_o_restante(
        self, api_client, django_user_model, rh_a, empresa_a
    ):
        for i in range(25):
            _user(django_user_model, f"q{i}@x.com", "colaborador", empresa_a)
        resp = as_user(api_client, rh_a).get(EMPLOYEES_URL, {"page": 2})
        assert resp.status_code == 200
        assert len(resp.data["results"]) > 0

    def test_filtro_por_setor(self, api_client, rh_a, setor_ti_a, colab_ti_a, colab_rh_a):
        resp = as_user(api_client, rh_a).get(EMPLOYEES_URL, {"sector": setor_ti_a.id})
        emails = [e["email"] for e in resp.data["results"]]
        assert colab_ti_a.email in emails
        assert colab_rh_a.email not in emails

    def test_filtro_por_status(self, api_client, rh_a, colab_ti_a, colab_rh_a):
        colab_rh_a.is_active = False
        colab_rh_a.save()
        resp = as_user(api_client, rh_a).get(EMPLOYEES_URL, {"is_active": "false"})
        emails = [e["email"] for e in resp.data["results"]]
        assert colab_rh_a.email in emails
        assert colab_ti_a.email not in emails

    def test_busca_por_nome(self, api_client, rh_a, colab_ti_a):
        resp = as_user(api_client, rh_a).get(EMPLOYEES_URL, {"search": colab_ti_a.full_name[:6]})
        assert resp.data["count"] >= 1

    def test_filtro_invalido_retorna_400_nao_500(self, api_client, rh_a):
        resp = as_user(api_client, rh_a).get(EMPLOYEES_URL, {"sector": "abc"})
        assert resp.status_code == 400
