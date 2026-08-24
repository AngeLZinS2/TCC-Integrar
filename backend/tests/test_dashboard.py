import datetime

import pytest
from apps.checklist.models import ChecklistItem
from apps.courses.models import Course, CourseProgress
from apps.sectors.models import Sector


@pytest.fixture
def sector_ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def sector_rh(db, company):
    return Sector.objects.create(name="RH", company=company)


@pytest.fixture
def course_geral(db, company):
    return Course.objects.create(title="Boas-vindas", sector=None, order=1, company=company)


@pytest.fixture
def course_ti(db, company, sector_ti):
    return Course.objects.create(title="Curso TI", sector=sector_ti, order=2, company=company)


@pytest.fixture
def checklist_geral(db, company):
    return ChecklistItem.objects.create(title="NDA", deadline="day1", sector=None, order=1, company=company)


@pytest.mark.django_db
class TestDashboardPermissions:
    def test_colaborador_forbidden_on_all_endpoints(self, api_client, colaborador_user):
        api_client.force_authenticate(user=colaborador_user)
        urls = [
            "/api/v1/dashboard/overview/",
            "/api/v1/dashboard/collaborators/",
            f"/api/v1/dashboard/collaborators/{colaborador_user.id}/",
        ]
        for url in urls:
            response = api_client.get(url)
            assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get("/api/v1/dashboard/overview/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestCollaboratorsList:
    def test_stats_math_is_correct(
        self, api_client, rh_admin_user, colaborador_user, sector_ti, course_geral, course_ti, checklist_geral
    ):
        colaborador_user.sector = sector_ti
        colaborador_user.save()
        CourseProgress.objects.create(user=colaborador_user, course=course_geral, status="completed")
        # course_ti fica implicitamente "não iniciado" (sem registro de progresso)

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/collaborators/")
        assert response.status_code == 200

        row = next(r for r in response.data if r["id"] == colaborador_user.id)
        assert row["courses_total"] == 2
        assert row["courses_completed"] == 1
        assert row["courses_percent"] == 50
        assert row["checklist_total"] == 1
        assert row["checklist_completed"] == 0
        assert row["checklist_percent"] == 0
        assert row["overall_percent"] == 25

    def test_zero_eligible_items_yields_100_percent(self, api_client, rh_admin_user, colaborador_user, sector_rh):
        colaborador_user.sector = sector_rh
        colaborador_user.save()

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/collaborators/")
        assert response.status_code == 200

        row = next(r for r in response.data if r["id"] == colaborador_user.id)
        assert row["courses_total"] == 0
        assert row["courses_percent"] == 100
        assert row["checklist_total"] == 0
        assert row["checklist_percent"] == 100
        assert row["overall_percent"] == 100

    def test_search_filters_by_name(self, api_client, rh_admin_user, colaborador_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/collaborators/?search=inexistente")
        assert response.status_code == 200
        assert response.data == []

    def test_invalid_sector_filter_returns_400_not_500(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/collaborators/?sector=abc")
        assert response.status_code == 400


@pytest.mark.django_db
class TestCollaboratorDetail:
    def test_only_eligible_courses_are_shown(
        self, api_client, rh_admin_user, colaborador_user, company, sector_ti, sector_rh, course_geral, course_ti
    ):
        colaborador_user.sector = sector_ti
        colaborador_user.save()
        Course.objects.create(title="Curso RH", sector=sector_rh, order=3, company=company)

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get(f"/api/v1/dashboard/collaborators/{colaborador_user.id}/")
        assert response.status_code == 200

        titles = [c["title"] for c in response.data["courses"]]
        assert "Curso RH" not in titles
        assert "Curso TI" in titles
        assert "Boas-vindas" in titles

    def test_404_for_nonexistent_collaborator(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/collaborators/999999/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestDashboardOverview:
    def test_overview_aggregates(
        self, api_client, rh_admin_user, colaborador_user, sector_ti, course_geral, course_ti
    ):
        colaborador_user.sector = sector_ti
        colaborador_user.save()
        CourseProgress.objects.create(user=colaborador_user, course=course_geral, status="completed")

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/overview/")
        assert response.status_code == 200

        assert response.data["total_collaborators"] == 1
        assert response.data["never_logged_in"] == 1
        assert response.data["avg_course_completion_percent"] == 50.0
        assert response.data["course_status_distribution"]["completed"] == 1
        assert response.data["course_status_distribution"]["not_started"] == 1

        sector_row = next(s for s in response.data["by_sector"] if s["sector_name"] == "TI")
        assert sector_row["collaborators"] == 1
        assert sector_row["avg_course_percent"] == 50.0


@pytest.mark.django_db
class TestCollaboratorsExport:
    def test_rh_can_export_csv(self, api_client, rh_admin_user, colaborador_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/collaborators/export/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        content = response.content.decode("utf-8")
        assert "Nome" in content.splitlines()[0]
        assert colaborador_user.full_name in content

    def test_colaborador_forbidden_from_export(self, api_client, colaborador_user):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get("/api/v1/dashboard/collaborators/export/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestOverdueCalculation:
    def test_collaborator_hired_long_ago_is_overdue(
        self, api_client, rh_admin_user, colaborador_user, checklist_geral
    ):
        colaborador_user.hire_date = datetime.date.today() - datetime.timedelta(days=30)
        colaborador_user.save()
        # checklist_geral tem deadline="day1" (vence 1 dia após a contratação) e não foi concluído

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/collaborators/")
        assert response.status_code == 200

        row = next(r for r in response.data if r["id"] == colaborador_user.id)
        assert row["overdue_count"] == 1

        detail = api_client.get(f"/api/v1/dashboard/collaborators/{colaborador_user.id}/")
        item = next(i for i in detail.data["checklist_items"] if i["id"] == checklist_geral.id)
        assert item["is_overdue"] is True
        assert item["due_date"] == str(colaborador_user.hire_date + datetime.timedelta(days=1))

        overview = api_client.get("/api/v1/dashboard/overview/")
        assert overview.data["overdue_collaborators_count"] == 1

    def test_collaborator_hired_today_is_not_overdue(
        self, api_client, rh_admin_user, colaborador_user, checklist_geral
    ):
        colaborador_user.hire_date = datetime.date.today()
        colaborador_user.save()

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/collaborators/")
        row = next(r for r in response.data if r["id"] == colaborador_user.id)
        assert row["overdue_count"] == 0

    def test_completed_item_is_never_overdue(
        self, api_client, rh_admin_user, colaborador_user, checklist_geral
    ):
        from apps.checklist.models import ChecklistProgress

        colaborador_user.hire_date = datetime.date.today() - datetime.timedelta(days=30)
        colaborador_user.save()
        ChecklistProgress.objects.create(user=colaborador_user, item=checklist_geral, completed=True)

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/collaborators/")
        row = next(r for r in response.data if r["id"] == colaborador_user.id)
        assert row["overdue_count"] == 0

    def test_no_hire_date_is_never_overdue(self, api_client, rh_admin_user, colaborador_user, checklist_geral):
        assert colaborador_user.hire_date is None

        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/dashboard/collaborators/")
        row = next(r for r in response.data if r["id"] == colaborador_user.id)
        assert row["overdue_count"] == 0
