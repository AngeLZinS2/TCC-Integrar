"""
Testes de autenticação e controle de acesso por papel.

Cobre:
  - Login com credenciais corretas / erradas
  - Refresh de token
  - Endpoint /me/ autenticado e sem autenticação
  - Cadastro de usuário por rh_admin e rejeição por colaborador
  - Propriedade is_rh_admin no model
"""

import pytest
from django.urls import reverse


# ── Fixtures locais ─────────────────────────────────────────────────────────

@pytest.fixture
def rh_token(api_client, rh_admin_user):
    """Retorna o access token de um rh_admin já autenticado."""
    url = reverse("token_obtain_pair")
    resp = api_client.post(url, {"email": "rh@example.com", "password": "senha@123"}, format="json")
    return resp.data["access"]


@pytest.fixture
def colaborador_token(api_client, colaborador_user):
    """Retorna o access token de um colaborador já autenticado."""
    url = reverse("token_obtain_pair")
    resp = api_client.post(url, {"email": "colaborador@example.com", "password": "senha@123"}, format="json")
    return resp.data["access"]


# ── Testes de login ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogin:
    URL = "/api/v1/auth/token/"

    def test_login_success_returns_tokens_and_user(self, api_client, rh_admin_user):
        resp = api_client.post(self.URL, {"email": "rh@example.com", "password": "senha@123"}, format="json")

        assert resp.status_code == 200
        assert "access" in resp.data
        assert "refresh" in resp.data
        # Verifica que dados do usuário vêm embutidos (evita round-trip extra)
        assert resp.data["user"]["email"] == "rh@example.com"
        assert resp.data["user"]["role"] == "rh_admin"

    def test_login_wrong_password_returns_401(self, api_client, rh_admin_user):
        resp = api_client.post(self.URL, {"email": "rh@example.com", "password": "errada"}, format="json")
        assert resp.status_code == 401

    def test_login_nonexistent_email_returns_401(self, api_client):
        resp = api_client.post(self.URL, {"email": "naoexiste@example.com", "password": "qualquer"}, format="json")
        assert resp.status_code == 401

    def test_login_inactive_user_returns_401(self, api_client, colaborador_user):
        colaborador_user.is_active = False
        colaborador_user.save()
        resp = api_client.post(self.URL, {"email": "colaborador@example.com", "password": "senha@123"}, format="json")
        assert resp.status_code == 401


# ── Testes de refresh token ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestTokenRefresh:
    def test_refresh_with_valid_token_returns_new_access(self, api_client, rh_admin_user):
        # Obtém tokens via login
        login_resp = api_client.post(
            "/api/v1/auth/token/",
            {"email": "rh@example.com", "password": "senha@123"},
            format="json",
        )
        refresh = login_resp.data["refresh"]

        resp = api_client.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")

        assert resp.status_code == 200
        assert "access" in resp.data

    def test_refresh_with_invalid_token_returns_401(self, api_client):
        resp = api_client.post("/api/v1/auth/token/refresh/", {"refresh": "token_invalido"}, format="json")
        assert resp.status_code == 401


# ── Testes do endpoint /me/ ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestMeView:
    URL = "/api/v1/auth/me/"

    def test_me_unauthenticated_returns_401(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == 401

    def test_me_authenticated_returns_user_data(self, api_client, colaborador_user, colaborador_token):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {colaborador_token}")
        resp = api_client.get(self.URL)

        assert resp.status_code == 200
        assert resp.data["email"] == "colaborador@example.com"
        assert resp.data["full_name"] == "João Silva"
        assert resp.data["role"] == "colaborador"

    def test_me_patch_updates_full_name(self, api_client, colaborador_user, colaborador_token):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {colaborador_token}")
        resp = api_client.patch(self.URL, {"full_name": "João Santos"}, format="json")

        assert resp.status_code == 200
        assert resp.data["full_name"] == "João Santos"

    def test_me_cannot_change_role_via_patch(self, api_client, colaborador_user, colaborador_token):
        """role é read-only — mudança de papel só via admin Django."""
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {colaborador_token}")
        resp = api_client.patch(self.URL, {"role": "rh_admin"}, format="json")

        assert resp.status_code == 200
        # role permanece colaborador
        colaborador_user.refresh_from_db()
        assert colaborador_user.role == "colaborador"

    def test_me_patch_nao_permite_autoatribuir_setor_de_outra_empresa(
        self, api_client, colaborador_user, colaborador_token
    ):
        """
        Multi-tenant: colaborador não pode se autoatribuir setor de outra empresa.

        Desde a P1 o campo `sector` é read-only em /auth/me/ — quem define
        setor é o RH. A API responde 200 ignorando o campo (comportamento
        padrão do DRF para read-only), e o setor permanece inalterado.
        """
        from apps.companies.models import Company
        from apps.sectors.models import Sector

        other_company = Company.objects.create(name="Outra Empresa")
        foreign_sector = Sector.objects.create(name="Setor Estranho", company=other_company)
        sector_antes = colaborador_user.sector_id

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {colaborador_token}")
        resp = api_client.patch(self.URL, {"sector": foreign_sector.id}, format="json")

        assert resp.status_code == 200
        colaborador_user.refresh_from_db()
        assert colaborador_user.sector_id == sector_antes
        assert colaborador_user.sector_id != foreign_sector.id


# ── Testes de cadastro de usuário ───────────────────────────────────────────

@pytest.mark.django_db
class TestRegisterView:
    URL = "/api/v1/auth/register/"
    NEW_USER = {
        "email": "novo@example.com",
        "full_name": "Novo Colaborador",
        "role": "colaborador",
        "password": "senha@123",
        "password_confirm": "senha@123",
    }

    def test_rh_admin_can_register_new_user(self, api_client, rh_admin_user, rh_token):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {rh_token}")
        resp = api_client.post(self.URL, self.NEW_USER, format="json")
        assert resp.status_code == 201

    def test_colaborador_cannot_register_user_returns_403(self, api_client, colaborador_user, colaborador_token):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {colaborador_token}")
        resp = api_client.post(self.URL, self.NEW_USER, format="json")
        assert resp.status_code == 403

    def test_unauthenticated_cannot_register_returns_401(self, api_client):
        resp = api_client.post(self.URL, self.NEW_USER, format="json")
        assert resp.status_code == 401

    def test_register_password_mismatch_returns_400(self, api_client, rh_admin_user, rh_token):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {rh_token}")
        data = {**self.NEW_USER, "password_confirm": "outra_senha"}
        resp = api_client.post(self.URL, data, format="json")
        assert resp.status_code == 400
        assert "password_confirm" in resp.data

    def test_register_duplicate_email_returns_400(self, api_client, rh_admin_user, rh_token):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {rh_token}")
        api_client.post(self.URL, self.NEW_USER, format="json")  # primeiro cadastro
        resp = api_client.post(self.URL, self.NEW_USER, format="json")  # duplicado
        assert resp.status_code == 400

    def test_register_rejects_sector_from_another_company(self, api_client, rh_admin_user, rh_token):
        """Multi-tenant: RH não pode vincular colaborador a um setor de outra empresa."""
        from apps.companies.models import Company
        from apps.sectors.models import Sector

        other_company = Company.objects.create(name="Outra Empresa")
        foreign_sector = Sector.objects.create(name="Setor Estranho", company=other_company)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {rh_token}")
        data = {**self.NEW_USER, "sector": foreign_sector.id}
        resp = api_client.post(self.URL, data, format="json")
        assert resp.status_code == 400
        assert "sector" in resp.data

    def test_register_rejects_position_from_another_company(self, api_client, rh_admin_user, rh_token):
        from apps.companies.models import Company
        from apps.sectors.models import Position, Sector

        other_company = Company.objects.create(name="Outra Empresa 2")
        foreign_sector = Sector.objects.create(name="Setor Estranho 2", company=other_company)
        foreign_position = Position.objects.create(name="Cargo Estranho", sector=foreign_sector)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {rh_token}")
        data = {**self.NEW_USER, "position": foreign_position.id}
        resp = api_client.post(self.URL, data, format="json")
        assert resp.status_code == 400
        assert "position" in resp.data


# ── Testes do model User ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserModel:
    def test_is_rh_admin_property(self, rh_admin_user):
        assert rh_admin_user.is_rh_admin is True

    def test_is_rh_admin_false_for_colaborador(self, colaborador_user):
        assert colaborador_user.is_rh_admin is False

    def test_str_representation(self, colaborador_user):
        assert "João Silva" in str(colaborador_user)
        assert "colaborador@example.com" in str(colaborador_user)

    def test_create_superuser_sets_rh_admin_role(self, django_user_model):
        superuser = django_user_model.objects.create_superuser(
            email="super@example.com",
            full_name="Super",
            password="super@123",
        )
        assert superuser.role == "rh_admin"
        assert superuser.is_staff is True
        assert superuser.is_superuser is True
