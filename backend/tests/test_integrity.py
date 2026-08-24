import pytest
from apps.courses.models import Course, CourseProgress
from apps.sectors.models import Sector


@pytest.fixture
def sector_ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def course_a(db, company):
    return Course.objects.create(title="Curso A", company=company, order=1)


@pytest.fixture
def course_b(db, company, course_a):
    return Course.objects.create(title="Curso B", company=company, order=2, prerequisite=course_a)


@pytest.mark.django_db
class TestSectorDeletionGuard:
    def test_cannot_delete_sector_with_collaborators(self, api_client, rh_admin_user, colaborador_user, sector_ti):
        colaborador_user.sector = sector_ti
        colaborador_user.save()

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.delete(f"/api/v1/sectors/{sector_ti.id}/")
        assert response.status_code == 400
        assert Sector.objects.filter(id=sector_ti.id).exists()

    def test_can_delete_empty_sector(self, api_client, rh_admin_user, sector_ti):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.delete(f"/api/v1/sectors/{sector_ti.id}/")
        assert response.status_code == 204
        assert not Sector.objects.filter(id=sector_ti.id).exists()


@pytest.mark.django_db
class TestCourseDeletionGuard:
    def test_cannot_delete_course_with_progress(self, api_client, rh_admin_user, colaborador_user, course_a):
        CourseProgress.objects.create(user=colaborador_user, course=course_a, status="in_progress")

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.delete(f"/api/v1/courses/{course_a.id}/")
        assert response.status_code == 400
        assert Course.objects.filter(id=course_a.id).exists()

    def test_can_delete_course_without_progress(self, api_client, rh_admin_user, course_a):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.delete(f"/api/v1/courses/{course_a.id}/")
        assert response.status_code == 204


@pytest.mark.django_db
class TestToggleColaboradorActive:
    def test_rh_can_deactivate_colaborador(self, api_client, rh_admin_user, colaborador_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(f"/api/v1/auth/colaboradores/{colaborador_user.id}/toggle-active/")
        assert response.status_code == 200
        assert response.data["id"] == colaborador_user.id
        colaborador_user.refresh_from_db()
        assert colaborador_user.is_active is False

    def test_cannot_deactivate_last_rh_admin(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(f"/api/v1/auth/colaboradores/{rh_admin_user.id}/toggle-active/")
        assert response.status_code == 400
        rh_admin_user.refresh_from_db()
        assert rh_admin_user.is_active is True

    def test_can_deactivate_rh_admin_when_another_is_active(
        self, api_client, rh_admin_user, company, django_user_model
    ):
        other_rh = django_user_model.objects.create_user(
            email="rh2@example.com", full_name="Outro RH", password="senha@123", role="rh_admin", company=company
        )
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(f"/api/v1/auth/colaboradores/{rh_admin_user.id}/toggle-active/")
        assert response.status_code == 200
        assert other_rh.is_active is True

    def test_cannot_toggle_user_from_another_company(self, api_client, rh_admin_user, django_user_model):
        from apps.companies.models import Company

        other_company = Company.objects.create(name="Outra Empresa")
        other_user = django_user_model.objects.create_user(
            email="outro@example.com",
            full_name="Outro",
            password="senha@123",
            role="colaborador",
            company=other_company,
        )
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(f"/api/v1/auth/colaboradores/{other_user.id}/toggle-active/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestCoursePrerequisite:
    def test_locked_course_cannot_be_started(self, api_client, colaborador_user, course_b):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.patch(f"/api/v1/courses/{course_b.id}/progress/", {"status": "in_progress"}, format="json")
        assert response.status_code == 400

    def test_course_unlocks_after_prerequisite_completed(
        self, api_client, colaborador_user, course_a, course_b
    ):
        CourseProgress.objects.create(user=colaborador_user, course=course_a, status="completed")

        api_client.force_authenticate(user=colaborador_user)
        response = api_client.patch(f"/api/v1/courses/{course_b.id}/progress/", {"status": "in_progress"}, format="json")
        assert response.status_code == 200

    def test_is_locked_field_reflects_prerequisite_state(self, api_client, colaborador_user, course_a, course_b):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get(f"/api/v1/courses/{course_b.id}/")
        assert response.data["is_locked"] is True

        CourseProgress.objects.create(user=colaborador_user, course=course_a, status="completed")
        response = api_client.get(f"/api/v1/courses/{course_b.id}/")
        assert response.data["is_locked"] is False

    def test_cannot_set_course_as_own_prerequisite(self, api_client, rh_admin_user, course_a):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.patch(
            f"/api/v1/courses/{course_a.id}/", {"prerequisite": course_a.id}, format="json"
        )
        assert response.status_code == 400

    def test_cannot_create_prerequisite_cycle(self, api_client, rh_admin_user, course_a, course_b):
        api_client.force_authenticate(user=rh_admin_user)
        # course_b já tem course_a como pré-requisito; tentar o inverso deve falhar
        response = api_client.patch(
            f"/api/v1/courses/{course_a.id}/", {"prerequisite": course_b.id}, format="json"
        )
        assert response.status_code == 400

    def test_prerequisite_must_belong_to_same_company(self, api_client, rh_admin_user, course_a):
        from apps.companies.models import Company

        other_company = Company.objects.create(name="Outra Empresa 2")
        other_course = Course.objects.create(title="Curso Externo", company=other_company, order=1)

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.patch(
            f"/api/v1/courses/{course_a.id}/", {"prerequisite": other_course.id}, format="json"
        )
        assert response.status_code == 400
