import pytest
from apps.courses.models import Course
from apps.sectors.models import Sector


@pytest.fixture
def sector_ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def sector_rh(db, company):
    return Sector.objects.create(name="RH", company=company)


@pytest.fixture
def leader_user(db, django_user_model, company, sector_ti):
    return django_user_model.objects.create_user(
        email="leader@example.com",
        full_name="Líder TI",
        password="senha@123",
        role="colaborador",
        company=company,
        sector=sector_ti,
        is_sector_leader=True,
    )


@pytest.mark.django_db
class TestSectorLeaderCourseCreation:
    def test_leader_creates_course_in_own_sector(self, api_client, leader_user, sector_ti):
        api_client.force_authenticate(user=leader_user)
        response = api_client.post(
            "/api/v1/courses/",
            {"title": "Treinamento TI", "sector": sector_ti.id, "order": 1},
        )
        assert response.status_code == 201

    def test_leader_cannot_create_course_in_other_sector(self, api_client, leader_user, sector_rh):
        api_client.force_authenticate(user=leader_user)
        response = api_client.post(
            "/api/v1/courses/",
            {"title": "Treinamento RH", "sector": sector_rh.id, "order": 1},
        )
        assert response.status_code == 400

    def test_leader_cannot_create_general_course(self, api_client, leader_user):
        api_client.force_authenticate(user=leader_user)
        response = api_client.post(
            "/api/v1/courses/",
            {"title": "Treinamento Geral", "order": 1},
        )
        assert response.status_code == 400

    def test_rh_admin_still_creates_any_course(self, api_client, rh_admin_user, sector_ti):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(
            "/api/v1/courses/",
            {"title": "Treinamento RH-admin", "sector": sector_ti.id, "order": 1},
        )
        assert response.status_code == 201

    def test_colaborador_without_flag_forbidden(self, api_client, colaborador_user):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.post(
            "/api/v1/courses/",
            {"title": "Treinamento Negado", "order": 1},
        )
        assert response.status_code == 403

    def test_leader_cannot_edit_course_of_other_sector(self, api_client, leader_user, company, sector_rh):
        course = Course.objects.create(title="Curso RH", company=company, sector=sector_rh, order=1)
        api_client.force_authenticate(user=leader_user)
        response = api_client.patch(f"/api/v1/courses/{course.id}/", {"title": "Editado"})
        assert response.status_code in (403, 404)


@pytest.mark.django_db
class TestIsSectorLeaderValidation:
    def test_register_leader_without_sector_rejected(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "novo@example.com",
                "full_name": "Novo Líder",
                "role": "colaborador",
                "is_sector_leader": True,
                "password": "senha@123",
                "password_confirm": "senha@123",
            },
        )
        assert response.status_code == 400

    def test_register_leader_with_sector_succeeds(self, api_client, rh_admin_user, sector_ti):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "novo2@example.com",
                "full_name": "Novo Líder 2",
                "role": "colaborador",
                "sector": sector_ti.id,
                "is_sector_leader": True,
                "password": "senha@123",
                "password_confirm": "senha@123",
            },
        )
        assert response.status_code == 201
        assert response.data["is_sector_leader"] is True

    def test_toggle_sector_leader_requires_sector(self, api_client, rh_admin_user, colaborador_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(
            f"/api/v1/auth/colaboradores/{colaborador_user.id}/toggle-sector-leader/"
        )
        assert response.status_code == 400

    def test_toggle_sector_leader_succeeds_with_sector(self, api_client, rh_admin_user, colaborador_user, sector_ti):
        colaborador_user.sector = sector_ti
        colaborador_user.save()
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(
            f"/api/v1/auth/colaboradores/{colaborador_user.id}/toggle-sector-leader/"
        )
        assert response.status_code == 200
        colaborador_user.refresh_from_db()
        assert colaborador_user.is_sector_leader is True
