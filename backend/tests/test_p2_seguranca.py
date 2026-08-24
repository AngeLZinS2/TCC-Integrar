"""
Multi-tenant e matriz de autorização (ETAPA 19 / Módulos 27 e 28).

Este arquivo faz uma coisa só: pegar TODOS os recursos da P2 e, para cada
um, provar que a Empresa A não alcança o da Empresa B mesmo conhecendo o
id — e que cada papel só faz o que lhe cabe.

O Módulo 27 pede atenção especial a ARQUIVOS, porque é onde o vazamento é
mais direto: um download não é uma listagem filtrada, é um arquivo saindo
do servidor.
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.automations import catalog
from apps.automations.models import AutomationAction, AutomationRule
from apps.communications.models import Announcement
from apps.companies.models import Company
from apps.courses.models import Course
from apps.courses.quiz_models import Certificate
from apps.documents.models import Document, DocumentVersion
from apps.events.models import Event
from apps.notifications.models import Notification
from apps.onboarding.models import OnboardingTask, OnboardingTemplate
from apps.requests.models import HRRequest
from apps.sectors.models import Sector
from apps.units.models import Unit

PDF = b"%PDF-1.4\n%fake\n"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


# ── Dois tenants completos ──────────────────────────────────────────────────

@pytest.fixture
def empresa_a(db, company):
    return company


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa B")


@pytest.fixture
def rh_a(db, django_user_model, empresa_a):
    return mk(django_user_model, "rh@a-sec.com", "rh_admin", empresa_a)


@pytest.fixture
def admin_a(db, django_user_model, empresa_a):
    return mk(django_user_model, "admin@a-sec.com", "company_admin", empresa_a)


@pytest.fixture
def rh_b(db, django_user_model, empresa_b):
    return mk(django_user_model, "rh@b-sec.com", "rh_admin", empresa_b)


@pytest.fixture
def admin_b(db, django_user_model, empresa_b):
    return mk(django_user_model, "admin@b-sec.com", "company_admin", empresa_b)


@pytest.fixture
def colab_b(db, django_user_model, empresa_b):
    return mk(django_user_model, "colab@b-sec.com", "colaborador", empresa_b)


@pytest.fixture
def recursos_de_b(db, empresa_b, rh_b, colab_b):
    """Um registro de cada tipo, todos da Empresa B."""
    setor = Sector.objects.create(name="Setor B", company=empresa_b)
    unidade = Unit.objects.create(company=empresa_b, name="Filial B")

    solicitacao = HRRequest.objects.create(
        company=empresa_b, requester=colab_b,
        subject="Assunto sigiloso da B", description="...",
    )

    documento = Document.objects.create(
        company=empresa_b, title="Contrato da B",
        status=Document.Status.PUBLISHED, published_at=timezone.now(),
    )
    versao = DocumentVersion.objects.create(
        document=documento, version_number=1, original_name="contrato-b.pdf",
        extension="pdf", mime_type="application/pdf", is_active=True,
        file=SimpleUploadedFile("contrato-b.pdf", PDF, content_type="application/pdf"),
    )

    comunicado = Announcement.objects.create(
        company=empresa_b, author=rh_b, title="Comunicado da B", content="...",
        status=Announcement.Status.PUBLISHED, published_at=timezone.now(),
    )

    evento = Event.objects.create(
        company=empresa_b, organizer=rh_b, title="Evento da B",
        start_at=timezone.now() + timezone.timedelta(days=7),
    )

    curso = Course.objects.create(title="Treinamento da B", company=empresa_b, order=1)

    tarefa = OnboardingTask.objects.create(
        company=empresa_b, employee=colab_b, title="Tarefa da B"
    )

    template = OnboardingTemplate.objects.create(
        company=empresa_b, name="Template da B"
    )

    certificado = Certificate.objects.create(
        user=colab_b, course=curso, company=empresa_b, score=100
    )

    regra = AutomationRule.objects.create(
        company=empresa_b, name="Automação da B",
        trigger_event=catalog.EMPLOYEE_CREATED,
    )
    AutomationAction.objects.create(
        rule=regra, action_type=catalog.SEND_NOTIFICATION,
        target=catalog.TARGET_EMPLOYEE, config={"message": "x"},
    )

    notificacao = Notification.objects.create(
        user=colab_b, title="Aviso da B", message="conteúdo sigiloso"
    )

    return {
        "setor": setor, "unidade": unidade, "solicitacao": solicitacao,
        "documento": documento, "versao": versao, "comunicado": comunicado,
        "evento": evento, "curso": curso, "tarefa": tarefa,
        "template": template, "certificado": certificado, "regra": regra,
        "notificacao": notificacao, "colab": colab_b,
    }


# ══════════════════════════════════════════════════════════════════════════
# A → B: nada passa
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIsolamentoPorId:
    """
    O id é conhecido em todos os casos. Um filtro de listagem que esconde
    mas não bloqueia o acesso direto não é isolamento.
    """

    @pytest.mark.parametrize(
        "rota,chave",
        [
            ("/api/v1/requests/{}/", "solicitacao"),
            ("/api/v1/documents/{}/", "documento"),
            ("/api/v1/communications/{}/", "comunicado"),
            ("/api/v1/events/{}/", "evento"),
            ("/api/v1/courses/{}/", "curso"),
            ("/api/v1/onboarding/tasks/{}/", "tarefa"),
            ("/api/v1/onboarding/templates/{}/", "template"),
            ("/api/v1/units/{}/", "unidade"),
            ("/api/v1/sectors/{}/", "setor"),
        ],
    )
    def test_admin_de_a_nao_alcanca_recurso_de_b(
        self, api_client, admin_a, recursos_de_b, rota, chave
    ):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.get(rota.format(recursos_de_b[chave].pk))
        assert resp.status_code == 404, f"{rota} vazou: {resp.status_code}"

    def test_certificado_de_b_nao_e_alcancavel(
        self, api_client, admin_a, recursos_de_b
    ):
        api_client.force_authenticate(user=admin_a)
        codigo = recursos_de_b["certificado"].code
        assert api_client.get(f"/api/v1/certificates/{codigo}/").status_code == 404

    def test_automacao_de_b_nao_e_alcancavel(
        self, api_client, admin_a, recursos_de_b
    ):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.get(f"/api/v1/automations/rules/{recursos_de_b['regra'].pk}/")
        assert resp.status_code == 404

    def test_notificacao_de_b_nao_e_alcancavel(
        self, api_client, admin_a, recursos_de_b
    ):
        api_client.force_authenticate(user=admin_a)
        alvo = recursos_de_b["notificacao"].pk
        assert api_client.get(f"/api/v1/notifications/{alvo}/").status_code == 404

    def test_colaborador_de_b_nao_e_alcancavel(
        self, api_client, admin_a, recursos_de_b
    ):
        api_client.force_authenticate(user=admin_a)
        alvo = recursos_de_b["colab"].pk
        assert api_client.get(f"/api/v1/employees/{alvo}/").status_code == 404

    def test_integracao_de_colaborador_de_b_nao_e_alcancavel(
        self, api_client, admin_a, recursos_de_b
    ):
        api_client.force_authenticate(user=admin_a)
        alvo = recursos_de_b["colab"].pk
        resp = api_client.get(f"/api/v1/onboarding/employees/{alvo}/")
        assert resp.status_code in {403, 404}


@pytest.mark.django_db
class TestListagensNaoVazam:
    @pytest.mark.parametrize(
        "rota",
        [
            "/api/v1/requests/",
            "/api/v1/documents/",
            "/api/v1/communications/",
            "/api/v1/events/",
            "/api/v1/courses/",
            "/api/v1/onboarding/tasks/",
            "/api/v1/onboarding/templates/",
            "/api/v1/units/",
            "/api/v1/certificates/",
        ],
    )
    def test_listagem_de_a_nao_traz_nada_de_b(
        self, api_client, admin_a, recursos_de_b, rota
    ):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.get(rota)
        assert resp.status_code == 200, rota
        assert resp.data["count"] == 0, f"{rota} vazou {resp.data['count']} registro(s)"

    def test_painel_de_a_nao_conta_nada_de_b(
        self, api_client, rh_a, recursos_de_b
    ):
        api_client.force_authenticate(user=rh_a)
        painel = api_client.get("/api/v1/dashboard/hr/").data
        assert painel["requests"]["open"] == 0
        assert painel["documents"]["published"] == 0
        assert painel["communication"]["published"] == 0
        assert painel["onboarding"]["total"] == 0


# ══════════════════════════════════════════════════════════════════════════
# Arquivos — o Módulo 27 pede atenção especial
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestArquivos:
    def test_download_de_documento_de_b_e_bloqueado(
        self, api_client, admin_a, recursos_de_b
    ):
        """
        O caso que o spec destaca: usuário de A com o id do documento de B.
        Um download não é listagem filtrada — é arquivo saindo do servidor.
        """
        api_client.force_authenticate(user=admin_a)
        doc = recursos_de_b["documento"].pk
        versao = recursos_de_b["versao"].pk
        resp = api_client.get(f"/api/v1/documents/{doc}/versions/{versao}/download/")
        assert resp.status_code == 404

    def test_download_de_versao_especifica_de_b_e_bloqueado(
        self, api_client, admin_a, recursos_de_b
    ):
        """
        Versão tem id próprio: bloquear só a rota do documento deixaria a
        porta da versão aberta.
        """
        api_client.force_authenticate(user=admin_a)
        versao = recursos_de_b["versao"].pk
        # Documento de A + versão de B: o par precisa bater, senão o id da
        # versão vira uma porta lateral.
        outro_doc = Document.objects.create(
            company=admin_a.company, title="Meu"
        )
        resp = api_client.get(
            f"/api/v1/documents/{outro_doc.pk}/versions/{versao}/download/"
        )
        assert resp.status_code == 404

    def test_download_sem_autenticacao_e_bloqueado(
        self, api_client, recursos_de_b
    ):
        api_client.force_authenticate(user=None)
        doc = recursos_de_b["documento"].pk
        versao = recursos_de_b["versao"].pk
        resp = api_client.get(f"/api/v1/documents/{doc}/versions/{versao}/download/")
        assert resp.status_code == 401

    def test_dono_do_documento_baixa(self, api_client, rh_b, recursos_de_b):
        """Contraprova: sem isto, o teste acima passaria com a rota quebrada."""
        api_client.force_authenticate(user=rh_b)
        doc = recursos_de_b["documento"].pk
        versao = recursos_de_b["versao"].pk
        resp = api_client.get(f"/api/v1/documents/{doc}/versions/{versao}/download/")
        assert resp.status_code == 200

    def test_anexo_de_solicitacao_de_b_nao_e_alcancavel(
        self, api_client, admin_a, recursos_de_b, rh_b, colab_b
    ):
        from apps.requests import services as req_services

        comentario = req_services.comentar(
            recursos_de_b["solicitacao"], autor=colab_b, texto="Segue anexo"
        )
        from apps.requests.models import RequestAttachment

        anexo = RequestAttachment.objects.create(
            comment=comentario, original_name="sigiloso.pdf", extension="pdf",
            file=SimpleUploadedFile("s.pdf", PDF, content_type="application/pdf"),
        )

        api_client.force_authenticate(user=admin_a)
        resp = api_client.get(
            f"/api/v1/requests/{recursos_de_b['solicitacao'].pk}"
            f"/attachments/{anexo.pk}/download/"
        )
        assert resp.status_code in {403, 404}

    def test_upload_com_extensao_proibida_e_recusado(
        self, api_client, rh_a, empresa_a
    ):
        doc = Document.objects.create(company=empresa_a, title="Alvo")
        api_client.force_authenticate(user=rh_a)
        resp = api_client.post(
            f"/api/v1/documents/{doc.pk}/versions/",
            {"file": SimpleUploadedFile(
                "malicioso.exe", b"MZ\x90\x00", content_type="application/pdf"
            )},
            format="multipart",
        )
        assert resp.status_code == 400

    def test_upload_com_mime_mentindo_e_recusado(
        self, api_client, rh_a, empresa_a
    ):
        """
        O `Content-Type` vem do cliente e não vale nada. O tipo real sai dos
        bytes iniciais do arquivo.
        """
        doc = Document.objects.create(company=empresa_a, title="Alvo")
        api_client.force_authenticate(user=rh_a)
        resp = api_client.post(
            f"/api/v1/documents/{doc.pk}/versions/",
            {"file": SimpleUploadedFile(
                "disfarcado.pdf", b"MZ\x90\x00executavel",
                content_type="application/pdf",
            )},
            format="multipart",
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════
# Matriz de autorização (Módulo 28)
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def owner(db, django_user_model, empresa_a):
    return mk(django_user_model, "owner@sec.com", "owner", empresa_a)


@pytest.fixture
def gestor_a(db, django_user_model, empresa_a):
    setor = Sector.objects.create(name="TI A", company=empresa_a)
    g = mk(django_user_model, "gestor@a-sec.com", "gestor", empresa_a, sector=setor)
    setor.manager = g
    setor.save()
    return g


@pytest.fixture
def colab_a(db, django_user_model, empresa_a, gestor_a):
    return mk(
        django_user_model, "colab@a-sec.com", "colaborador", empresa_a,
        sector=gestor_a.sector, manager=gestor_a,
    )


def papeis(request, nomes):
    return [request.getfixturevalue(n) for n in nomes]


@pytest.mark.django_db
class TestMatrizDeAutorizacao:
    """
    A matriz do Módulo 28, como teste em vez de tabela no código.

    Cada linha: (rota, método, quem PODE). Quem não está na lista tem que
    receber 403 ou 404 — nunca 200, nunca 400.
    """

    ESCRITA = [
        ("/api/v1/units/", {"name": "Nova"}, ["admin_a"]),
        (
            "/api/v1/automations/rules/",
            {
                "name": "Nova", "trigger_event": catalog.EMPLOYEE_CREATED,
                "actions": [
                    {"action_type": catalog.SEND_NOTIFICATION,
                     "target": catalog.TARGET_EMPLOYEE,
                     "config": {"message": "x"}}
                ],
            },
            ["admin_a"],
        ),
        (
            "/api/v1/onboarding/templates/",
            {"name": "Novo roteiro"},
            ["admin_a", "rh_a"],
        ),
    ]

    @pytest.mark.parametrize("rota,payload,autorizados", ESCRITA)
    def test_quem_nao_pode_recebe_403(
        self, request, api_client, rota, payload, autorizados
    ):
        todos = ["owner", "admin_a", "rh_a", "gestor_a", "colab_a"]
        negados = [p for p in todos if p not in autorizados]

        for nome in negados:
            api_client.force_authenticate(user=request.getfixturevalue(nome))
            resp = api_client.post(rota, payload, format="json")
            assert resp.status_code in {403, 404}, (
                f"{nome} conseguiu {resp.status_code} em POST {rota}"
            )

    @pytest.mark.parametrize("rota,payload,autorizados", ESCRITA)
    def test_quem_pode_consegue(
        self, request, api_client, rota, payload, autorizados
    ):
        """
        Contraprova: sem ela, uma rota quebrada faria o teste acima passar.
        """
        for nome in autorizados:
            api_client.force_authenticate(user=request.getfixturevalue(nome))
            corpo = dict(payload)
            corpo["name"] = f"{corpo['name']} {nome}"
            resp = api_client.post(rota, corpo, format="json")
            assert resp.status_code == 201, (
                f"{nome} recebeu {resp.status_code} em POST {rota}: {resp.data}"
            )

    def test_owner_nao_alcanca_dado_operacional(
        self, api_client, owner, empresa_a, rh_a, colab_a
    ):
        """
        A regra da P0: o dono da plataforma administra tenants e métricas
        agregadas, nunca os dados pessoais dos colaboradores.
        """
        HRRequest.objects.create(
            company=empresa_a, requester=colab_a, subject="Pessoal", description="."
        )
        api_client.force_authenticate(user=owner)

        for rota in [
            "/api/v1/requests/",
            "/api/v1/employees/",
            "/api/v1/onboarding/tasks/",
            "/api/v1/certificates/",
        ]:
            resp = api_client.get(rota)
            vazio = resp.status_code in {403, 404} or resp.data.get("count") == 0
            assert vazio, f"owner enxergou dado operacional em {rota}"

    def test_colaborador_abre_a_propria_solicitacao(
        self, api_client, colab_a
    ):
        api_client.force_authenticate(user=colab_a)
        resp = api_client.post(
            "/api/v1/requests/",
            {"subject": "Minha solicitação", "description": "Preciso de X"},
            format="json",
        )
        assert resp.status_code == 201

    def test_colaborador_nao_ve_solicitacao_de_colega(
        self, api_client, django_user_model, empresa_a, colab_a
    ):
        colega = mk(django_user_model, "colega@a-sec.com", "colaborador", empresa_a)
        alheia = HRRequest.objects.create(
            company=empresa_a, requester=colega, subject="Do colega", description="."
        )
        api_client.force_authenticate(user=colab_a)
        assert api_client.get(f"/api/v1/requests/{alheia.pk}/").status_code == 404

    def test_gestor_nao_vira_rh_pelo_painel(self, api_client, gestor_a):
        api_client.force_authenticate(user=gestor_a)
        assert api_client.get("/api/v1/dashboard/hr/").status_code == 403


# ══════════════════════════════════════════════════════════════════════════
# Tenant nunca vem do cliente (Módulo 38)
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTenantNuncaVemDoCliente:
    def test_company_no_corpo_e_ignorado(
        self, api_client, rh_a, empresa_a, empresa_b
    ):
        """
        "Nunca fazer: company_id vindo do Flutter + trust." Se o campo fosse
        aceito, bastaria trocar um número no corpo para gravar na empresa
        alheia.
        """
        api_client.force_authenticate(user=rh_a)
        resp = api_client.post(
            "/api/v1/onboarding/templates/",
            {"name": "Tentativa", "company": empresa_b.pk},
            format="json",
        )
        assert resp.status_code == 201
        criado = OnboardingTemplate.objects.get(name="Tentativa")
        assert criado.company_id == empresa_a.pk

    def test_company_em_unidade_e_ignorado(
        self, api_client, admin_a, empresa_a, empresa_b
    ):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.post(
            "/api/v1/units/",
            {"name": "Tentativa", "company": empresa_b.pk},
            format="json",
        )
        assert resp.status_code == 201
        assert Unit.objects.get(name="Tentativa").company_id == empresa_a.pk

    def test_filtro_por_empresa_alheia_nao_amplia_o_escopo(
        self, api_client, admin_a, empresa_b, recursos_de_b
    ):
        """
        Passar `?company=` de outra empresa não pode abrir o que o escopo
        do usuário fecha.
        """
        api_client.force_authenticate(user=admin_a)
        resp = api_client.get(f"/api/v1/onboarding/tasks/?company={empresa_b.pk}")
        assert resp.data["count"] == 0
