import pytest
from django.utils import timezone
from datetime import timedelta
from apps.events.models import Event

pytestmark = pytest.mark.django_db

def test_listar_eventos(api_client, rh_admin_user, company):
    # Event today
    Event.objects.create(title="Festa", start_at=timezone.now() + timedelta(hours=2),
                         company=company, organizer=rh_admin_user)
    # Event past
    Event.objects.create(title="Passado", start_at=timezone.now() - timedelta(days=10),
                         company=company, organizer=rh_admin_user)
    
    api_client.force_authenticate(user=rh_admin_user)
    resp = api_client.get("/api/v1/events/")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["results"][0]["title"] == "Festa"

def test_criar_evento_rh(api_client, rh_admin_user):
    api_client.force_authenticate(user=rh_admin_user)
    resp = api_client.post("/api/v1/events/", {
        "title": "Confraternização",
        "start_at": (timezone.now() + timedelta(days=5)).isoformat(),
        "description": "Festa da firma"
    })
    assert resp.status_code == 201
    assert Event.objects.filter(title="Confraternização").exists()

def test_criar_evento_colaborador_rejeitado(api_client, colaborador_user):
    api_client.force_authenticate(user=colaborador_user)
    resp = api_client.post("/api/v1/events/", {
        "title": "Hack",
        "start_at": (timezone.now() + timedelta(days=1)).isoformat(),
    })
    assert resp.status_code == 403

def test_listar_aniversariantes(api_client, rh_admin_user, django_user_model, company):
    today = timezone.now().date()
    
    # Aniversariante amanhã
    bday_tomorrow = today + timedelta(days=1)
    django_user_model.objects.create_user(
        email="niver@x.com", full_name="Aniversariante", password="x", 
        company=company, birth_date=bday_tomorrow.replace(year=1990)
    )
    
    # Não aniversariante (daqui a 3 meses)
    bday_far = today + timedelta(days=90)
    django_user_model.objects.create_user(
        email="longe@x.com", full_name="Longe", password="x", 
        company=company, birth_date=bday_far.replace(year=1990)
    )
    
    api_client.force_authenticate(user=rh_admin_user)
    resp = api_client.get("/api/v1/events/birthdays/")
    
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["full_name"] == "Aniversariante"
