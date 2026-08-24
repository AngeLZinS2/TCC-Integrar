"""
Integração entre módulos (ETAPA 18 / Módulo 17).

O spec descreve UMA cadeia:

    Novo colaborador → onboarding criado → treinamento obrigatório
    atribuído → documento obrigatório pendente → gestor notificado →
    RH notificado → colaborador recebe boas-vindas

E impõe uma restrição de arquitetura: "tudo isso deve funcionar através de
eventos/serviços. Não criar lógica duplicada em cada View."

Este arquivo testa a cadeia inteira a partir de UMA requisição de cadastro
— nenhum service é chamado à mão. Se algum elo depender de código dentro
de uma view, ele não dispara aqui e o teste quebra.
"""

import pytest
from django.utils import timezone

from apps.automations import catalog
from apps.automations.models import (
    AutomationAction,
    AutomationCondition,
    AutomationRule,
    AutomationRun,
)
from apps.courses.models import Course, CourseProgress
from apps.documents.models import Document
from apps.notifications.models import Notification
from apps.onboarding.models import OnboardingTask, OnboardingTemplate, TemplateTask
from apps.sectors.models import Position, Sector

REGISTER = "/api/v1/auth/register/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def ti(db, company):
    return Sector.objects.create(name="Tecnologia", company=company)


@pytest.fixture
def junior(db, ti):
    return Position.objects.create(name="Dev Júnior", sector=ti)


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-int@x.com", "rh_admin", company)


@pytest.fixture
def gestor(db, django_user_model, company, ti):
    g = mk(django_user_model, "gestor-int@x.com", "gestor", company, sector=ti)
    ti.manager = g
    ti.save()
    return g


@pytest.fixture
def treinamento_obrigatorio(db, company):
    return Course.objects.create(title="Segurança da Informação", company=company, order=1)


@pytest.fixture
def documento_obrigatorio(db, company):
    from apps.documents.models import DocumentVersion

    doc = Document.objects.create(
        company=company, title="Código de Conduta", is_required=True,
        status=Document.Status.PUBLISHED, published_at=timezone.now(),
    )
    DocumentVersion.objects.create(
        document=doc, version_number=1, original_name="conduta.pdf",
        extension="pdf", mime_type="application/pdf", is_active=True,
    )
    return doc


@pytest.fixture
def cenario_completo(db, company, ti, junior, rh, gestor, treinamento_obrigatorio):
    """
    A empresa configurada como o spec descreve: um roteiro de integração e
    uma automação que atribui o treinamento e avisa gestor e RH.
    """
    template = OnboardingTemplate.objects.create(
        company=company, name="Integração padrão", sector=ti
    )
    TemplateTask.objects.create(
        template=template, title="Criar acessos", days_offset=1,
        responsible="hr", order=1,
    )
    TemplateTask.objects.create(
        template=template, title="Apresentar a equipe", days_offset=1,
        responsible="manager", order=2,
    )
    TemplateTask.objects.create(
        template=template, title="Enviar documentos", days_offset=3,
        responsible="employee", order=3,
    )

    regra = AutomationRule.objects.create(
        company=company, name="Admissão", trigger_event=catalog.EMPLOYEE_CREATED
    )
    AutomationCondition.objects.create(
        rule=regra, field="sector_id", operator=catalog.OP_EQUALS, value=str(ti.pk)
    )
    AutomationAction.objects.create(
        rule=regra, action_type=catalog.ASSIGN_TRAINING,
        target=catalog.TARGET_EMPLOYEE,
        config={"course_ids": [treinamento_obrigatorio.pk]}, order=1,
    )
    AutomationAction.objects.create(
        rule=regra, action_type=catalog.SEND_NOTIFICATION,
        target=catalog.TARGET_MANAGER,
        config={
            "title": "Novo integrante na equipe",
            "message": "{employee_name} começou hoje. Confira as tarefas de integração.",
        },
        order=2,
    )
    AutomationAction.objects.create(
        rule=regra, action_type=catalog.SEND_NOTIFICATION,
        target=catalog.TARGET_HR,
        config={
            "title": "Admissão registrada",
            "message": "Cadastro de {employee_name} concluído.",
        },
        order=3,
    )
    return template, regra


def admitir(api_client, rh, ti, junior, capturar, email="novato-int@x.com"):
    """Uma única requisição — nada de chamar service à mão."""
    api_client.force_authenticate(user=rh)
    with capturar(execute=True):
        resposta = api_client.post(
            REGISTER,
            {
                "email": email, "full_name": "Novato da Silva",
                "password": "SenhaForte@123", "password_confirm": "SenhaForte@123",
                "sector": ti.pk, "position": junior.pk,
            },
            format="json",
        )
    return resposta


@pytest.mark.django_db
class TestCadeiaDeAdmissao:
    def test_a_cadeia_inteira_roda_a_partir_de_um_unico_cadastro(
        self, api_client, django_user_model, cenario_completo, rh, gestor,
        ti, junior, treinamento_obrigatorio, documento_obrigatorio,
        django_capture_on_commit_callbacks,
    ):
        resposta = admitir(
            api_client, rh, ti, junior, django_capture_on_commit_callbacks
        )
        assert resposta.status_code == 201, resposta.data

        novato = django_user_model.objects.get(email="novato-int@x.com")

        # 1. Onboarding criado, com responsáveis resolvidos por PAPEL.
        tarefas = {t.title: t for t in OnboardingTask.objects.filter(employee=novato)}
        assert set(tarefas) == {
            "Criar acessos", "Apresentar a equipe", "Enviar documentos"
        }
        assert tarefas["Criar acessos"].assigned_to_id == rh.pk
        assert tarefas["Apresentar a equipe"].assigned_to_id == gestor.pk
        assert tarefas["Enviar documentos"].assigned_to_id == novato.pk

        # 2. Prazos relativos à admissão viraram datas reais.
        assert tarefas["Criar acessos"].due_date == novato.hire_date + timezone.timedelta(days=1)

        # 3. Treinamento obrigatório atribuído.
        assert CourseProgress.objects.filter(
            user=novato, course=treinamento_obrigatorio
        ).exists()

        # 4. Documento obrigatório aparece como pendência dele.
        api_client.force_authenticate(user=novato)
        pendentes = api_client.get("/api/v1/documents/pending/")
        assert pendentes.status_code == 200
        titulos = [d["title"] for d in pendentes.data["results"]]
        assert documento_obrigatorio.title in titulos

        # 5. Gestor notificado, com o nome interpolado.
        aviso_gestor = Notification.objects.get(
            user=gestor, title="Novo integrante na equipe"
        )
        assert "Novato da Silva" in aviso_gestor.message

        # 6. RH notificado.
        assert Notification.objects.filter(
            user=rh, title="Admissão registrada"
        ).exists()

        # 7. Colaborador recebeu boas-vindas.
        assert Notification.objects.filter(
            user=novato, title__startswith="Bem-vindo"
        ).exists()

    def test_a_home_do_novato_reflete_a_cadeia(
        self, api_client, django_user_model, cenario_completo, rh, ti, junior,
        documento_obrigatorio, django_capture_on_commit_callbacks,
    ):
        """
        O painel tem que contar o que a cadeia produziu. Se divergir, a
        pessoa vê "0 pendências" numa integração que acabou de ser criada.
        """
        admitir(api_client, rh, ti, junior, django_capture_on_commit_callbacks)
        novato = django_user_model.objects.get(email="novato-int@x.com")

        api_client.force_authenticate(user=novato)
        home = api_client.get("/api/v1/dashboard/me/").data

        assert home["onboarding"]["total"] == 3
        assert home["pending"]["onboarding_tasks"] == 3
        assert home["pending"]["documents"] == 1
        assert home["pending"]["trainings"] >= 1

    def test_o_painel_do_gestor_enxerga_o_novato(
        self, api_client, django_user_model, cenario_completo, rh, gestor,
        ti, junior, django_capture_on_commit_callbacks,
    ):
        admitir(api_client, rh, ti, junior, django_capture_on_commit_callbacks)

        api_client.force_authenticate(user=gestor)
        painel = api_client.get("/api/v1/dashboard/team/").data

        assert painel["team_size"] == 1
        assert painel["onboarding"]["in_progress"] == 1

    def test_o_painel_do_rh_contabiliza_a_admissao(
        self, api_client, cenario_completo, rh, ti, junior,
        django_capture_on_commit_callbacks,
    ):
        admitir(api_client, rh, ti, junior, django_capture_on_commit_callbacks)

        api_client.force_authenticate(user=rh)
        painel = api_client.get("/api/v1/dashboard/hr/").data

        assert painel["onboarding"]["total"] == 3
        assert painel["onboarding"]["pending"] == 3

    def test_condicao_da_automacao_e_respeitada_na_cadeia(
        self, api_client, django_user_model, cenario_completo, company, rh,
        treinamento_obrigatorio, django_capture_on_commit_callbacks,
    ):
        """
        A regra é do setor de Tecnologia. Quem entra em outro setor recebe
        o onboarding (o template é do setor, mas há fallback) e NÃO recebe o
        treinamento da automação.
        """
        financeiro = Sector.objects.create(name="Financeiro", company=company)

        api_client.force_authenticate(user=rh)
        with django_capture_on_commit_callbacks(execute=True):
            api_client.post(
                REGISTER,
                {
                    "email": "financeiro@x.com", "full_name": "Fin Anceiro",
                    "password": "SenhaForte@123", "password_confirm": "SenhaForte@123",
                    "sector": financeiro.pk,
                },
                format="json",
            )

        de_fora = django_user_model.objects.get(email="financeiro@x.com")
        assert not CourseProgress.objects.filter(
            user=de_fora, course=treinamento_obrigatorio
        ).exists()

    def test_a_cadeia_e_idempotente_sob_reexecucao(
        self, api_client, django_user_model, cenario_completo, rh, ti, junior,
        treinamento_obrigatorio, django_capture_on_commit_callbacks,
    ):
        """
        Reprocessar a admissão — por retry de task ou reaplicação manual —
        não pode duplicar o plano de integração nem zerar o progresso.
        """
        from apps.onboarding.services import aplicar_templates_automaticos

        admitir(api_client, rh, ti, junior, django_capture_on_commit_callbacks)
        novato = django_user_model.objects.get(email="novato-int@x.com")

        progresso = CourseProgress.objects.get(
            user=novato, course=treinamento_obrigatorio
        )
        progresso.status = "in_progress"
        progresso.save()

        aplicar_templates_automaticos(novato)
        from apps.automations.engine import disparar

        disparar(catalog.EMPLOYEE_CREATED, novato.company, employee=novato)

        assert OnboardingTask.objects.filter(employee=novato).count() == 3
        progresso.refresh_from_db()
        assert progresso.status == "in_progress"


@pytest.mark.django_db
class TestSemLogicaDuplicada:
    def test_a_cadeia_roda_sem_passar_por_view_nenhuma(
        self, django_user_model, cenario_completo, company, ti, junior, rh, gestor,
        treinamento_obrigatorio, django_capture_on_commit_callbacks,
    ):
        """
        A restrição do Módulo 17: "não criar lógica duplicada em cada View".

        Criar o usuário direto pelo model — sem API, sem serializer, sem
        view — tem que produzir a mesma cadeia. Se algum elo morasse dentro
        de uma view, ele não aconteceria aqui.
        """
        with django_capture_on_commit_callbacks(execute=True):
            direto = django_user_model.objects.create_user(
                email="direto@x.com", full_name="Direto Pelo Model",
                password="senha@123", role="colaborador", company=company,
                sector=ti, position=junior, hire_date=timezone.localdate(),
            )

        assert OnboardingTask.objects.filter(employee=direto).count() == 3
        assert CourseProgress.objects.filter(
            user=direto, course=treinamento_obrigatorio
        ).exists()
        assert Notification.objects.filter(
            user=gestor, title="Novo integrante na equipe"
        ).exists()

    def test_falha_de_automacao_nao_impede_o_onboarding(
        self, api_client, django_user_model, cenario_completo, company, rh,
        ti, junior, django_capture_on_commit_callbacks,
    ):
        """
        Os elos são independentes: uma automação quebrada não pode levar
        junto o plano de integração, que vem por outro caminho.
        """
        quebrada = AutomationRule.objects.create(
            company=company, name="Quebrada",
            trigger_event=catalog.EMPLOYEE_CREATED,
        )
        AutomationAction.objects.create(
            rule=quebrada, action_type=catalog.CREATE_ONBOARDING,
            target=catalog.TARGET_EMPLOYEE, config={"template_id": 999999},
        )

        resposta = admitir(
            api_client, rh, ti, junior, django_capture_on_commit_callbacks
        )
        assert resposta.status_code == 201

        novato = django_user_model.objects.get(email="novato-int@x.com")
        assert OnboardingTask.objects.filter(employee=novato).count() == 3
        assert AutomationRun.objects.filter(
            rule=quebrada, status=AutomationRun.Status.FAILED
        ).exists()

    def test_auditoria_registra_a_cadeia(
        self, api_client, django_user_model, cenario_completo, rh, ti, junior,
        django_capture_on_commit_callbacks,
    ):
        """
        A cadeia mexe em dados de pessoas; ela precisa deixar rastro.
        """
        from apps.audit.models import AuditLog

        admitir(api_client, rh, ti, junior, django_capture_on_commit_callbacks)

        recursos = set(
            AuditLog.objects.filter(company_id=rh.company_id).values_list(
                "resource_type", flat=True
            )
        )
        assert "onboarding_plan" in recursos
