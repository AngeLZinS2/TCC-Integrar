import pytest
from apps.sectors.models import Sector


@pytest.fixture
def sector_ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.mark.django_db
class TestCompanyDirectory:
    URL = "/api/v1/auth/directory/"

    def test_colaborador_can_see_directory(self, api_client, colaborador_user, rh_admin_user):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get(self.URL)
        assert response.status_code == 200
        emails = [u["email"] for u in response.data]
        assert colaborador_user.email in emails
        assert rh_admin_user.email in emails

    def test_rh_admin_can_see_directory(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get(self.URL)
        assert response.status_code == 200

    def test_owner_forbidden(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        response = api_client.get(self.URL)
        assert response.status_code == 200
        assert response.data == []

    def test_directory_scoped_to_own_company(
        self, api_client, colaborador_user, django_user_model
    ):
        from apps.companies.models import Company

        other_company = Company.objects.create(name="Empresa Diretorio")
        other_user = django_user_model.objects.create_user(
            email="outro_dir@example.com",
            full_name="Outro Colaborador",
            password="senha@123",
            role="colaborador",
            company=other_company,
        )

        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get(self.URL)
        emails = [u["email"] for u in response.data]
        assert other_user.email not in emails

    def test_inactive_users_excluded(self, api_client, colaborador_user, rh_admin_user):
        colaborador_user.is_active = False
        colaborador_user.save()

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get(self.URL)
        emails = [u["email"] for u in response.data]
        assert colaborador_user.email not in emails

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401
