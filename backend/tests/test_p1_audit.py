"""
Testes da Fase P1 — audit log e configurações da empresa.
"""

import pytest

from apps.audit.models import AuditLog
from apps.companies.models import Company
from apps.sectors.models import Sector

AUDIT_URL = "/api/v1/audit/"
EMPLOYEES_URL = "/api/v1/employees/"
SECTORS_URL = "/api/v1/sectors/"
MY_COMPANY_URL = "/api/v1/companies/me/"
SETUP_URL = "/api/v1/companies/me/setup/"


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa B")


def _user(django_user_model, email, role, company, **extra):
    return django_user_model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **extra
    )


@pytest.fixture
def admin_a(db, django_user_model, company):
    return _user(django_user_model, "admin-a@x.com", "company_admin", company)


@pytest.fixture
def admin_b(db, django_user_model, empresa_b):
    return _user(django_user_model, "admin-b@x.com", "company_admin", empresa_b)


def as_user(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


# ══════════════════════════════════════════════════════════════════════════
# Registro de eventos
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestRegistroDeEventos:
    def test_criar_colaborador_gera_registro(self, api_client, admin_a):
        as_user(api_client, admin_a).post(
            EMPLOYEES_URL,
            {"email": "novo@x.com", "full_name": "Novo", "role": "colaborador",
             "password": "senha@12345", "password_confirm": "senha@12345"},
            format="json",
        )
        log = AuditLog.objects.filter(resource_type="employee", action="create").first()
        assert log is not None
        assert log.actor_id == admin_a.id
        assert log.company_id == admin_a.company_id
        assert log.resource_label == "Novo"

    def test_editar_colaborador_registra_os_campos_alterados(
        self, api_client, admin_a, colaborador_user
    ):
        as_user(api_client, admin_a).patch(
            f"{EMPLOYEES_URL}{colaborador_user.id}/",
            {"phone": "11999998888"},
            format="json",
        )
        log = AuditLog.objects.filter(resource_type="employee", action="update").first()
        assert log is not None
        assert log.metadata["changed_fields"] == ["phone"]

    def test_troca_de_papel_tem_acao_propria(self, api_client, admin_a, colaborador_user):
        as_user(api_client, admin_a).patch(
            f"{EMPLOYEES_URL}{colaborador_user.id}/", {"role": "gestor"}, format="json"
        )
        log = AuditLog.objects.filter(action=AuditLog.Action.ROLE_CHANGE).first()
        assert log is not None
        assert log.metadata == {"from": "colaborador", "to": "gestor"}

    def test_desativar_gera_registro(self, api_client, admin_a, colaborador_user):
        as_user(api_client, admin_a).post(
            f"{EMPLOYEES_URL}{colaborador_user.id}/toggle-active/"
        )
        assert AuditLog.objects.filter(action=AuditLog.Action.DEACTIVATE).exists()

    def test_reativar_gera_registro(self, api_client, admin_a, colaborador_user):
        colaborador_user.is_active = False
        colaborador_user.save()
        as_user(api_client, admin_a).post(
            f"{EMPLOYEES_URL}{colaborador_user.id}/toggle-active/"
        )
        assert AuditLog.objects.filter(action=AuditLog.Action.ACTIVATE).exists()

    def test_criar_setor_gera_registro(self, api_client, admin_a):
        as_user(api_client, admin_a).post(SECTORS_URL, {"name": "Financeiro"}, format="json")
        log = AuditLog.objects.filter(resource_type="sector", action="create").first()
        assert log is not None
        assert log.resource_label == "Financeiro"

    def test_login_gera_registro(self, api_client, colaborador_user):
        api_client.post(
            "/api/v1/auth/token/",
            {"email": "colaborador@example.com", "password": "senha@123"},
            format="json",
        )
        log = AuditLog.objects.filter(action=AuditLog.Action.LOGIN).first()
        assert log is not None
        assert log.actor_id == colaborador_user.id

    def test_login_falho_nao_gera_registro(self, api_client, colaborador_user):
        api_client.post(
            "/api/v1/auth/token/",
            {"email": "colaborador@example.com", "password": "errada"},
            format="json",
        )
        assert not AuditLog.objects.filter(action=AuditLog.Action.LOGIN).exists()

    def test_registro_nunca_guarda_senha(self, api_client, admin_a):
        as_user(api_client, admin_a).post(
            EMPLOYEES_URL,
            {"email": "seguro@x.com", "full_name": "Seguro", "role": "colaborador",
             "password": "SenhaSecreta@123", "password_confirm": "SenhaSecreta@123"},
            format="json",
        )
        for log in AuditLog.objects.all():
            corpo = str(log.metadata) + log.resource_label
            assert "SenhaSecreta" not in corpo
            assert "password" not in str(log.metadata)

    def test_falha_na_auditoria_nao_derruba_a_operacao(
        self, api_client, admin_a, colaborador_user, monkeypatch
    ):
        """
        Auditoria com defeito não pode impedir o RH de trabalhar — o helper
        engole a exceção e a requisição segue normalmente.
        """
        from apps.audit import services

        def explode(*args, **kwargs):
            raise RuntimeError("banco de auditoria fora do ar")

        monkeypatch.setattr(services.AuditLog.objects, "create", explode)
        resp = as_user(api_client, admin_a).patch(
            f"{EMPLOYEES_URL}{colaborador_user.id}/", {"phone": "11900000000"}, format="json"
        )
        assert resp.status_code == 200
        colaborador_user.refresh_from_db()
        assert colaborador_user.phone == "11900000000"


# ══════════════════════════════════════════════════════════════════════════
# Leitura do histórico
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestLeituraDoHistorico:
    def test_company_admin_le_o_historico(self, api_client, admin_a):
        as_user(api_client, admin_a).post(SECTORS_URL, {"name": "X"}, format="json")
        resp = api_client.get(AUDIT_URL)
        assert resp.status_code == 200
        assert resp.data["count"] >= 1

    def test_rh_nao_le_o_historico(self, api_client, rh_admin_user):
        """audit.read é exclusivo do admin da empresa."""
        resp = as_user(api_client, rh_admin_user).get(AUDIT_URL)
        assert resp.status_code == 403

    def test_colaborador_nao_le_o_historico(self, api_client, colaborador_user):
        resp = as_user(api_client, colaborador_user).get(AUDIT_URL)
        assert resp.status_code == 403

    def test_owner_nao_le_historico_de_empresa(self, api_client, owner_user):
        resp = as_user(api_client, owner_user).get(AUDIT_URL)
        assert resp.status_code == 403

    def test_historico_e_isolado_por_empresa(self, api_client, admin_a, admin_b):
        as_user(api_client, admin_b).post(SECTORS_URL, {"name": "Setor da B"}, format="json")
        resp = as_user(api_client, admin_a).get(AUDIT_URL)
        rotulos = [r["resource_label"] for r in resp.data["results"]]
        assert "Setor da B" not in rotulos

    def test_historico_e_somente_leitura(self, api_client, admin_a):
        """
        Não existe rota de escrita nem de detalhe: POST cai em 405 e as
        rotas de alteração/exclusão sequer são registradas (404). Um log
        editável pela API não serviria como auditoria.
        """
        cliente = as_user(api_client, admin_a)
        assert cliente.post(AUDIT_URL, {}, format="json").status_code == 405
        assert cliente.delete(f"{AUDIT_URL}1/").status_code == 404
        assert cliente.patch(f"{AUDIT_URL}1/", {}, format="json").status_code == 404

    def test_filtro_por_acao(self, api_client, admin_a, colaborador_user):
        cliente = as_user(api_client, admin_a)
        cliente.post(SECTORS_URL, {"name": "Y"}, format="json")
        cliente.post(f"{EMPLOYEES_URL}{colaborador_user.id}/toggle-active/")

        resp = cliente.get(AUDIT_URL, {"action": "deactivate"})
        assert all(r["action"] == "deactivate" for r in resp.data["results"])
        assert resp.data["count"] >= 1

    def test_filtro_por_tipo_de_recurso(self, api_client, admin_a):
        cliente = as_user(api_client, admin_a)
        cliente.post(SECTORS_URL, {"name": "Z"}, format="json")
        resp = cliente.get(AUDIT_URL, {"resource_type": "sector"})
        assert all(r["resource_type"] == "sector" for r in resp.data["results"])

    def test_resumo_legivel(self, api_client, admin_a):
        as_user(api_client, admin_a).post(SECTORS_URL, {"name": "Compras"}, format="json")
        resp = api_client.get(AUDIT_URL)
        registro = resp.data["results"][0]
        assert registro["summary"] == f"{admin_a.full_name} criou o setor Compras"

    def test_resumo_de_sessao_nao_expoe_jargao_tecnico(self, api_client, colaborador_user):
        """
        'entrou no sistema' já se explica — anexar o tipo interno do recurso
        ('session') deixaria jargão de banco visível na tela.
        """
        api_client.post(
            "/api/v1/auth/token/",
            {"email": "colaborador@example.com", "password": "senha@123"},
            format="json",
        )
        from apps.audit.serializers import AuditLogSerializer

        log = AuditLog.objects.filter(action=AuditLog.Action.LOGIN).first()
        resumo = AuditLogSerializer(log).data["summary"]
        assert resumo == f"{colaborador_user.full_name} entrou no sistema"
        assert "session" not in resumo

    def test_historico_e_paginado(self, api_client, admin_a):
        cliente = as_user(api_client, admin_a)
        for i in range(25):
            cliente.post(SECTORS_URL, {"name": f"Setor {i}"}, format="json")
        resp = cliente.get(AUDIT_URL)
        assert len(resp.data["results"]) == 20
        assert resp.data["next"] is not None


# ══════════════════════════════════════════════════════════════════════════
# Configurações da empresa
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestConfiguracoesDaEmpresa:
    def test_admin_le_dados_da_propria_empresa(self, api_client, admin_a, company):
        resp = as_user(api_client, admin_a).get(MY_COMPANY_URL)
        assert resp.status_code == 200
        assert resp.data["name"] == company.name

    def test_admin_altera_dados_da_empresa(self, api_client, admin_a, company):
        resp = as_user(api_client, admin_a).patch(
            MY_COMPANY_URL,
            {"legal_name": "Empresa Teste LTDA", "cnpj": "12.345.678/0001-90",
             "phone": "1133334444"},
            format="json",
        )
        assert resp.status_code == 200
        company.refresh_from_db()
        assert company.legal_name == "Empresa Teste LTDA"

    def test_rh_le_mas_nao_altera(self, api_client, rh_admin_user):
        cliente = as_user(api_client, rh_admin_user)
        assert cliente.get(MY_COMPANY_URL).status_code == 200
        resp = cliente.patch(MY_COMPANY_URL, {"legal_name": "Hack"}, format="json")
        assert resp.status_code == 403

    def test_colaborador_nao_altera(self, api_client, colaborador_user):
        resp = as_user(api_client, colaborador_user).patch(
            MY_COMPANY_URL, {"legal_name": "Hack"}, format="json"
        )
        assert resp.status_code == 403

    def test_empresa_a_nao_altera_dados_da_empresa_b(
        self, api_client, admin_a, admin_b, empresa_b, company
    ):
        """
        O endpoint não aceita id — o escopo vem sempre do usuário, então não
        existe parâmetro para manipular.
        """
        as_user(api_client, admin_a).patch(
            MY_COMPANY_URL, {"legal_name": "Alterado por A"}, format="json"
        )
        empresa_b.refresh_from_db()
        company.refresh_from_db()
        assert empresa_b.legal_name == ""
        assert company.legal_name == "Alterado por A"

    def test_status_da_empresa_nao_e_editavel_pelo_tenant(
        self, api_client, admin_a, company
    ):
        """Suspender empresa é decisão comercial da plataforma."""
        as_user(api_client, admin_a).patch(MY_COMPANY_URL, {"is_active": False}, format="json")
        company.refresh_from_db()
        assert company.is_active is True

    def test_alteracao_da_empresa_e_auditada(self, api_client, admin_a):
        as_user(api_client, admin_a).patch(
            MY_COMPANY_URL, {"description": "Nova descrição"}, format="json"
        )
        log = AuditLog.objects.filter(resource_type="company").first()
        assert log is not None
        assert log.metadata["changed_fields"] == ["description"]


# ══════════════════════════════════════════════════════════════════════════
# Checklist de configuração inicial
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestChecklistDeConfiguracao:
    def test_empresa_nova_comeca_com_tudo_pendente(self, api_client, admin_a):
        resp = as_user(api_client, admin_a).get(SETUP_URL)
        assert resp.status_code == 200
        assert resp.data["completed_steps"] == 0
        assert resp.data["percent"] == 0
        assert resp.data["is_complete"] is False
        assert len(resp.data["steps"]) == 6

    def test_criar_setor_marca_o_passo(self, api_client, admin_a):
        cliente = as_user(api_client, admin_a)
        cliente.post(SECTORS_URL, {"name": "TI"}, format="json")
        resp = cliente.get(SETUP_URL)
        passo = next(p for p in resp.data["steps"] if p["key"] == "first_sector")
        assert passo["done"] is True
        assert resp.data["completed_steps"] == 1

    def test_preencher_dados_marca_o_passo_da_empresa(self, api_client, admin_a):
        cliente = as_user(api_client, admin_a)
        cliente.patch(MY_COMPANY_URL, {"cnpj": "12.345.678/0001-90"}, format="json")
        resp = cliente.get(SETUP_URL)
        passo = next(p for p in resp.data["steps"] if p["key"] == "company_info")
        assert passo["done"] is True

    def test_progresso_reflete_o_estado_real_do_banco(
        self, api_client, admin_a, company, colaborador_user
    ):
        """
        Não há flag "já configurei": o checklist deriva do banco, então não
        tem como ficar dessincronizado da realidade.
        """
        Sector.objects.create(name="TI", company=company)
        resp = as_user(api_client, admin_a).get(SETUP_URL)
        feitos = {p["key"] for p in resp.data["steps"] if p["done"]}
        assert "first_sector" in feitos
        assert "first_employee" in feitos
        assert "first_training" not in feitos

    def test_checklist_e_isolado_por_empresa(self, api_client, admin_a, admin_b, empresa_b):
        Sector.objects.create(name="Setor da B", company=empresa_b)
        resp = as_user(api_client, admin_a).get(SETUP_URL)
        passo = next(p for p in resp.data["steps"] if p["key"] == "first_sector")
        assert passo["done"] is False

    def test_owner_nao_acessa_checklist_de_empresa(self, api_client, owner_user):
        resp = as_user(api_client, owner_user).get(SETUP_URL)
        assert resp.status_code == 403
