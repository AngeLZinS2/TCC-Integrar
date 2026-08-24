import pytest
from apps.materials.models import Material
from apps.sectors.models import Sector


@pytest.fixture
def sector_ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def sector_rh(db, company):
    return Sector.objects.create(name="RH", company=company)


@pytest.fixture
def mat_geral(db, company):
    return Material.objects.create(
        title="Manual do Colaborador", file_url="https://example.com/manual.pdf", sector=None, company=company
    )


@pytest.fixture
def mat_ti(db, company, sector_ti):
    return Material.objects.create(
        title="Guia de Boas Práticas de Código",
        file_url="https://example.com/clean-code.pdf",
        sector=sector_ti,
        company=company,
    )


@pytest.fixture
def leader_user(db, django_user_model, company, sector_ti):
    return django_user_model.objects.create_user(
        email="leader-mat@example.com",
        full_name="Líder TI",
        password="senha@123",
        role="colaborador",
        company=company,
        sector=sector_ti,
        is_sector_leader=True,
    )


@pytest.mark.django_db
class TestMaterials:
    def test_list_materials_for_colaborador(self, api_client, colaborador_user, sector_ti, mat_geral, mat_ti):
        colaborador_user.sector = sector_ti
        colaborador_user.save()

        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get("/api/v1/materials/")
        assert response.status_code == 200
        titles = [m["title"] for m in response.data["results"]]
        assert "Manual do Colaborador" in titles
        assert "Guia de Boas Práticas de Código" in titles

    def test_invalid_sector_filter_returns_400_not_500(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.get("/api/v1/materials/?sector=abc")
        assert response.status_code == 400


@pytest.mark.django_db
class TestSectorLeaderMaterialCreation:
    def test_leader_creates_material_in_own_sector(self, api_client, leader_user, sector_ti):
        api_client.force_authenticate(user=leader_user)
        response = api_client.post(
            "/api/v1/materials/",
            {"title": "Material TI", "file_url": "https://example.com/a.pdf", "sector": sector_ti.id},
        )
        assert response.status_code == 201

    def test_leader_cannot_create_material_in_other_sector(self, api_client, leader_user, sector_rh):
        api_client.force_authenticate(user=leader_user)
        response = api_client.post(
            "/api/v1/materials/",
            {"title": "Material RH", "file_url": "https://example.com/b.pdf", "sector": sector_rh.id},
        )
        assert response.status_code == 400

    def test_leader_cannot_create_general_material(self, api_client, leader_user):
        api_client.force_authenticate(user=leader_user)
        response = api_client.post(
            "/api/v1/materials/",
            {"title": "Material Geral", "file_url": "https://example.com/c.pdf"},
        )
        assert response.status_code == 400

    def test_rh_admin_still_creates_any_material(self, api_client, rh_admin_user, sector_ti):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(
            "/api/v1/materials/",
            {"title": "Material RH-admin", "file_url": "https://example.com/d.pdf", "sector": sector_ti.id},
        )
        assert response.status_code == 201

    def test_rh_admin_creates_general_material(self, api_client, rh_admin_user):
        api_client.force_authenticate(user=rh_admin_user)
        response = api_client.post(
            "/api/v1/materials/",
            {"title": "Material Geral RH", "file_url": "https://example.com/e.pdf"},
        )
        assert response.status_code == 201

    def test_colaborador_without_flag_forbidden(self, api_client, colaborador_user):
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.post(
            "/api/v1/materials/",
            {"title": "Material Negado", "file_url": "https://example.com/f.pdf"},
        )
        assert response.status_code == 403

    def test_leader_cannot_edit_material_of_other_sector(self, api_client, leader_user, company, sector_rh):
        material = Material.objects.create(
            title="Material RH existente", file_url="https://example.com/g.pdf", sector=sector_rh, company=company
        )
        api_client.force_authenticate(user=leader_user)
        response = api_client.patch(f"/api/v1/materials/{material.id}/", {"title": "Editado"})
        assert response.status_code in (403, 404)
