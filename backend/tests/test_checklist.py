import pytest
from apps.checklist.models import ChecklistItem, ChecklistProgress
from apps.sectors.models import Sector


@pytest.fixture
def sector_ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def item_geral(db, company):
    return ChecklistItem.objects.create(
        title="Assinar contrato e entregar documentos", deadline="day1", sector=None, company=company
    )


@pytest.fixture
def item_ti(db, company, sector_ti):
    return ChecklistItem.objects.create(
        title="Configurar ambiente de desenvolvimento", deadline="day1", sector=sector_ti, company=company
    )


@pytest.mark.django_db
class TestChecklist:
    def test_colaborador_sees_general_and_sector_items(self, api_client, colaborador_user, sector_ti, item_geral, item_ti):
        colaborador_user.sector = sector_ti
        colaborador_user.save()

        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get("/api/v1/checklist/")
        assert response.status_code == 200
        titles = [i["title"] for i in response.data["results"]]
        assert "Assinar contrato e entregar documentos" in titles
        assert "Configurar ambiente de desenvolvimento" in titles

    def test_toggle_checklist_progress(self, api_client, colaborador_user, item_geral):
        api_client.force_authenticate(user=colaborador_user)
        # Toggle on
        response = api_client.post(f"/api/v1/checklist/{item_geral.id}/toggle/")
        assert response.status_code == 200
        assert response.data["completed"] is True
        assert response.data["completed_at"] is not None

        # Toggle off
        response = api_client.post(f"/api/v1/checklist/{item_geral.id}/toggle/")
        assert response.status_code == 200
        assert response.data["completed"] is False
        assert response.data["completed_at"] is None

    def test_invalid_sector_filter_returns_400_not_500(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/checklist/?sector=abc")
        assert response.status_code == 400
