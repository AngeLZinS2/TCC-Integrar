"""
Testes da Fase P0 — segurança, privilégios e controle de sessão.

Cobre os seis itens da auditoria:
  P0-01  Platform Owner sem acesso a PII de colaboradores
  P0-02  Empresa suspensa bloqueia requisições autenticadas
  P0-03  Empresa suspensa bloqueia refresh de token
  P0-04  Rate limiting no login
  P0-05  Recuperação de senha
  P0-06  Logout com revogação real de sessão

Boa parte destes testes NÃO pode usar `force_authenticate`: ele injeta o
usuário direto na request e pula a camada de autenticação — justamente
onde mora a checagem de empresa suspensa. Por isso o token é obtido via
HTTP e enviado no header, como um cliente real faria.
"""

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings

from apps.companies.models import Company
from apps.courses.models import Course
from apps.sectors.models import Sector

TOKEN_URL = "/api/v1/auth/token/"
REFRESH_URL = "/api/v1/auth/token/refresh/"
LOGOUT_URL = "/api/v1/auth/logout/"
RESET_URL = "/api/v1/auth/password-reset/"
RESET_CONFIRM_URL = "/api/v1/auth/password-reset/confirm/"
ME_URL = "/api/v1/auth/me/"


# ── Helpers ──────────────────────────────────────────────────────────────────

def login(api_client, email, password="senha@123"):
    """Autentica via HTTP e devolve a resposta crua."""
    return api_client.post(TOKEN_URL, {"email": email, "password": password}, format="json")


def tokens_for(api_client, email, password="senha@123"):
    resp = login(api_client, email, password)
    assert resp.status_code == 200, f"login falhou: {resp.status_code} {resp.data}"
    return resp.data["access"], resp.data["refresh"]


def auth(api_client, access):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return api_client


def reset_link_parts():
    """Extrai uid e token do último e-mail de recuperação enviado."""
    body = mail.outbox[-1].body
    query = body.split("reset-password?")[1].split()[0]
    parts = dict(p.split("=", 1) for p in query.split("&"))
    return parts["uid"], parts["token"]


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def company_beta(db):
    return Company.objects.create(name="Empresa Beta")


@pytest.fixture
def rh_beta_user(db, django_user_model, company_beta):
    return django_user_model.objects.create_user(
        email="rh-beta@example.com", full_name="RH Beta", password="senha@123",
        role="rh_admin", company=company_beta,
    )


@pytest.fixture
def colaborador_beta_user(db, django_user_model, company_beta):
    return django_user_model.objects.create_user(
        email="colab-beta@example.com", full_name="Colab Beta", password="senha@123",
        role="colaborador", company=company_beta,
    )


# ══════════════════════════════════════════════════════════════════════════
# P0-01 — Platform Owner não acessa PII de colaboradores
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestOwnerSemAcessoAPII:
    def test_endpoint_de_colaboradores_da_empresa_nao_existe_mais(
        self, api_client, owner_user, company, colaborador_user
    ):
        access, _ = tokens_for(api_client, "owner@example.com")
        resp = auth(api_client, access).get(f"/api/v1/companies/{company.id}/collaborators/")
        assert resp.status_code == 404

    def test_owner_continua_vendo_lista_de_empresas(self, api_client, owner_user, company):
        access, _ = tokens_for(api_client, "owner@example.com")
        resp = auth(api_client, access).get("/api/v1/companies/")
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_owner_continua_vendo_metricas_agregadas(
        self, api_client, owner_user, company, colaborador_user
    ):
        access, _ = tokens_for(api_client, "owner@example.com")
        resp = auth(api_client, access).get(f"/api/v1/companies/{company.id}/dashboard/")
        assert resp.status_code == 200
        assert "total_collaborators" in resp.data
        assert "avg_course_completion_percent" in resp.data

    def test_metricas_agregadas_nao_contem_nenhum_dado_pessoal(
        self, api_client, owner_user, company, colaborador_user
    ):
        """O corpo inteiro da resposta não pode conter nome nem e-mail de ninguém."""
        access, _ = tokens_for(api_client, "owner@example.com")
        resp = auth(api_client, access).get(f"/api/v1/companies/{company.id}/dashboard/")
        corpo = str(resp.data)
        assert colaborador_user.full_name not in corpo
        assert colaborador_user.email not in corpo

    def test_resumo_da_empresa_na_listagem_nao_contem_pii(
        self, api_client, owner_user, company, colaborador_user
    ):
        access, _ = tokens_for(api_client, "owner@example.com")
        resp = auth(api_client, access).get("/api/v1/companies/")
        corpo = str(resp.data)
        assert colaborador_user.full_name not in corpo
        assert colaborador_user.email not in corpo

    def test_owner_nao_lista_colaboradores_pelo_painel_do_rh(self, api_client, owner_user):
        access, _ = tokens_for(api_client, "owner@example.com")
        resp = auth(api_client, access).get("/api/v1/dashboard/collaborators/")
        assert resp.status_code == 403

    def test_owner_nao_acessa_colaborador_por_id(self, api_client, owner_user, colaborador_user):
        access, _ = tokens_for(api_client, "owner@example.com")
        resp = auth(api_client, access).get(f"/api/v1/dashboard/collaborators/{colaborador_user.id}/")
        assert resp.status_code == 403

    def test_owner_nao_cadastra_colaborador(self, api_client, owner_user):
        access, _ = tokens_for(api_client, "owner@example.com")
        resp = auth(api_client, access).post(
            "/api/v1/auth/register/",
            {"email": "x@x.com", "full_name": "X", "role": "colaborador",
             "password": "senha@12345", "password_confirm": "senha@12345"},
            format="json",
        )
        assert resp.status_code == 403

    def test_owner_nao_desativa_colaborador(self, api_client, owner_user, colaborador_user):
        access, _ = tokens_for(api_client, "owner@example.com")
        resp = auth(api_client, access).post(
            f"/api/v1/auth/colaboradores/{colaborador_user.id}/toggle-active/"
        )
        assert resp.status_code == 403

    def test_owner_nao_exporta_csv_de_colaboradores(self, api_client, owner_user):
        access, _ = tokens_for(api_client, "owner@example.com")
        resp = auth(api_client, access).get("/api/v1/dashboard/collaborators/export/")
        assert resp.status_code == 403

    def test_rh_continua_acessando_colaboradores_da_propria_empresa(
        self, api_client, rh_admin_user, colaborador_user
    ):
        access, _ = tokens_for(api_client, "rh@example.com")
        resp = auth(api_client, access).get("/api/v1/dashboard/collaborators/")
        assert resp.status_code == 200
        emails = [linha["email"] for linha in resp.data]
        assert colaborador_user.email in emails

    def test_rh_nao_acessa_colaborador_de_outra_empresa(
        self, api_client, rh_admin_user, colaborador_beta_user
    ):
        access, _ = tokens_for(api_client, "rh@example.com")
        resp = auth(api_client, access).get(
            f"/api/v1/dashboard/collaborators/{colaborador_beta_user.id}/"
        )
        assert resp.status_code == 404

    def test_colaborador_nao_acessa_lista_administrativa(self, api_client, colaborador_user):
        access, _ = tokens_for(api_client, "colaborador@example.com")
        resp = auth(api_client, access).get("/api/v1/dashboard/collaborators/")
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════
# P0-02 / P0-03 — Suspensão de empresa é real
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSuspensaoDeEmpresa:
    def test_empresa_ativa_login_api_e_refresh_funcionam(self, api_client, rh_admin_user):
        access, refresh = tokens_for(api_client, "rh@example.com")
        assert auth(api_client, access).get(ME_URL).status_code == 200
        api_client.credentials()
        assert api_client.post(REFRESH_URL, {"refresh": refresh}, format="json").status_code == 200

    def test_empresa_suspensa_bloqueia_login(self, api_client, rh_admin_user, company):
        company.is_active = False
        company.save()
        assert login(api_client, "rh@example.com").status_code == 401

    def test_empresa_suspensa_bloqueia_api_com_token_ja_emitido(
        self, api_client, rh_admin_user, company
    ):
        """O coração do P0-02: o token foi emitido ANTES da suspensão."""
        access, _ = tokens_for(api_client, "rh@example.com")
        assert auth(api_client, access).get(ME_URL).status_code == 200

        company.is_active = False
        company.save()

        assert auth(api_client, access).get(ME_URL).status_code == 401

    def test_empresa_suspensa_bloqueia_todos_os_endpoints_de_negocio(
        self, api_client, rh_admin_user, company
    ):
        access, _ = tokens_for(api_client, "rh@example.com")
        company.is_active = False
        company.save()

        cliente = auth(api_client, access)
        for url in ["/api/v1/courses/", "/api/v1/materials/", "/api/v1/checklist/",
                    "/api/v1/sectors/", "/api/v1/dashboard/overview/", "/api/v1/notifications/"]:
            assert cliente.get(url).status_code == 401, f"{url} deveria bloquear"

    def test_empresa_suspensa_bloqueia_refresh(self, api_client, rh_admin_user, company):
        """O coração do P0-03: sem isso a sessão se renovaria por 7 dias."""
        _, refresh = tokens_for(api_client, "rh@example.com")
        company.is_active = False
        company.save()

        api_client.credentials()
        assert api_client.post(REFRESH_URL, {"refresh": refresh}, format="json").status_code == 401

    def test_mensagem_de_empresa_suspensa_nao_expoe_detalhe_tecnico(
        self, api_client, rh_admin_user, company
    ):
        access, _ = tokens_for(api_client, "rh@example.com")
        company.is_active = False
        company.save()
        resp = auth(api_client, access).get(ME_URL)
        assert "suspensa" in str(resp.data).lower()

    def test_os_tres_401_carregam_o_mesmo_codigo_company_suspended(
        self, api_client, rh_admin_user, company
    ):
        """
        Login, API e refresh precisam devolver o MESMO código para que o app
        trate os três por um caminho só — sem depender do texto da mensagem.
        """
        access, refresh = tokens_for(api_client, "rh@example.com")
        company.is_active = False
        company.save()

        na_api = auth(api_client, access).get(ME_URL)
        api_client.credentials()
        no_refresh = api_client.post(REFRESH_URL, {"refresh": refresh}, format="json")
        cache.clear()
        no_login = login(api_client, "rh@example.com")

        for resp in (na_api, no_refresh, no_login):
            assert resp.status_code == 401
            assert str(resp.data.get("code")) == "company_suspended", resp.data

    def test_colaborador_de_empresa_suspensa_tambem_e_bloqueado(
        self, api_client, colaborador_user, company
    ):
        access, _ = tokens_for(api_client, "colaborador@example.com")
        company.is_active = False
        company.save()
        assert auth(api_client, access).get(ME_URL).status_code == 401

    def test_owner_nao_e_afetado_por_suspensao(self, api_client, owner_user, company):
        """Owner não tem empresa — não pode ser bloqueado por esta regra."""
        access, refresh = tokens_for(api_client, "owner@example.com")
        company.is_active = False
        company.save()

        assert auth(api_client, access).get(ME_URL).status_code == 200
        api_client.credentials()
        assert api_client.post(REFRESH_URL, {"refresh": refresh}, format="json").status_code == 200

    def test_suspensao_de_uma_empresa_nao_afeta_a_outra(
        self, api_client, rh_admin_user, rh_beta_user, company
    ):
        access_beta, _ = tokens_for(api_client, "rh-beta@example.com")
        company.is_active = False   # suspende a Demo, não a Beta
        company.save()
        assert auth(api_client, access_beta).get(ME_URL).status_code == 200

    def test_reativar_empresa_restaura_o_acesso(self, api_client, rh_admin_user, company):
        access, _ = tokens_for(api_client, "rh@example.com")
        company.is_active = False
        company.save()
        assert auth(api_client, access).get(ME_URL).status_code == 401

        company.is_active = True
        company.save()
        assert auth(api_client, access).get(ME_URL).status_code == 200

    def test_usuario_desativado_e_bloqueado_na_hora(self, api_client, colaborador_user):
        access, _ = tokens_for(api_client, "colaborador@example.com")
        colaborador_user.is_active = False
        colaborador_user.save()
        assert auth(api_client, access).get(ME_URL).status_code == 401

    def test_usuario_desativado_nao_consegue_refresh(self, api_client, colaborador_user):
        _, refresh = tokens_for(api_client, "colaborador@example.com")
        colaborador_user.is_active = False
        colaborador_user.save()
        api_client.credentials()
        assert api_client.post(REFRESH_URL, {"refresh": refresh}, format="json").status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# P0-04 — Rate limiting no login
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestRateLimitLogin:
    def test_primeira_tentativa_processa(self, api_client, rh_admin_user):
        assert login(api_client, "rh@example.com").status_code == 200

    def test_tentativas_dentro_do_limite_processam(self, api_client, rh_admin_user):
        for _ in range(4):
            assert login(api_client, "rh@example.com", "errada").status_code == 401

    def test_ao_exceder_o_limite_retorna_429(self, api_client, rh_admin_user):
        for _ in range(5):
            login(api_client, "rh@example.com", "errada")
        assert login(api_client, "rh@example.com", "errada").status_code == 429

    def test_429_tambem_vale_para_senha_correta_apos_o_limite(self, api_client, rh_admin_user):
        """Depois de estourar o limite, nem a senha certa passa."""
        for _ in range(5):
            login(api_client, "rh@example.com", "errada")
        assert login(api_client, "rh@example.com").status_code == 429

    def test_apos_a_janela_o_login_volta_a_funcionar(self, api_client, rh_admin_user):
        """
        Limpar o cache reproduz o efeito da janela de 1 minuto expirando —
        é onde o histórico de tentativas do throttle vive.
        """
        for _ in range(5):
            login(api_client, "rh@example.com", "errada")
        assert login(api_client, "rh@example.com").status_code == 429

        cache.clear()
        assert login(api_client, "rh@example.com").status_code == 200

    def test_bloqueio_por_email_alcanca_conta_alvo(self, api_client, rh_admin_user):
        """
        O throttle por e-mail existe para o ataque distribuído: mesmo que o
        IP mude, a conta alvo continua protegida.
        """
        for _ in range(5):
            login(api_client, "rh@example.com", "errada")
        resp = api_client.post(
            TOKEN_URL, {"email": "rh@example.com", "password": "errada"},
            format="json", REMOTE_ADDR="203.0.113.77",
        )
        assert resp.status_code == 429

    def test_erro_de_login_nao_revela_se_o_email_existe(self, api_client, rh_admin_user):
        existente = login(api_client, "rh@example.com", "errada")
        cache.clear()
        inexistente = login(api_client, "nao-existe@example.com", "errada")

        assert existente.status_code == inexistente.status_code == 401
        assert str(existente.data) == str(inexistente.data)


# ══════════════════════════════════════════════════════════════════════════
# P0-05 — Recuperação de senha
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestRecuperacaoDeSenha:
    def test_pedido_com_email_existente_envia_email(self, api_client, colaborador_user):
        resp = api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        assert resp.status_code == 200
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["colaborador@example.com"]

    def test_pedido_com_email_inexistente_responde_igual_e_nao_envia(self, api_client):
        resp = api_client.post(RESET_URL, {"email": "ninguem@example.com"}, format="json")
        assert resp.status_code == 200
        assert len(mail.outbox) == 0

    def test_resposta_e_identica_para_email_existente_e_inexistente(
        self, api_client, colaborador_user
    ):
        """Impede enumeração de contas pela resposta do endpoint."""
        existente = api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        cache.clear()
        inexistente = api_client.post(RESET_URL, {"email": "ninguem@example.com"}, format="json")

        assert existente.status_code == inexistente.status_code == 200
        assert existente.data == inexistente.data

    def test_resposta_nunca_devolve_o_token(self, api_client, colaborador_user):
        resp = api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        corpo = str(resp.data)
        assert "token" not in corpo.lower()
        assert "uid" not in corpo.lower()

    def test_fluxo_completo_troca_a_senha(self, api_client, colaborador_user):
        api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        uid, token = reset_link_parts()

        resp = api_client.post(
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token,
             "new_password": "NovaSenha@2026", "new_password_confirm": "NovaSenha@2026"},
            format="json",
        )
        assert resp.status_code == 200

        colaborador_user.refresh_from_db()
        assert colaborador_user.check_password("NovaSenha@2026")

    def test_senha_nova_permite_login_e_antiga_nao(self, api_client, colaborador_user):
        api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        uid, token = reset_link_parts()
        api_client.post(
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token,
             "new_password": "NovaSenha@2026", "new_password_confirm": "NovaSenha@2026"},
            format="json",
        )
        cache.clear()

        assert login(api_client, "colaborador@example.com", "NovaSenha@2026").status_code == 200
        cache.clear()
        assert login(api_client, "colaborador@example.com", "senha@123").status_code == 401

    def test_token_nao_pode_ser_reutilizado(self, api_client, colaborador_user):
        api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        uid, token = reset_link_parts()
        corpo = {"uid": uid, "token": token,
                 "new_password": "NovaSenha@2026", "new_password_confirm": "NovaSenha@2026"}

        assert api_client.post(RESET_CONFIRM_URL, corpo, format="json").status_code == 200
        assert api_client.post(RESET_CONFIRM_URL, corpo, format="json").status_code == 400

    @override_settings(PASSWORD_RESET_TIMEOUT=-1)
    def test_token_expirado_e_rejeitado(self, api_client, colaborador_user):
        api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        uid, token = reset_link_parts()

        resp = api_client.post(
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token,
             "new_password": "NovaSenha@2026", "new_password_confirm": "NovaSenha@2026"},
            format="json",
        )
        assert resp.status_code == 400

    def test_token_invalido_e_rejeitado(self, api_client, colaborador_user):
        api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        uid, _ = reset_link_parts()

        resp = api_client.post(
            RESET_CONFIRM_URL,
            {"uid": uid, "token": "token-forjado",
             "new_password": "NovaSenha@2026", "new_password_confirm": "NovaSenha@2026"},
            format="json",
        )
        assert resp.status_code == 400

    def test_senhas_diferentes_sao_rejeitadas(self, api_client, colaborador_user):
        api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        uid, token = reset_link_parts()

        resp = api_client.post(
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token,
             "new_password": "NovaSenha@2026", "new_password_confirm": "Outra@2026"},
            format="json",
        )
        assert resp.status_code == 400

    def test_senha_fraca_e_rejeitada_pelos_validadores_do_django(
        self, api_client, colaborador_user
    ):
        api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        uid, token = reset_link_parts()

        resp = api_client.post(
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token,
             "new_password": "12345678", "new_password_confirm": "12345678"},
            format="json",
        )
        assert resp.status_code == 400

    def test_usuario_de_empresa_suspensa_nao_recebe_email(
        self, api_client, colaborador_user, company
    ):
        company.is_active = False
        company.save()
        resp = api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        assert resp.status_code == 200
        assert len(mail.outbox) == 0

    def test_usuario_desativado_nao_recebe_email(self, api_client, colaborador_user):
        colaborador_user.is_active = False
        colaborador_user.save()
        api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        assert len(mail.outbox) == 0

    def test_reset_de_senha_invalida_sessoes_antigas(self, api_client, colaborador_user):
        """Trocar a senha derruba quem estiver logado com a sessão anterior."""
        _, refresh_antigo = tokens_for(api_client, "colaborador@example.com")

        api_client.post(RESET_URL, {"email": "colaborador@example.com"}, format="json")
        uid, token = reset_link_parts()
        api_client.post(
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token,
             "new_password": "NovaSenha@2026", "new_password_confirm": "NovaSenha@2026"},
            format="json",
        )

        resp = api_client.post(REFRESH_URL, {"refresh": refresh_antigo}, format="json")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# P0-06 — Logout com revogação real
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestLogout:
    def test_logout_retorna_205(self, api_client, colaborador_user):
        access, refresh = tokens_for(api_client, "colaborador@example.com")
        resp = auth(api_client, access).post(LOGOUT_URL, {"refresh": refresh}, format="json")
        assert resp.status_code == 205

    def test_refresh_apos_logout_e_rejeitado(self, api_client, colaborador_user):
        """O coração do P0-06: antes, o refresh continuava valendo por 7 dias."""
        access, refresh = tokens_for(api_client, "colaborador@example.com")
        auth(api_client, access).post(LOGOUT_URL, {"refresh": refresh}, format="json")

        api_client.credentials()
        resp = api_client.post(REFRESH_URL, {"refresh": refresh}, format="json")
        assert resp.status_code == 401

    def test_logout_sem_refresh_retorna_400(self, api_client, colaborador_user):
        access, _ = tokens_for(api_client, "colaborador@example.com")
        assert auth(api_client, access).post(LOGOUT_URL, {}, format="json").status_code == 400

    def test_logout_exige_autenticacao(self, api_client):
        assert api_client.post(LOGOUT_URL, {"refresh": "x"}, format="json").status_code == 401

    def test_logout_repetido_nao_quebra(self, api_client, colaborador_user):
        access, refresh = tokens_for(api_client, "colaborador@example.com")
        cliente = auth(api_client, access)
        assert cliente.post(LOGOUT_URL, {"refresh": refresh}, format="json").status_code == 205
        assert cliente.post(LOGOUT_URL, {"refresh": refresh}, format="json").status_code == 205

    def test_refresh_antigo_morre_apos_rotacao(self, api_client, colaborador_user):
        """BLACKLIST_AFTER_ROTATION: um refresh já usado não vale de novo."""
        _, refresh = tokens_for(api_client, "colaborador@example.com")

        primeira = api_client.post(REFRESH_URL, {"refresh": refresh}, format="json")
        assert primeira.status_code == 200

        segunda = api_client.post(REFRESH_URL, {"refresh": refresh}, format="json")
        assert segunda.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# Multi-tenant — garantia de que a Fase P0 não afrouxou o isolamento
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIsolamentoContinuaIntacto:
    def test_rh_de_uma_empresa_nao_le_recurso_da_outra(
        self, api_client, rh_admin_user, company_beta
    ):
        curso_beta = Course.objects.create(title="Curso Beta", company=company_beta, order=1)
        access, _ = tokens_for(api_client, "rh@example.com")
        assert auth(api_client, access).get(f"/api/v1/courses/{curso_beta.id}/").status_code == 404

    def test_rh_de_uma_empresa_nao_edita_recurso_da_outra(
        self, api_client, rh_admin_user, company_beta
    ):
        curso_beta = Course.objects.create(title="Curso Beta", company=company_beta, order=1)
        access, _ = tokens_for(api_client, "rh@example.com")
        cliente = auth(api_client, access)
        assert cliente.patch(
            f"/api/v1/courses/{curso_beta.id}/", {"title": "Invadido"}, format="json"
        ).status_code == 404
        assert cliente.delete(f"/api/v1/courses/{curso_beta.id}/").status_code == 404

    def test_criacao_com_fk_de_outro_tenant_continua_bloqueada(
        self, api_client, rh_admin_user, company_beta
    ):
        setor_beta = Sector.objects.create(name="Ops Beta", company=company_beta)
        access, _ = tokens_for(api_client, "rh@example.com")
        resp = auth(api_client, access).post(
            "/api/v1/courses/",
            {"title": "Tentativa", "sector": setor_beta.id, "order": 1},
            format="json",
        )
        assert resp.status_code == 400

    def test_listagem_so_traz_recursos_da_propria_empresa(
        self, api_client, rh_admin_user, company, company_beta
    ):
        Course.objects.create(title="Curso Demo", company=company, order=1)
        Course.objects.create(title="Curso Beta", company=company_beta, order=1)

        access, _ = tokens_for(api_client, "rh@example.com")
        resp = auth(api_client, access).get("/api/v1/courses/")
        titulos = [c["title"] for c in resp.data["results"]]
        assert "Curso Demo" in titulos
        assert "Curso Beta" not in titulos
