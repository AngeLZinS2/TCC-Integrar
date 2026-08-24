import pytest
from apps.requests.models import HRRequest, RequestHistory, RequestComment
from apps.companies.models import Company

pytestmark = pytest.mark.django_db

def test_colaborador_cria_solicitacao(api_client, colaborador_user):
    api_client.force_authenticate(user=colaborador_user)
    
    payload = {
        "category": "benefits",
        "subject": "Dúvida sobre Vale Refeição",
        "description": "Gostaria de saber como altero o benefício.",
        "priority": "normal"
    }
    
    response = api_client.post("/api/v1/requests/", payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["subject"] == "Dúvida sobre Vale Refeição"
    assert data["status"] == "received"
    assert "SOL-" in data["number"]
    
    # Check history
    history = RequestHistory.objects.filter(request_id=data["id"]).first()
    assert history.action_type == "created"
    assert history.actor == colaborador_user

def test_colaborador_lista_apenas_suas_solicitacoes(api_client, django_user_model, company, colaborador_user):
    colab2 = django_user_model.objects.create_user(
        email="colab2@example.com", full_name="Colab 2", password="x", role="colaborador", company=company
    )
    
    # colab1 creates 1
    HRRequest.objects.create(company=company, requester=colaborador_user, subject="Req 1")
    # colab2 creates 1
    HRRequest.objects.create(company=company, requester=colab2, subject="Req 2")
    
    api_client.force_authenticate(user=colaborador_user)
    response = api_client.get("/api/v1/requests/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["results"][0]["subject"] == "Req 1"

def test_rh_lista_todas_solicitacoes_da_empresa(api_client, rh_admin_user, django_user_model, company):
    colab1 = django_user_model.objects.create_user(email="c1@x.com", full_name="C1", password="x", role="colaborador", company=company)
    colab2 = django_user_model.objects.create_user(email="c2@x.com", full_name="C2", password="x", role="colaborador", company=company)
    
    HRRequest.objects.create(company=company, requester=colab1, subject="Req 1")
    HRRequest.objects.create(company=company, requester=colab2, subject="Req 2")
    
    api_client.force_authenticate(user=rh_admin_user)
    response = api_client.get("/api/v1/requests/")
    
    assert response.status_code == 200
    assert response.json()["count"] == 2

def test_rh_altera_status_e_gera_historico(api_client, rh_admin_user, colaborador_user, company):
    req = HRRequest.objects.create(company=company, requester=colaborador_user, subject="Req")
    
    api_client.force_authenticate(user=rh_admin_user)
    response = api_client.patch(f"/api/v1/requests/{req.id}/status/", {"status": "in_progress"})
    
    assert response.status_code == 200
    req.refresh_from_db()
    assert req.status == "in_progress"
    
    history = RequestHistory.objects.filter(request=req).last()
    assert history.action_type == "status_changed"
    assert history.actor == rh_admin_user

def test_isolamento_multi_tenant_requests(api_client, django_user_model, rh_admin_user):
    company_b = Company.objects.create(name="Empresa B")
    rh_b = django_user_model.objects.create_user(email="rh_b@x.com", full_name="RH B", password="x", role="rh_admin", company=company_b)
    
    req_b = HRRequest.objects.create(company=company_b, requester=rh_b, subject="Req B")
    
    api_client.force_authenticate(user=rh_admin_user)
    # RH of company A tries to get request of company B
    response = api_client.get(f"/api/v1/requests/{req_b.id}/")
    
    assert response.status_code == 404

def test_criar_comentario(api_client, colaborador_user, company):
    req = HRRequest.objects.create(company=company, requester=colaborador_user, subject="Req")
    
    api_client.force_authenticate(user=colaborador_user)
    response = api_client.post(f"/api/v1/requests/{req.id}/comments/", {"text": "Novo comentário"})
    
    assert response.status_code == 201
    
    comment = RequestComment.objects.filter(request=req).first()
    assert comment.text == "Novo comentário"
    
    history = RequestHistory.objects.filter(request=req).first()
    assert history.action_type == "commented"
