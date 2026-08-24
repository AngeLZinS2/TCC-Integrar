"""
Eventos: agenda, RSVP, capacidade, cancelamento e segmentação.
"""

import pytest
from django.utils import timezone

from apps.companies.models import Company
from apps.events.models import Event, EventAttendance
from apps.notifications.models import Notification
from apps.sectors.models import Sector

URL = "/api/v1/events/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


def daqui(**kw):
    return timezone.now() + timezone.timedelta(**kw)


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa B")


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-ag@x.com", "rh_admin", company)


@pytest.fixture
def colab(db, django_user_model, company):
    return mk(django_user_model, "colab-ag@x.com", "colaborador", company)


@pytest.fixture
def rh_b(db, django_user_model, empresa_b):
    return mk(django_user_model, "rh@b-ag.com", "rh_admin", empresa_b)


def criar_evento(company, organizador, **kw):
    dados = {
        "title": "Reunião geral",
        "start_at": daqui(days=3),
        "company": company,
        "organizer": organizador,
    }
    dados.update(kw)
    return Event.objects.create(**dados)


# ══════════════════════════════════════════════════════════════════════════
# Agenda
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAgenda:
    def test_agenda_mostra_so_o_que_vem_pela_frente(self, api_client, company, rh):
        criar_evento(company, rh, title="Futuro")
        criar_evento(company, rh, title="Passado", start_at=daqui(days=-5))

        api_client.force_authenticate(user=rh)
        titulos = [e["title"] for e in api_client.get(URL).data["results"]]
        assert titulos == ["Futuro"]

    def test_historico_atras_de_um_filtro(self, api_client, company, rh):
        criar_evento(company, rh, title="Passado", start_at=daqui(days=-5))

        api_client.force_authenticate(user=rh)
        titulos = [e["title"] for e in api_client.get(URL, {"past": "true"}).data["results"]]
        assert titulos == ["Passado"]

    def test_ordena_por_horario_e_nao_so_por_dia(self, api_client, company, rh):
        """
        O motivo de `start_at` ser datetime: com data pura, dois eventos do
        mesmo dia empatavam e a ordem ficava indefinida.
        """
        criar_evento(company, rh, title="Tarde", start_at=daqui(days=1, hours=8))
        criar_evento(company, rh, title="Manhã", start_at=daqui(days=1, hours=1))

        api_client.force_authenticate(user=rh)
        titulos = [e["title"] for e in api_client.get(URL).data["results"]]
        assert titulos == ["Manhã", "Tarde"]

    def test_termino_antes_do_inicio_e_rejeitado(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            URL,
            {
                "title": "Torto",
                "start_at": daqui(days=2).isoformat(),
                "end_at": daqui(days=1).isoformat(),
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_evento_sem_data_e_rejeitado(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(URL, {"title": "Sem data"}, format="json")
        assert resp.status_code == 400

    def test_colaborador_nao_cria_evento(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        resp = api_client.post(
            URL, {"title": "Hack", "start_at": daqui(days=1).isoformat()}, format="json"
        )
        assert resp.status_code == 403

    def test_colaborador_sem_permissao_recebe_403_e_nao_400(self, api_client, colab):
        """Quem não pode criar não deve descobrir o formato esperado."""
        api_client.force_authenticate(user=colab)
        assert api_client.post(URL, {}, format="json").status_code == 403

    def test_listagem_e_paginada(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        resp = api_client.get(URL)
        assert "count" in resp.data and "results" in resp.data


# ══════════════════════════════════════════════════════════════════════════
# RSVP
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestRSVP:
    def test_confirma_presenca(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=colab)

        resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
        assert resp.status_code == 200
        assert resp.data["confirmed_count"] == 1
        assert resp.data["my_attendance"] == "going"

    def test_mudar_de_ideia_atualiza_em_vez_de_duplicar(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=colab)

        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
        resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "not_going"}, format="json")

        assert resp.data["confirmed_count"] == 0
        assert EventAttendance.objects.filter(event=evento, user=colab).count() == 1

    def test_recusar_nao_ocupa_vaga(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh, capacity=1)
        api_client.force_authenticate(user=colab)

        resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "not_going"}, format="json")
        assert resp.data["confirmed_count"] == 0
        assert resp.data["seats_left"] == 1

    def test_evento_lotado_recusa_nova_confirmacao(
        self, api_client, django_user_model, company, rh, colab
    ):
        evento = criar_evento(company, rh, capacity=1)
        atrasado = mk(django_user_model, "atrasado@x.com", "colaborador", company)

        api_client.force_authenticate(user=colab)
        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")

        api_client.force_authenticate(user=atrasado)
        resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
        assert resp.status_code == 400
        assert "capacidade" in str(resp.data).lower()

    def test_quem_ja_confirmou_pode_reconfirmar_com_lotacao_cheia(
        self, api_client, company, rh, colab
    ):
        """Reenviar "vou" não pode ser barrado por uma vaga que é dele."""
        evento = criar_evento(company, rh, capacity=1)
        api_client.force_authenticate(user=colab)
        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")

        resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
        assert resp.status_code == 200

    def test_vaga_liberada_ao_desistir(
        self, api_client, django_user_model, company, rh, colab
    ):
        evento = criar_evento(company, rh, capacity=1)
        outro = mk(django_user_model, "fila@x.com", "colaborador", company)

        api_client.force_authenticate(user=colab)
        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "not_going"}, format="json")

        api_client.force_authenticate(user=outro)
        resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
        assert resp.status_code == 200

    def test_sem_capacidade_definida_nao_lota(
        self, api_client, django_user_model, company, rh, colab
    ):
        evento = criar_evento(company, rh, capacity=None)
        for i in range(3):
            pessoa = mk(django_user_model, f"p{i}-ag@x.com", "colaborador", company)
            api_client.force_authenticate(user=pessoa)
            resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
            assert resp.status_code == 200
        assert resp.data["seats_left"] is None

    def test_evento_que_nao_pede_confirmacao(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh, allows_rsvp=False)
        api_client.force_authenticate(user=colab)
        resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
        assert resp.status_code == 400

    def test_nao_confirma_em_evento_que_ja_passou(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh, start_at=daqui(days=-1))
        api_client.force_authenticate(user=colab)
        resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
        assert resp.status_code == 400

    def test_nao_confirma_em_evento_cancelado(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh, status=Event.Status.CANCELLED)
        api_client.force_authenticate(user=colab)
        resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
        assert resp.status_code == 400

    def test_nao_confirma_em_evento_de_outra_empresa(self, api_client, company, rh, rh_b):
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=rh_b)
        resp = api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════
# Capacidade e lista de participantes
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCapacidadeEParticipantes:
    def test_nao_reduz_capacidade_abaixo_do_confirmado(
        self, api_client, django_user_model, company, rh
    ):
        """Reduzir deixaria gente confirmada e sem vaga — sem saída boa."""
        evento = criar_evento(company, rh, capacity=5)
        for i in range(3):
            pessoa = mk(django_user_model, f"c{i}-cap@x.com", "colaborador", company)
            api_client.force_authenticate(user=pessoa)
            api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")

        api_client.force_authenticate(user=rh)
        resp = api_client.patch(f"{URL}{evento.id}/", {"capacity": 2}, format="json")
        assert resp.status_code == 400

    def test_aumentar_capacidade_e_permitido(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh, capacity=1)
        api_client.force_authenticate(user=colab)
        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")

        api_client.force_authenticate(user=rh)
        assert api_client.patch(f"{URL}{evento.id}/", {"capacity": 10}, format="json").status_code == 200

    def test_organizador_ve_a_lista_de_confirmados(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=colab)
        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")

        api_client.force_authenticate(user=rh)
        resp = api_client.get(f"{URL}{evento.id}/attendees/")
        assert resp.status_code == 200
        nomes = [a["user_details"]["full_name"] for a in resp.data["results"]]
        assert colab.full_name in nomes

    def test_colaborador_nao_ve_a_lista_de_participantes(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=colab)
        assert api_client.get(f"{URL}{evento.id}/attendees/").status_code == 403

    def test_quem_recusou_nao_entra_na_lista(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=colab)
        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "not_going"}, format="json")

        api_client.force_authenticate(user=rh)
        assert api_client.get(f"{URL}{evento.id}/attendees/").data["count"] == 0


# ══════════════════════════════════════════════════════════════════════════
# Cancelamento
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCancelamento:
    def test_cancelar_avisa_quem_confirmou(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh, title="Workshop")
        api_client.force_authenticate(user=colab)
        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")

        api_client.force_authenticate(user=rh)
        resp = api_client.post(f"{URL}{evento.id}/cancel/")
        assert resp.status_code == 200
        assert resp.data["status"] == "cancelled"
        assert Notification.objects.filter(
            user=colab, title__contains="Evento cancelado"
        ).exists()

    def test_nao_avisa_quem_havia_recusado(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=colab)
        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "not_going"}, format="json")

        api_client.force_authenticate(user=rh)
        api_client.post(f"{URL}{evento.id}/cancel/")
        assert not Notification.objects.filter(
            user=colab, title__contains="Evento cancelado"
        ).exists()

    def test_cancelar_preserva_as_confirmacoes(self, api_client, company, rh, colab):
        """Cancelar não é excluir: o registro de quem ia fica."""
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=colab)
        api_client.post(f"{URL}{evento.id}/rsvp/", {"status": "going"}, format="json")

        api_client.force_authenticate(user=rh)
        api_client.post(f"{URL}{evento.id}/cancel/")
        assert EventAttendance.objects.filter(event=evento, user=colab).exists()

    def test_cancelar_duas_vezes_e_recusado(self, api_client, company, rh):
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=rh)
        api_client.post(f"{URL}{evento.id}/cancel/")
        assert api_client.post(f"{URL}{evento.id}/cancel/").status_code == 400

    def test_colaborador_nao_cancela(self, api_client, company, rh, colab):
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=colab)
        assert api_client.post(f"{URL}{evento.id}/cancel/").status_code == 403


# ══════════════════════════════════════════════════════════════════════════
# Segmentação e isolamento
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSegmentacaoEIsolamento:
    def test_evento_sem_alvo_alcanca_a_empresa_inteira(self, api_client, company, rh, colab):
        criar_evento(company, rh, title="Para todos")
        api_client.force_authenticate(user=colab)
        titulos = [e["title"] for e in api_client.get(URL).data["results"]]
        assert "Para todos" in titulos

    def test_evento_de_setor_nao_aparece_para_quem_e_de_fora(
        self, api_client, django_user_model, company, rh
    ):
        ti = Sector.objects.create(name="TI", company=company)
        rh_setor = Sector.objects.create(name="RH", company=company)

        evento = criar_evento(company, rh, title="Só TI")
        evento.target_sectors.add(ti)

        de_fora = mk(django_user_model, "fora-ev@x.com", "colaborador", company, sector=rh_setor)
        api_client.force_authenticate(user=de_fora)
        titulos = [e["title"] for e in api_client.get(URL).data["results"]]
        assert "Só TI" not in titulos

    def test_evento_de_setor_aparece_para_quem_e_do_setor(
        self, api_client, django_user_model, company, rh
    ):
        ti = Sector.objects.create(name="TI", company=company)
        evento = criar_evento(company, rh, title="Só TI")
        evento.target_sectors.add(ti)

        do_ti = mk(django_user_model, "doti@x.com", "colaborador", company, sector=ti)
        api_client.force_authenticate(user=do_ti)
        titulos = [e["title"] for e in api_client.get(URL).data["results"]]
        assert "Só TI" in titulos

    def test_setor_de_outra_empresa_e_rejeitado(self, api_client, rh, empresa_b):
        alheio = Sector.objects.create(name="Alheio", company=empresa_b)
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            URL,
            {
                "title": "x",
                "start_at": daqui(days=1).isoformat(),
                "target_sectors": [alheio.id],
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_nao_lista_evento_de_outra_empresa(self, api_client, company, rh, rh_b):
        criar_evento(company, rh, title="Da Empresa A")
        api_client.force_authenticate(user=rh_b)
        assert api_client.get(URL).data["count"] == 0

    def test_nao_edita_evento_de_outra_empresa(self, api_client, company, rh, rh_b):
        evento = criar_evento(company, rh)
        api_client.force_authenticate(user=rh_b)
        resp = api_client.patch(f"{URL}{evento.id}/", {"title": "Invadido"}, format="json")
        assert resp.status_code == 404
