"""
Regressão dos bugs encontrados na revisão da P2.

Cada teste aqui reproduz um defeito que existia de verdade — não são
cenários hipotéticos. Se algum voltar a falhar, o bug voltou.
"""

import datetime

import pytest

from apps.communications.models import Announcement
from apps.companies.models import Company
from apps.sectors.models import Position, Sector

REQUESTS_URL = "/api/v1/requests/"
COMMS_URL = "/api/v1/communications/"
BIRTHDAYS_URL = "/api/v1/events/birthdays/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def outra_empresa(db):
    return Company.objects.create(name="Outra SA")


@pytest.fixture
def setor_ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def cargo_dev(db, setor_ti):
    return Position.objects.create(name="Desenvolvedor", sector=setor_ti)


@pytest.fixture
def cargo_qa(db, setor_ti):
    return Position.objects.create(name="QA", sector=setor_ti)


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-p2@x.com", "rh_admin", company)


# ══════════════════════════════════════════════════════════════════════════
# BUG 1 — Responsável de outra empresa vazava nome e e-mail
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestResponsavelPrecisaSerDaEmpresa:
    def _abrir_solicitacao(self, api_client, autor):
        api_client.force_authenticate(user=autor)
        resp = api_client.post(
            REQUESTS_URL,
            {"subject": "Teste", "description": "d", "category": "other"},
            format="json",
        )
        assert resp.status_code == 201, resp.data
        return resp.data["id"]

    def test_nao_atribui_solicitacao_a_usuario_de_outra_empresa(
        self, api_client, django_user_model, company, outra_empresa, rh
    ):
        colab = mk(django_user_model, "c-p2@x.com", "colaborador", company)
        estranho = mk(django_user_model, "fora@outra.com", "rh_admin", outra_empresa)
        rid = self._abrir_solicitacao(api_client, colab)

        api_client.force_authenticate(user=rh)
        resp = api_client.patch(
            f"{REQUESTS_URL}{rid}/", {"assigned_to": estranho.id}, format="json"
        )
        assert resp.status_code == 400

    def test_dados_de_usuario_externo_nunca_aparecem_na_solicitacao(
        self, api_client, django_user_model, company, outra_empresa, rh
    ):
        """O sintoma que o bug produzia: PII de outro tenant na tela."""
        colab = mk(django_user_model, "c2-p2@x.com", "colaborador", company)
        estranho = mk(django_user_model, "segredo@outra.com", "rh_admin", outra_empresa)
        rid = self._abrir_solicitacao(api_client, colab)

        api_client.force_authenticate(user=rh)
        api_client.patch(f"{REQUESTS_URL}{rid}/", {"assigned_to": estranho.id}, format="json")

        corpo = str(api_client.get(f"{REQUESTS_URL}{rid}/").data)
        assert estranho.email not in corpo
        assert estranho.full_name not in corpo

    def test_atribuir_a_colega_da_mesma_empresa_continua_funcionando(
        self, api_client, django_user_model, company, rh
    ):
        colab = mk(django_user_model, "c3-p2@x.com", "colaborador", company)
        rid = self._abrir_solicitacao(api_client, colab)

        api_client.force_authenticate(user=rh)
        resp = api_client.patch(f"{REQUESTS_URL}{rid}/", {"assigned_to": rh.id}, format="json")
        assert resp.status_code == 200
        assert resp.data["assigned_to"] == rh.id


# ══════════════════════════════════════════════════════════════════════════
# BUG 2 — Segmentação somava alvos em vez de afunilar
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSegmentacaoAfunila:
    def _comunicado(self, company, autor, titulo, setores=(), cargos=()):
        a = Announcement.objects.create(
            status=Announcement.Status.PUBLISHED,
            company=company, title=titulo, content="conteúdo", author=autor
        )
        for s in setores:
            a.target_sectors.add(s)
        for c in cargos:
            a.target_positions.add(c)
        return a

    def _titulos_para(self, api_client, user):
        api_client.force_authenticate(user=user)
        return [x["title"] for x in api_client.get(COMMS_URL).data["results"]]

    def test_setor_mais_cargo_alcanca_so_a_intersecao(
        self, api_client, django_user_model, company, rh, setor_ti, cargo_dev, cargo_qa
    ):
        """
        "TI + Desenvolvedor" é para os devs DE TI. Antes, o QA de TI também
        recebia, porque as dimensões eram somadas com OR.
        """
        self._comunicado(company, rh, "So devs de TI", [setor_ti], [cargo_dev])

        dev = mk(django_user_model, "dev@x.com", "colaborador", company,
                 sector=setor_ti, position=cargo_dev)
        qa = mk(django_user_model, "qa@x.com", "colaborador", company,
                sector=setor_ti, position=cargo_qa)

        assert "So devs de TI" in self._titulos_para(api_client, dev)
        assert "So devs de TI" not in self._titulos_para(api_client, qa)

    def test_cargo_igual_em_outro_setor_nao_recebe(
        self, api_client, django_user_model, company, rh, setor_ti, cargo_dev
    ):
        outro_setor = Sector.objects.create(name="Produto", company=company)
        cargo_homonimo = Position.objects.create(name="Desenvolvedor", sector=outro_setor)
        self._comunicado(company, rh, "So devs de TI", [setor_ti], [cargo_dev])

        dev_de_fora = mk(django_user_model, "devprod@x.com", "colaborador", company,
                         sector=outro_setor, position=cargo_homonimo)
        assert "So devs de TI" not in self._titulos_para(api_client, dev_de_fora)

    def test_so_setor_alcanca_o_setor_inteiro(
        self, api_client, django_user_model, company, rh, setor_ti, cargo_qa
    ):
        self._comunicado(company, rh, "Aviso do TI", [setor_ti])
        qa = mk(django_user_model, "qa2@x.com", "colaborador", company,
                sector=setor_ti, position=cargo_qa)
        assert "Aviso do TI" in self._titulos_para(api_client, qa)

    def test_sem_alvo_alcanca_a_empresa_inteira(
        self, api_client, django_user_model, company, rh
    ):
        self._comunicado(company, rh, "Para todos")
        qualquer = mk(django_user_model, "qq@x.com", "colaborador", company)
        assert "Para todos" in self._titulos_para(api_client, qualquer)

    def test_rh_enxerga_comunicado_de_qualquer_segmento(
        self, api_client, company, rh, setor_ti, cargo_dev
    ):
        """Quem administra precisa ver tudo para conseguir gerenciar."""
        self._comunicado(company, rh, "So devs de TI", [setor_ti], [cargo_dev])
        assert "So devs de TI" in self._titulos_para(api_client, rh)

    def test_detalhe_respeita_a_segmentacao(
        self, api_client, django_user_model, company, rh, setor_ti, cargo_dev, cargo_qa
    ):
        """Saber o id não pode ser suficiente para abrir o comunicado."""
        a = self._comunicado(company, rh, "So devs de TI", [setor_ti], [cargo_dev])
        qa = mk(django_user_model, "qa3@x.com", "colaborador", company,
                sector=setor_ti, position=cargo_qa)

        api_client.force_authenticate(user=qa)
        assert api_client.get(f"{COMMS_URL}{a.id}/").status_code == 404

    def test_nao_segmenta_para_setor_de_outra_empresa(
        self, api_client, rh, outra_empresa
    ):
        setor_alheio = Sector.objects.create(name="Alheio", company=outra_empresa)
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            COMMS_URL,
            {"title": "x", "content": "y", "target_sectors": [setor_alheio.id]},
            format="json",
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════
# BUG 3 — Aniversariantes expunham a data de nascimento completa
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPrivacidadeDosAniversariantes:
    @pytest.fixture
    def aniversariante(self, django_user_model, company):
        hoje = datetime.date.today()
        return mk(
            django_user_model, "niver@x.com", "colaborador", company,
            birth_date=datetime.date(1990, hoje.month, hoje.day),
        )

    def test_nao_expoe_o_ano_de_nascimento(self, api_client, aniversariante):
        api_client.force_authenticate(user=aniversariante)
        registro = api_client.get(BIRTHDAYS_URL).data["results"][0]

        assert "birth_date" not in registro
        assert "1990" not in str(registro)

    def test_mostra_apenas_dia_e_mes(self, api_client, aniversariante):
        api_client.force_authenticate(user=aniversariante)
        registro = api_client.get(BIRTHDAYS_URL).data["results"][0]

        hoje = datetime.date.today()
        assert registro["birthday"] == f"{hoje.day:02d}/{hoje.month:02d}"

    def test_nao_expoe_email(self, api_client, aniversariante):
        """Quem precisa do contato usa o Diretório, não este painel."""
        api_client.force_authenticate(user=aniversariante)
        registro = api_client.get(BIRTHDAYS_URL).data["results"][0]
        assert "email" not in registro

    def test_nao_lista_aniversariante_de_outra_empresa(
        self, api_client, django_user_model, aniversariante, outra_empresa
    ):
        hoje = datetime.date.today()
        mk(django_user_model, "niver@outra.com", "colaborador", outra_empresa,
           birth_date=datetime.date(1985, hoje.month, hoje.day))

        api_client.force_authenticate(user=aniversariante)
        nomes = [r["full_name"] for r in api_client.get(BIRTHDAYS_URL).data["results"]]
        assert "Niver" in nomes
        assert len(nomes) == 1
