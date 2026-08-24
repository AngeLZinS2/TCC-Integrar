"""
Performance: N+1 nas telas que crescem (ETAPA 20 / Módulo 22).

A técnica é sempre a mesma: monta N registros, conta as queries, monta 3N
e conta de novo. Se o número subir junto, é N+1 — e o teste falha ANTES de
alguém descobrir em produção com 500 colaboradores.

Assertivas de número absoluto seriam frágeis (qualquer `select_related`
novo mudaria a contagem). O que se afirma aqui é a INVARIÂNCIA: mais dados
não podem significar mais queries.
"""

import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone

from apps.communications.models import Announcement
from apps.courses.models import Course, CourseProgress
from apps.documents.models import Document, DocumentVersion
from apps.events.models import Event
from apps.notifications.models import Notification
from apps.onboarding.models import OnboardingTask
from apps.requests.models import HRRequest
from apps.sectors.models import Position, Sector


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def setor(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def cargo(db, setor):
    return Position.objects.create(name="Dev", sector=setor)


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-perf@x.com", "rh_admin", company)


@pytest.fixture
def colab(db, django_user_model, company, setor, cargo):
    return mk(
        django_user_model, "colab-perf@x.com", "colaborador", company,
        sector=setor, position=cargo, hire_date=timezone.localdate(),
    )


def contar_queries(api_client, user, rota) -> int:
    api_client.force_authenticate(user=user)
    with CaptureQueriesContext(connection) as capturadas:
        resposta = api_client.get(rota)
        assert resposta.status_code == 200, f"{rota}: {resposta.status_code}"
    return len(capturadas)


def assert_constante(api_client, user, rota, criar, *, pequeno=2, grande=12):
    """
    Executa `criar(n)` duas vezes e compara as contagens de query.

    A margem de 1 absorve variação legítima (uma query a mais na contagem
    da paginação em alguns bancos). O que não se aceita é a contagem
    crescer proporcionalmente ao volume.
    """
    criar(pequeno)
    poucas = contar_queries(api_client, user, rota)

    criar(grande)
    muitas = contar_queries(api_client, user, rota)

    assert muitas <= poucas + 1, (
        f"{rota}: {poucas} queries com {pequeno} registros e {muitas} com "
        f"{pequeno + grande} — cresce com o volume (N+1)."
    )


# ══════════════════════════════════════════════════════════════════════════
# Listagens
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestListagens:
    def test_tarefas_de_onboarding(self, api_client, company, rh, colab):
        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                OnboardingTask.objects.create(
                    company=company, employee=colab, assigned_to=rh,
                    title=f"Tarefa {contador['n']}",
                    due_date=timezone.localdate(),
                )

        assert_constante(api_client, rh, "/api/v1/onboarding/tasks/", criar)

    def test_solicitacoes(self, api_client, company, rh, colab):
        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                HRRequest.objects.create(
                    company=company, requester=colab, assigned_to=rh,
                    subject=f"Assunto {contador['n']}", description=".",
                )

        assert_constante(api_client, rh, "/api/v1/requests/", criar)

    def test_documentos(self, api_client, company, rh):
        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                doc = Document.objects.create(
                    company=company, title=f"Documento {contador['n']}",
                    status=Document.Status.PUBLISHED, published_at=timezone.now(),
                )
                DocumentVersion.objects.create(
                    document=doc, version_number=1, original_name="a.pdf",
                    extension="pdf", is_active=True,
                )

        assert_constante(api_client, rh, "/api/v1/documents/", criar)

    def test_comunicados(self, api_client, company, rh, colab):
        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                Announcement.objects.create(
                    company=company, author=rh, title=f"Aviso {contador['n']}",
                    content=".", status=Announcement.Status.PUBLISHED,
                    published_at=timezone.now(),
                )

        assert_constante(api_client, colab, "/api/v1/communications/", criar)

    def test_eventos(self, api_client, company, rh, colab):
        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                Event.objects.create(
                    company=company, organizer=rh, title=f"Evento {contador['n']}",
                    start_at=timezone.now() + timezone.timedelta(days=contador["n"]),
                )

        assert_constante(api_client, colab, "/api/v1/events/", criar)

    def test_treinamentos(self, api_client, company, rh, colab):
        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                Course.objects.create(
                    title=f"Curso {contador['n']}", company=company,
                    order=contador["n"],
                )

        assert_constante(api_client, colab, "/api/v1/courses/", criar)

    def test_notificacoes(self, api_client, colab):
        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                Notification.objects.create(
                    user=colab, title=f"Aviso {contador['n']}", message="."
                )

        assert_constante(api_client, colab, "/api/v1/notifications/", criar)

    def test_colaboradores(self, api_client, django_user_model, company, setor, rh):
        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                mk(
                    django_user_model, f"p{contador['n']}-perf@x.com",
                    "colaborador", company, sector=setor,
                )

        assert_constante(api_client, rh, "/api/v1/employees/", criar)


# ══════════════════════════════════════════════════════════════════════════
# Painéis
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPaineis:
    def test_painel_do_rh_nao_cresce_com_o_quadro(
        self, api_client, django_user_model, company, setor, rh
    ):
        """
        O painel do RH é a tela mais fácil de virar N+1 e a mais visitada.
        """
        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                pessoa = mk(
                    django_user_model, f"d{contador['n']}-perf@x.com",
                    "colaborador", company, sector=setor,
                )
                curso = Course.objects.create(
                    title=f"C{contador['n']}", company=company, order=contador["n"]
                )
                CourseProgress.objects.create(
                    user=pessoa, course=curso, status="completed"
                )
                OnboardingTask.objects.create(
                    company=company, employee=pessoa, title=f"T{contador['n']}"
                )
                HRRequest.objects.create(
                    company=company, requester=pessoa,
                    subject=f"S{contador['n']}", description=".",
                )

        assert_constante(api_client, rh, "/api/v1/dashboard/hr/", criar)

    def test_home_do_colaborador_nao_cresce(
        self, api_client, company, colab
    ):
        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                OnboardingTask.objects.create(
                    company=company, employee=colab, title=f"T{contador['n']}"
                )
                Course.objects.create(
                    title=f"C{contador['n']}", company=company, order=contador["n"]
                )
                Notification.objects.create(
                    user=colab, title=f"N{contador['n']}", message="."
                )

        assert_constante(api_client, colab, "/api/v1/dashboard/me/", criar)

    def test_painel_do_gestor_nao_cresce_com_a_equipe(
        self, api_client, django_user_model, company, setor
    ):
        gestor = mk(
            django_user_model, "gestor-perf@x.com", "gestor", company, sector=setor
        )
        setor.manager = gestor
        setor.save()

        contador = {"n": 0}

        def criar(quantidade):
            for _ in range(quantidade):
                contador["n"] += 1
                pessoa = mk(
                    django_user_model, f"e{contador['n']}-perf@x.com",
                    "colaborador", company, sector=setor, manager=gestor,
                )
                OnboardingTask.objects.create(
                    company=company, employee=pessoa, title=f"T{contador['n']}"
                )

        assert_constante(api_client, gestor, "/api/v1/dashboard/team/", criar)


# ══════════════════════════════════════════════════════════════════════════
# Notificação em massa
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestNotificacaoEmMassa:
    def test_notificar_a_empresa_inteira_usa_um_insert_so(
        self, django_user_model, company, setor
    ):
        """
        Módulo 40: "não criar milhares de notificações síncronas". Um INSERT
        por pessoa numa empresa de 500 seriam 500 idas ao banco dentro da
        requisição que publicou o comunicado.
        """
        from apps.notifications.channels import notify

        pessoas = [
            mk(
                django_user_model, f"m{i}-perf@x.com", "colaborador", company,
                sector=setor,
            )
            for i in range(25)
        ]

        with CaptureQueriesContext(connection) as capturadas:
            enviados = notify(pessoas, "Aviso geral", "Mensagem para todos")

        assert enviados == 25
        inserts = [
            q for q in capturadas.captured_queries
            if "INSERT INTO" in q["sql"] and "notification" in q["sql"].lower()
        ]
        assert len(inserts) == 1, (
            f"{len(inserts)} INSERTs para 25 pessoas — deveria ser bulk_create."
        )

    def test_publicar_comunicado_nao_cresce_com_o_publico(
        self, api_client, django_user_model, company, setor, rh
    ):
        """
        Publicar avisa todo o público-alvo. O custo tem que ser constante,
        senão a requisição de publicação degrada conforme a empresa cresce.
        """
        def publicar_com(quantidade_de_pessoas):
            for i in range(quantidade_de_pessoas):
                mk(
                    django_user_model, f"pub{i}-{quantidade_de_pessoas}@x.com",
                    "colaborador", company, sector=setor,
                )
            com = Announcement.objects.create(
                company=company, author=rh,
                title=f"Aviso {quantidade_de_pessoas}", content=".",
            )
            api_client.force_authenticate(user=rh)
            with CaptureQueriesContext(connection) as capturadas:
                resp = api_client.post(f"/api/v1/communications/{com.pk}/publish/")
                assert resp.status_code == 200, resp.data
            return len(capturadas)

        poucas = publicar_com(3)
        muitas = publicar_com(20)

        assert muitas <= poucas + 2, (
            f"publicação: {poucas} queries para 3 pessoas e {muitas} para 23 — "
            "cresce com o público."
        )

    def test_gerar_onboarding_usa_bulk_create(
        self, company, colab, rh
    ):
        """
        Um template de dez itens não pode ser dez INSERTs.
        """
        from apps.onboarding.models import OnboardingTemplate, TemplateTask
        from apps.onboarding.services import aplicar_template

        template = OnboardingTemplate.objects.create(
            company=company, name="Longo", apply_automatically=False
        )
        for i in range(10):
            TemplateTask.objects.create(
                template=template, title=f"Passo {i}", days_offset=i, order=i
            )

        with CaptureQueriesContext(connection) as capturadas:
            criadas = aplicar_template(template, colab, criado_por=rh)

        assert len(criadas) == 10
        inserts = [
            q for q in capturadas.captured_queries
            if "INSERT INTO" in q["sql"] and "onboardingtask" in q["sql"].lower()
        ]
        assert len(inserts) == 1, (
            f"{len(inserts)} INSERTs para 10 tarefas — deveria ser bulk_create."
        )
