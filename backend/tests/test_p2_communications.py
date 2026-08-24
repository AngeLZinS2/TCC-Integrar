import pytest
from apps.communications.models import Announcement, AnnouncementRead
from apps.companies.models import Company

pytestmark = pytest.mark.django_db

def test_rh_cria_comunicado(api_client, rh_admin_user, company):
    api_client.force_authenticate(user=rh_admin_user)
    
    payload = {
        "title": "Aviso Importante",
        "content": "Amanhã não haverá expediente.",
        "is_urgent": True
    }
    
    response = api_client.post("/api/v1/communications/", payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Aviso Importante"
    assert data["is_urgent"] == True
    
    ann = Announcement.objects.get(id=data["id"])
    assert ann.author == rh_admin_user
    assert ann.company == company

def test_colaborador_nao_cria_comunicado(api_client, colaborador_user):
    api_client.force_authenticate(user=colaborador_user)
    
    payload = {
        "title": "Hack",
        "content": "Tentando criar aviso."
    }
    
    response = api_client.post("/api/v1/communications/", payload)
    assert response.status_code == 403

def test_colaborador_ve_comunicado_global(api_client, rh_admin_user, colaborador_user, company):
    Announcement.objects.create(
            status=Announcement.Status.PUBLISHED,company=company, author=rh_admin_user, title="Global")
    
    api_client.force_authenticate(user=colaborador_user)
    response = api_client.get("/api/v1/communications/")
    
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["title"] == "Global"
    
def test_colaborador_ve_comunicado_segmentado(api_client, rh_admin_user, django_user_model, company):
    from apps.sectors.models import Sector
    
    sector_ti = Sector.objects.create(company=company, name="TI")
    sector_rh = Sector.objects.create(company=company, name="RH")
    
    colab_ti = django_user_model.objects.create_user(email="ti@x.com", full_name="TI", password="x", company=company, sector=sector_ti)
    colab_rh = django_user_model.objects.create_user(email="rh2@x.com", full_name="RH", password="x", company=company, sector=sector_rh)
    
    ann = Announcement.objects.create(
            status=Announcement.Status.PUBLISHED,company=company, author=rh_admin_user, title="Aviso TI")
    ann.target_sectors.add(sector_ti)
    
    api_client.force_authenticate(user=colab_ti)
    resp_ti = api_client.get("/api/v1/communications/")
    assert resp_ti.json()["count"] == 1
    
    api_client.force_authenticate(user=colab_rh)
    resp_rh = api_client.get("/api/v1/communications/")
    assert resp_rh.json()["count"] == 0

def test_marcar_como_lido(api_client, rh_admin_user, colaborador_user, company):
    ann = Announcement.objects.create(
            status=Announcement.Status.PUBLISHED,company=company, author=rh_admin_user, title="Leitura Obrigatória")
    
    api_client.force_authenticate(user=colaborador_user)
    response = api_client.post(f"/api/v1/communications/{ann.id}/read/")
    assert response.status_code == 200
    
    read_exists = AnnouncementRead.objects.filter(announcement=ann, user=colaborador_user).exists()
    assert read_exists == True
    
    # Check if get includes is_read = True
    response_get = api_client.get("/api/v1/communications/")
    assert response_get.json()["results"][0]["is_read"] == True

def test_isolamento_multi_tenant_comunicados(api_client, django_user_model, rh_admin_user, company):
    company_b = Company.objects.create(name="Empresa B")
    rh_b = django_user_model.objects.create_user(email="rh_b@x.com", full_name="RH B", password="x", role="rh_admin", company=company_b)
    
    Announcement.objects.create(
            status=Announcement.Status.PUBLISHED,company=company_b, author=rh_b, title="Empresa B Only")
    Announcement.objects.create(
            status=Announcement.Status.PUBLISHED,company=company, author=rh_admin_user, title="Empresa A")
    
    api_client.force_authenticate(user=rh_admin_user)
    response = api_client.get("/api/v1/communications/")
    
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["title"] == "Empresa A"
