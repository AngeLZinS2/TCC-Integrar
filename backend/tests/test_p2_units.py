"""
Unidades / filiais (ETAPA 14).

Duas coisas precisam ficar travadas: uma empresa não usa a Unit de outra
(seria o mesmo vazamento de tenancy dos setores), e a unidade AFUNILA a
segmentação junto com setor e cargo em vez de somar — "TI" + "Centro" é o
TI da Centro, não todo o TI mais toda a Centro.
"""

import pytest
from django.utils import timezone

from apps.communications.models import Announcement
from apps.communications.services import audience_of, visible_to
from apps.companies.models import Company
from apps.courses.models import Course
from apps.documents.models import Document
from apps.events.models import Event
from apps.sectors.models import Position, Sector
from apps.units.models import Unit

UNITS = "/api/v1/units/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Grupo Rival")


@pytest.fixture
def centro(db, company):
    return Unit.objects.create(company=company, name="Unidade Centro", code="CTR")


@pytest.fixture
def norte(db, company):
    return Unit.objects.create(company=company, name="Unidade Norte", code="NRT")


@pytest.fixture
def ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def admin(db, django_user_model, company):
    return mk(django_user_model, "admin-un@x.com", "company_admin", company)


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-un@x.com", "rh_admin", company)


@pytest.fixture
def dev_centro(db, django_user_model, company, ti, centro):
    return mk(
        django_user_model, "dev-centro@x.com", "colaborador", company,
        sector=ti, unit=centro,
    )


@pytest.fixture
def dev_norte(db, django_user_model, company, ti, norte):
    return mk(
        django_user_model, "dev-norte@x.com", "colaborador", company,
        sector=ti, unit=norte,
    )


@pytest.fixture
def sem_unidade(db, django_user_model, company, ti):
    return mk(django_user_model, "sem-un@x.com", "colaborador", company, sector=ti)


# ══════════════════════════════════════════════════════════════════════════
# CRUD e isolamento
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCadastro:
    def test_admin_cria_unidade(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            UNITS,
            {"name": "Unidade Shopping", "code": "SHP", "city": "São Roque", "state": "sp"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["state"] == "SP"
        assert Unit.objects.get(name="Unidade Shopping").company_id == admin.company_id

    def test_colaborador_le_mas_nao_cria(self, api_client, dev_centro, centro):
        api_client.force_authenticate(user=dev_centro)
        assert api_client.get(UNITS).data["count"] == 1
        assert api_client.post(UNITS, {"name": "X"}, format="json").status_code == 403

    def test_rh_nao_cria_unidade(self, api_client, rh):
        """
        Criar filial é decisão de estrutura da empresa, não rotina de RH —
        e uma unidade errada reetiqueta todo mundo lotado nela.
        """
        api_client.force_authenticate(user=rh)
        assert api_client.post(UNITS, {"name": "X"}, format="json").status_code == 403

    def test_nao_ve_unidade_de_outra_empresa(
        self, api_client, django_user_model, empresa_b, centro
    ):
        admin_b = mk(django_user_model, "admin@b-un.com", "company_admin", empresa_b)
        api_client.force_authenticate(user=admin_b)
        assert api_client.get(UNITS).data["count"] == 0
        assert api_client.get(f"{UNITS}{centro.id}/").status_code == 404

    def test_nome_duplicado_vira_400_e_nao_500(self, api_client, admin, centro):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(UNITS, {"name": centro.name}, format="json")
        assert resp.status_code == 400

    def test_codigo_duplicado_vira_400(self, api_client, admin, centro):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(UNITS, {"name": "Outra", "code": centro.code}, format="json")
        assert resp.status_code == 400

    def test_varias_unidades_sem_codigo_convivem(self, api_client, admin):
        """
        `code` é opcional; se o vazio entrasse na unicidade, a segunda
        unidade sem código já não poderia ser criada.
        """
        api_client.force_authenticate(user=admin)
        assert api_client.post(UNITS, {"name": "A"}, format="json").status_code == 201
        assert api_client.post(UNITS, {"name": "B"}, format="json").status_code == 201

    def test_mesmo_nome_em_empresas_diferentes_e_permitido(
        self, api_client, django_user_model, empresa_b, centro
    ):
        admin_b = mk(django_user_model, "admin2@b-un.com", "company_admin", empresa_b)
        api_client.force_authenticate(user=admin_b)
        assert api_client.post(
            UNITS, {"name": centro.name}, format="json"
        ).status_code == 201

    def test_responsavel_de_outra_empresa_e_rejeitado(
        self, api_client, django_user_model, empresa_b, admin
    ):
        de_fora = mk(django_user_model, "gestor@b-un.com", "gestor", empresa_b)
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            UNITS, {"name": "Nova", "manager": de_fora.id}, format="json"
        )
        assert resp.status_code == 400

    def test_contagem_ignora_desligados(
        self, api_client, django_user_model, company, admin, centro, dev_centro
    ):
        mk(
            django_user_model, "desligado@x.com", "colaborador", company,
            unit=centro, is_active=False,
        )
        api_client.force_authenticate(user=admin)
        unidade = api_client.get(f"{UNITS}{centro.id}/").data
        assert unidade["employee_count"] == 1


@pytest.mark.django_db
class TestLotacao:
    def test_cadastro_aceita_unidade(self, api_client, rh, centro, django_user_model):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "novo-un@x.com", "full_name": "Novo",
                "password": "SenhaForte@123", "password_confirm": "SenhaForte@123",
                "unit": centro.id,
            },
            format="json",
        )
        assert resp.status_code == 201, resp.data
        assert django_user_model.objects.get(email="novo-un@x.com").unit_id == centro.pk

    def test_nao_lota_colaborador_em_unidade_de_outra_empresa(
        self, api_client, rh, empresa_b
    ):
        de_fora = Unit.objects.create(company=empresa_b, name="Filial Rival")
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "invasor@x.com", "full_name": "Invasor",
                "password": "SenhaForte@123", "password_confirm": "SenhaForte@123",
                "unit": de_fora.id,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "unit" in resp.data

    def test_me_devolve_a_unidade(self, api_client, dev_centro, centro):
        api_client.force_authenticate(user=dev_centro)
        resp = api_client.get("/api/v1/auth/me/")
        assert resp.data["unit"] == centro.pk
        assert resp.data["unit_name"] == centro.name


# ══════════════════════════════════════════════════════════════════════════
# Segmentação
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestComunicados:
    def _publicar(self, company, autor, **alvos):
        com = Announcement.objects.create(
            company=company, author=autor, title="Aviso", content="...",
            status=Announcement.Status.PUBLISHED, published_at=timezone.now(),
        )
        for campo, valores in alvos.items():
            getattr(com, campo).set(valores)
        return com

    def test_alvo_de_unidade_restringe(
        self, company, rh, centro, dev_centro, dev_norte
    ):
        self._publicar(company, rh, target_units=[centro])

        assert visible_to(dev_centro).count() == 1
        assert visible_to(dev_norte).count() == 0

    def test_sem_alvo_de_unidade_alcanca_todos(
        self, company, rh, dev_centro, dev_norte, sem_unidade
    ):
        self._publicar(company, rh)

        assert visible_to(dev_centro).count() == 1
        assert visible_to(dev_norte).count() == 1
        assert visible_to(sem_unidade).count() == 1

    def test_quem_nao_tem_unidade_fica_fora_do_alvo_de_unidade(
        self, company, rh, centro, sem_unidade
    ):
        self._publicar(company, rh, target_units=[centro])
        assert visible_to(sem_unidade).count() == 0

    def test_setor_e_unidade_afunilam_em_vez_de_somar(
        self, company, rh, ti, centro, dev_centro, dev_norte, django_user_model, norte
    ):
        """
        O bug clássico: "TI" + "Centro" virando todo o TI MAIS toda a
        Centro. Aqui tem que ser só o TI da Centro.
        """
        vendas = Sector.objects.create(name="Vendas", company=company)
        vendedor_centro = mk(
            django_user_model, "vend-centro@x.com", "colaborador", company,
            sector=vendas, unit=centro,
        )

        self._publicar(company, rh, target_sectors=[ti], target_units=[centro])

        assert visible_to(dev_centro).count() == 1      # TI + Centro  ✓
        assert visible_to(dev_norte).count() == 0       # TI, mas Norte
        assert visible_to(vendedor_centro).count() == 0  # Centro, mas Vendas

    def test_duas_unidades_no_alvo_valem_como_OU(
        self, company, rh, centro, norte, dev_centro, dev_norte
    ):
        self._publicar(company, rh, target_units=[centro, norte])

        assert visible_to(dev_centro).count() == 1
        assert visible_to(dev_norte).count() == 1

    def test_audiencia_concorda_com_a_visibilidade(
        self, company, rh, ti, centro, dev_centro, dev_norte
    ):
        """
        `audience_of` decide quem recebe a notificação e `visible_to` decide
        quem consegue abrir. Se divergirem, alguém é avisado de um
        comunicado que não pode ler.
        """
        com = self._publicar(company, rh, target_sectors=[ti], target_units=[centro])

        alcancados = {u.pk for u in audience_of(com)}
        assert dev_centro.pk in alcancados
        assert dev_norte.pk not in alcancados

    def test_unidade_de_outra_empresa_e_rejeitada_no_alvo(
        self, api_client, rh, empresa_b
    ):
        de_fora = Unit.objects.create(company=empresa_b, name="Rival")
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            "/api/v1/communications/",
            {"title": "X", "content": "Y", "target_units": [de_fora.id]},
            format="json",
        )
        assert resp.status_code == 400
        assert "target_units" in resp.data


@pytest.mark.django_db
class TestEventos:
    def test_evento_segmentado_por_unidade(
        self, api_client, company, rh, centro, dev_centro, dev_norte
    ):
        evento = Event.objects.create(
            company=company, organizer=rh, title="Confraternização",
            start_at=timezone.now() + timezone.timedelta(days=5),
        )
        evento.target_units.set([centro])

        api_client.force_authenticate(user=dev_centro)
        assert api_client.get("/api/v1/events/").data["count"] == 1

        api_client.force_authenticate(user=dev_norte)
        assert api_client.get("/api/v1/events/").data["count"] == 0

    def test_evento_sem_alvo_aparece_para_todos(
        self, api_client, company, rh, dev_norte
    ):
        Event.objects.create(
            company=company, organizer=rh, title="Geral",
            start_at=timezone.now() + timezone.timedelta(days=5),
        )
        api_client.force_authenticate(user=dev_norte)
        assert api_client.get("/api/v1/events/").data["count"] == 1


@pytest.mark.django_db
class TestDocumentos:
    def _publicar(self, company, **alvos):
        doc = Document.objects.create(
            company=company, title="Manual", status=Document.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        for campo, valores in alvos.items():
            getattr(doc, campo).set(valores)
        return doc

    def test_documento_segmentado_por_unidade(
        self, api_client, company, centro, dev_centro, dev_norte
    ):
        self._publicar(company, target_units=[centro])

        api_client.force_authenticate(user=dev_centro)
        assert api_client.get("/api/v1/documents/").data["count"] == 1

        api_client.force_authenticate(user=dev_norte)
        assert api_client.get("/api/v1/documents/").data["count"] == 0

    def test_rh_ve_documento_de_qualquer_unidade(
        self, api_client, company, rh, centro
    ):
        """Quem gerencia precisa enxergar tudo para publicar e revisar."""
        self._publicar(company, target_units=[centro])
        api_client.force_authenticate(user=rh)
        assert api_client.get("/api/v1/documents/").data["count"] == 1


@pytest.mark.django_db
class TestTreinamentos:
    def test_treinamento_segmentado_por_unidade(
        self, api_client, company, centro, dev_centro, dev_norte
    ):
        curso = Course.objects.create(title="NR-10", company=company, order=1)
        curso.target_units.set([centro])

        api_client.force_authenticate(user=dev_centro)
        assert api_client.get("/api/v1/courses/").data["count"] == 1

        api_client.force_authenticate(user=dev_norte)
        assert api_client.get("/api/v1/courses/").data["count"] == 0

    def test_trilha_de_notificacao_concorda_com_a_listagem(
        self, company, centro, dev_centro, dev_norte
    ):
        """
        `eligible_courses_for` alimenta o aviso de "novo treinamento". Se
        divergisse da listagem, o aviso chegaria para quem não abre o curso.
        """
        from apps.notifications.services import eligible_courses_for

        curso = Course.objects.create(title="NR-10", company=company, order=1)
        curso.target_units.set([centro])

        assert eligible_courses_for(dev_centro).count() == 1
        assert eligible_courses_for(dev_norte).count() == 0

    def test_unidade_de_outra_empresa_e_rejeitada(
        self, api_client, django_user_model, company, empresa_b
    ):
        de_fora = Unit.objects.create(company=empresa_b, name="Rival")
        rh = mk(django_user_model, "rh-tr@x.com", "rh_admin", company)

        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            "/api/v1/courses/",
            {"title": "X", "order": 1, "target_units": [de_fora.id]},
            format="json",
        )
        assert resp.status_code == 400
