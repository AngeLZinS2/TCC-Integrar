import pytest
from apps.companies.models import Company
from apps.courses.models import Course
from apps.sectors.models import Sector


@pytest.fixture
def company_b(db):
    return Company.objects.create(name="Empresa B")


@pytest.fixture
def rh_admin_b(db, django_user_model, company_b):
    return django_user_model.objects.create_user(
        email="rh_b@example.com",
        full_name="RH Admin B",
        password="senha@123",
        role="rh_admin",
        company=company_b,
    )


@pytest.fixture
def sector_b(db, company_b):
    return Sector.objects.create(name="TI", company=company_b)


@pytest.fixture
def course_b(db, company_b):
    return Course.objects.create(title="Curso da Empresa B", company=company_b, order=1)


@pytest.mark.django_db
class TestCompanyAccess:
    URL = "/api/v1/companies/"

    def test_rh_admin_forbidden(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get(self.URL)
        assert response.status_code == 403

    def test_colaborador_forbidden(self, api_client, colaborador_user):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get(self.URL)
        assert response.status_code == 403

    def test_owner_can_list(self, api_client, owner_user, company):
        api_client.force_authenticate(user=owner_user)
        response = api_client.get(self.URL)
        assert response.status_code == 200
        names = [c["name"] for c in response.data]
        assert company.name in names


@pytest.mark.django_db
class TestCompanyExport:
    def test_owner_can_export_csv(self, api_client, owner_user, company):
        api_client.force_authenticate(user=owner_user)
        response = api_client.get("/api/v1/companies/export/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        content = response.content.decode("utf-8")
        assert "Nome" in content.splitlines()[0]
        assert company.name in content

    def test_rh_admin_forbidden_from_export(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/companies/export/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestCompanyBootstrap:
    URL = "/api/v1/companies/"

    def test_owner_creates_company_with_admin(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        response = api_client.post(
            self.URL,
            {
                "name": "Empresa Nova",
                "admin_email": "admin@empresanova.com",
                "admin_full_name": "Admin Nova",
                "admin_password": "senha@123",
            },
            format="json",
        )
        assert response.status_code == 201
        assert Company.objects.filter(name="Empresa Nova").exists()

        new_company = Company.objects.get(name="Empresa Nova")
        admin = new_company.users.get(email="admin@empresanova.com")
        assert admin.role == "rh_admin"
        assert admin.check_password("senha@123")

    def test_duplicate_company_name_rejected(self, api_client, owner_user, company):
        api_client.force_authenticate(user=owner_user)
        response = api_client.post(
            self.URL,
            {
                "name": company.name,
                "admin_email": "outro@example.com",
                "admin_full_name": "Outro Admin",
                "admin_password": "senha@123",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "name" in response.data


@pytest.mark.django_db
class TestInactiveCompanyBlocksLogin:
    def test_login_blocked_for_inactive_company(self, api_client, colaborador_user, company):
        company.is_active = False
        company.save()

        response = api_client.post(
            "/api/v1/auth/token/",
            {"email": "colaborador@example.com", "password": "senha@123"},
            format="json",
        )
        assert response.status_code == 401

    def test_toggle_active_reactivates_login(self, api_client, owner_user, colaborador_user, company):
        company.is_active = False
        company.save()

        api_client.force_authenticate(user=owner_user)
        response = api_client.post(f"/api/v1/companies/{company.id}/toggle-active/")
        assert response.status_code == 200
        assert response.data["is_active"] is True

        response = api_client.post(
            "/api/v1/auth/token/",
            {"email": "colaborador@example.com", "password": "senha@123"},
            format="json",
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestCrossTenantIsolation:
    def test_rh_admin_never_sees_other_company_sectors(
        self, api_client, rh_admin_user, company, sector_b, rh_admin_b
    ):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/sectors/")
        assert response.status_code == 200
        ids = [s["id"] for s in response.data["results"]]
        assert sector_b.id not in ids

    def test_rh_admin_never_sees_other_company_courses(self, api_client, rh_admin_user, course_b):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/courses/")
        assert response.status_code == 200
        ids = [c["id"] for c in response.data["results"]]
        assert course_b.id not in ids

    def test_rh_cannot_register_collaborator_into_other_company(self, api_client, rh_admin_user, company_b):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "novato@example.com",
                "full_name": "Novato",
                "role": "colaborador",
                "company": company_b.id,
                "password": "senha@123",
                "password_confirm": "senha@123",
            },
            format="json",
        )
        assert response.status_code == 201
        from apps.users.models import User

        created = User.objects.get(email="novato@example.com")
        assert created.company_id == rh_admin_user.company_id
        assert created.company_id != company_b.id

    def test_owner_dashboard_scoped_per_company(
        self, api_client, owner_user, rh_admin_user, company, course_geral_stub, company_b, course_b
    ):
        api_client.force_authenticate(user=owner_user)
        response = api_client.get(f"/api/v1/companies/{company.id}/dashboard/")
        assert response.status_code == 200

        response_b = api_client.get(f"/api/v1/companies/{company_b.id}/dashboard/")
        assert response_b.status_code == 200


@pytest.fixture
def course_geral_stub(db, company):
    return Course.objects.create(title="Curso Geral Stub", company=company, order=1)
