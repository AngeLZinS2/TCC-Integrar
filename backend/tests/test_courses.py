import pytest
from apps.courses.models import Content, Course, CourseProgress
from apps.sectors.models import Sector


@pytest.fixture
def sector_ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def sector_rh(db, company):
    return Sector.objects.create(name="RH", company=company)


@pytest.fixture
def course_geral(db, company):
    return Course.objects.create(
        title="Boas-vindas à Empresa", description="Visão geral", sector=None, order=1, company=company
    )


@pytest.fixture
def course_ti(db, company, sector_ti):
    c = Course.objects.create(
        title="Arquitetura de Software", description="Stack e padrões", sector=sector_ti, order=2, company=company
    )
    Content.objects.create(course=c, type="video", file_url="https://example.com/video1.mp4", order=1)
    return c


@pytest.fixture
def course_rh(db, company, sector_rh):
    return Course.objects.create(title="Processos de Departamento Pessoal", sector=sector_rh, order=3, company=company)


@pytest.mark.django_db
class TestCourses:
    def test_colaborador_sees_general_and_own_sector_courses(
        self, api_client, colaborador_user, sector_ti, course_geral, course_ti, course_rh
    ):
        colaborador_user.sector = sector_ti
        colaborador_user.save()

        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get("/api/v1/courses/")
        assert response.status_code == 200

        titles = [c["title"] for c in response.data["results"]]
        assert "Boas-vindas à Empresa" in titles
        assert "Arquitetura de Software" in titles
        assert "Processos de Departamento Pessoal" not in titles

    def test_rh_admin_sees_all_courses(
        self, api_client, rh_admin_user, course_geral, course_ti, course_rh
    ):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/courses/")
        assert response.status_code == 200
        titles = [c["title"] for c in response.data["results"]]
        assert len(titles) == 3

    def test_course_detail_includes_contents(self, api_client, colaborador_user, sector_ti, course_ti):
        colaborador_user.sector = sector_ti
        colaborador_user.save()
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get(f"/api/v1/courses/{course_ti.id}/")
        assert response.status_code == 200
        assert len(response.data["contents"]) == 1
        assert response.data["contents"][0]["type"] == "video"

    def test_update_course_progress(self, api_client, colaborador_user, sector_ti, course_ti):
        colaborador_user.sector = sector_ti
        colaborador_user.save()
        api_client.force_authenticate(user=colaborador_user)
        # Patch progress
        response = api_client.patch(
            f"/api/v1/courses/{course_ti.id}/progress/",
            {"status": "completed"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "completed"
        assert response.data["completed_at"] is not None

        # Verify CourseProgress in DB
        progress = CourseProgress.objects.get(user=colaborador_user, course=course_ti)
        assert progress.status == "completed"

    def test_invalid_sector_filter_returns_400_not_500(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/courses/?sector=abc")
        assert response.status_code == 400

    def test_invalid_position_filter_returns_400_not_500(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/courses/?position=abc")
        assert response.status_code == 400
