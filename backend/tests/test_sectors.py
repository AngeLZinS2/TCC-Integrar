import pytest
from apps.sectors.models import Position, Sector


@pytest.fixture
def sector_ti(db, company):
    return Sector.objects.create(name="Tecnologia da Informação", description="Setor de TI", company=company)


@pytest.fixture
def position_dev(db, sector_ti):
    return Position.objects.create(name="Desenvolvedor Júnior", sector=sector_ti)


@pytest.mark.django_db
class TestSectors:
    def test_list_sectors_authenticated(self, api_client, colaborador_user, sector_ti):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get("/api/v1/sectors/")
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1
        assert response.data["results"][0]["name"] == "Tecnologia da Informação"

    def test_rh_can_create_sector(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(
            "/api/v1/sectors/",
            {"name": "Recursos Humanos", "description": "Setor de RH"},
            format="json",
        )
        assert response.status_code == 201
        assert Sector.objects.filter(name="Recursos Humanos").exists()

    def test_colaborador_cannot_create_sector(self, api_client, colaborador_user):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.post(
            "/api/v1/sectors/",
            {"name": "Financeiro", "description": "Setor Financeiro"},
            format="json",
        )
        assert response.status_code == 403

    def test_list_positions_by_sector(self, api_client, colaborador_user, sector_ti, position_dev):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get(f"/api/v1/sectors/{sector_ti.id}/positions/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Desenvolvedor Júnior"

    def test_invalid_sector_filter_on_positions_returns_400_not_500(self, api_client, colaborador_user):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get("/api/v1/sectors/positions/?sector=abc")
        assert response.status_code == 400
