"""
Automações: gatilho + condição + ação (ETAPA 16).

O que mais importa aqui não é a automação funcionar — é ela NÃO derrubar
quem a disparou. Uma regra mal configurada não pode impedir o cadastro de
um colaborador, e não pode alcançar dados de outra empresa através do
`config`, que é JSON e passa longe das FKs que o Django validaria sozinho.
"""

import pytest
from django.utils import timezone

from apps.automations import catalog
from apps.automations.engine import disparar
from apps.automations.models import (
    AutomationAction,
    AutomationCondition,
    AutomationRule,
    AutomationRun,
)
from apps.companies.models import Company
from apps.courses.models import Course, CourseProgress
from apps.notifications.models import Notification
from apps.onboarding.models import OnboardingTask, OnboardingTemplate, TemplateTask
from apps.sectors.models import Position, Sector

RULES = "/api/v1/automations/rules/"
CATALOG = "/api/v1/automations/catalog/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


def regra(company, evento, *, nome="Regra", condicoes=(), acoes=()):
    r = AutomationRule.objects.create(
        company=company, name=nome, trigger_event=evento
    )
    for campo, operador, valor in condicoes:
        AutomationCondition.objects.create(
            rule=r, field=campo, operator=operador, value=valor
        )
    for tipo, alvo, config in acoes:
        AutomationAction.objects.create(
            rule=r, action_type=tipo, target=alvo, config=config
        )
    return r


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa Rival")


@pytest.fixture
def ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def junior(db, ti):
    return Position.objects.create(name="Dev Júnior", sector=ti)


@pytest.fixture
def admin(db, django_user_model, company):
    return mk(django_user_model, "admin-aut@x.com", "company_admin", company)


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-aut@x.com", "rh_admin", company)


@pytest.fixture
def gestor(db, django_user_model, company, ti):
    g = mk(django_user_model, "gestor-aut@x.com", "gestor", company, sector=ti)
    ti.manager = g
    ti.save()
    return g


@pytest.fixture
def colab(db, django_user_model, company, ti, junior, gestor):
    return mk(
        django_user_model, "colab-aut@x.com", "colaborador", company,
        sector=ti, position=junior, manager=gestor,
        hire_date=timezone.localdate(),
    )


# ══════════════════════════════════════════════════════════════════════════
# O motor não derruba quem disparou
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestResiliencia:
    def test_acao_quebrada_nao_derruba_o_cadastro(
        self, api_client, company, rh, django_user_model
    ):
        """
        A garantia central: uma automação mal configurada não pode impedir
        o RH de cadastrar alguém.
        """
        regra(
            company, catalog.EMPLOYEE_CREATED,
            # `template_id` de um template que não existe: a ação vai falhar.
            acoes=[(catalog.CREATE_ONBOARDING, catalog.TARGET_EMPLOYEE,
                    {"template_id": 999999})],
        )

        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "sobrevivente@x.com", "full_name": "Sobrevivente",
                "password": "SenhaForte@123", "password_confirm": "SenhaForte@123",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert django_user_model.objects.filter(email="sobrevivente@x.com").exists()

    def test_acao_sem_executor_registra_falha_em_vez_de_estourar(
        self, company, colab
    ):
        r = AutomationRule.objects.create(
            company=company, name="Inexistente", trigger_event=catalog.EMPLOYEE_CREATED
        )
        # Grava um tipo que não tem executor — simula código removido sem
        # migração dos dados.
        AutomationAction.objects.create(
            rule=r, action_type="acao_fantasma", target=catalog.TARGET_EMPLOYEE
        )

        assert disparar(catalog.EMPLOYEE_CREATED, company, employee=colab) == 0

        execucao = AutomationRun.objects.get(rule=r)
        assert execucao.status == AutomationRun.Status.FAILED
        assert "acao_fantasma" in execucao.detail

    def test_regra_inativa_nao_dispara(self, company, colab):
        r = regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "oi"})],
        )
        r.is_active = False
        r.save()

        assert disparar(catalog.EMPLOYEE_CREATED, company, employee=colab) == 0
        assert not AutomationRun.objects.exists()

    def test_execucao_bem_sucedida_fica_registrada(self, company, colab):
        """
        Sem o log, uma automação que falha em silêncio é indistinguível de
        uma que nunca foi acionada.
        """
        r = regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "Bem-vindo"})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        execucao = AutomationRun.objects.get(rule=r)
        assert execucao.status == AutomationRun.Status.SUCCESS
        assert execucao.subject_label == colab.full_name


# ══════════════════════════════════════════════════════════════════════════
# Isolamento entre empresas
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTenancy:
    def test_regra_de_outra_empresa_nao_dispara(
        self, company, empresa_b, colab
    ):
        regra(
            empresa_b, catalog.EMPLOYEE_CREATED, nome="Da rival",
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "x"})],
        )
        assert disparar(catalog.EMPLOYEE_CREATED, company, employee=colab) == 0

    def test_template_de_outra_empresa_nao_e_aplicado(
        self, company, empresa_b, colab
    ):
        """
        `config` é JSON: um id de outro tenant chega até o executor sem
        passar por nenhuma FK. O escopo tem que estar na consulta.
        """
        alheio = OnboardingTemplate.objects.create(
            company=empresa_b, name="Roteiro da rival"
        )
        TemplateTask.objects.create(template=alheio, title="Não deveria existir")

        r = regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.CREATE_ONBOARDING, catalog.TARGET_EMPLOYEE,
                    {"template_id": alheio.pk})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        assert not OnboardingTask.objects.filter(employee=colab).exists()
        assert "não encontrado" in AutomationRun.objects.get(rule=r).detail.lower()

    def test_treinamento_de_outra_empresa_nao_e_atribuido(
        self, company, empresa_b, colab
    ):
        alheio = Course.objects.create(
            title="Curso da rival", company=empresa_b, order=1
        )
        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.ASSIGN_TRAINING, catalog.TARGET_EMPLOYEE,
                    {"course_ids": [alheio.pk]})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        assert not CourseProgress.objects.filter(user=colab, course=alheio).exists()

    def test_api_nao_lista_regra_de_outra_empresa(
        self, api_client, django_user_model, empresa_b, company, admin
    ):
        regra(empresa_b, catalog.EMPLOYEE_CREATED, nome="Da rival")
        api_client.force_authenticate(user=admin)
        assert api_client.get(RULES).data["count"] == 0

    def test_api_recusa_template_de_outra_empresa_na_configuracao(
        self, api_client, admin, empresa_b
    ):
        alheio = OnboardingTemplate.objects.create(company=empresa_b, name="Rival")
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            RULES,
            {
                "name": "Tentativa", "trigger_event": catalog.EMPLOYEE_CREATED,
                "actions": [
                    {"action_type": catalog.CREATE_ONBOARDING,
                     "target": catalog.TARGET_EMPLOYEE,
                     "config": {"template_id": alheio.pk}}
                ],
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_api_recusa_treinamento_de_outra_empresa(
        self, api_client, admin, empresa_b
    ):
        alheio = Course.objects.create(title="Rival", company=empresa_b, order=1)
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            RULES,
            {
                "name": "Tentativa", "trigger_event": catalog.EMPLOYEE_CREATED,
                "actions": [
                    {"action_type": catalog.ASSIGN_TRAINING,
                     "target": catalog.TARGET_EMPLOYEE,
                     "config": {"course_ids": [alheio.pk]}}
                ],
            },
            format="json",
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════
# Condições
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCondicoes:
    def test_condicao_que_bate_executa(self, company, colab, ti):
        regra(
            company, catalog.EMPLOYEE_CREATED,
            condicoes=[("sector_id", catalog.OP_EQUALS, str(ti.pk))],
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "Bem-vindo ao TI"})],
        )
        assert disparar(catalog.EMPLOYEE_CREATED, company, employee=colab) == 1

    def test_condicao_que_nao_bate_e_ignorada(self, company, colab):
        outro = Sector.objects.create(name="Financeiro", company=company)
        r = regra(
            company, catalog.EMPLOYEE_CREATED,
            condicoes=[("sector_id", catalog.OP_EQUALS, str(outro.pk))],
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "x"})],
        )
        assert disparar(catalog.EMPLOYEE_CREATED, company, employee=colab) == 0
        assert AutomationRun.objects.get(rule=r).status == AutomationRun.Status.SKIPPED

    def test_comparacao_funciona_entre_int_do_contexto_e_texto_da_regra(
        self, company, colab, ti
    ):
        """
        O contexto traz `sector_id` como int e a regra guarda string. Sem
        normalizar, "5" != 5 e a automação nunca dispararia — falha
        silenciosa, a pior categoria.
        """
        condicao = AutomationCondition(
            field="sector_id", operator=catalog.OP_EQUALS, value=str(ti.pk)
        )
        assert condicao.matches({"sector_id": ti.pk}) is True

    def test_duas_condicoes_afunilam_em_vez_de_somar(
        self, company, colab, ti, junior
    ):
        """
        Quem escreve duas condições está estreitando o alvo, não ampliando.
        """
        outro_cargo = Position.objects.create(name="Sênior", sector=ti)

        regra(
            company, catalog.EMPLOYEE_CREATED, nome="TI + Sênior",
            condicoes=[
                ("sector_id", catalog.OP_EQUALS, str(ti.pk)),
                ("position_id", catalog.OP_EQUALS, str(outro_cargo.pk)),
            ],
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "x"})],
        )
        # O colaborador é do TI, mas Júnior — uma bate, a outra não.
        assert disparar(catalog.EMPLOYEE_CREATED, company, employee=colab) == 0

    def test_operador_esta_entre(self, company, colab, ti):
        outro = Sector.objects.create(name="Vendas", company=company)
        regra(
            company, catalog.EMPLOYEE_CREATED,
            condicoes=[("sector_id", catalog.OP_IN, f"{outro.pk},{ti.pk}")],
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "x"})],
        )
        assert disparar(catalog.EMPLOYEE_CREATED, company, employee=colab) == 1

    def test_operador_diferente_de(self, company, colab, ti):
        regra(
            company, catalog.EMPLOYEE_CREATED,
            condicoes=[("sector_id", catalog.OP_NOT_EQUALS, str(ti.pk))],
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "x"})],
        )
        assert disparar(catalog.EMPLOYEE_CREATED, company, employee=colab) == 0

    def test_sem_condicao_sempre_dispara(self, company, colab):
        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "x"})],
        )
        assert disparar(catalog.EMPLOYEE_CREATED, company, employee=colab) == 1


# ══════════════════════════════════════════════════════════════════════════
# Ações
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAcoes:
    def test_notificar_o_colaborador(self, company, colab):
        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"title": "Boas-vindas", "message": "Que bom ter você aqui"})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        assert Notification.objects.filter(user=colab, title="Boas-vindas").exists()

    def test_notificar_o_gestor(self, company, colab, gestor):
        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_MANAGER,
                    {"title": "Novo na equipe", "message": "Chegou gente nova"})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        assert Notification.objects.filter(user=gestor, title="Novo na equipe").exists()
        assert not Notification.objects.filter(user=colab, title="Novo na equipe").exists()

    def test_notificar_o_rh(self, company, colab, rh, admin):
        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_HR,
                    {"title": "Conferir cadastro", "message": "Novo colaborador"})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        avisados = set(
            Notification.objects.filter(title="Conferir cadastro").values_list(
                "user_id", flat=True
            )
        )
        assert {rh.pk, admin.pk} <= avisados

    def test_interpolacao_usa_os_dados_do_evento(self, company, colab):
        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"title": "Olá", "message": "Bem-vindo, {employee_name}!"})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        aviso = Notification.objects.get(user=colab, title="Olá")
        assert colab.full_name in aviso.message

    def test_placeholder_desconhecido_nao_derruba_a_acao(self, company, colab):
        """
        Um typo no formulário não pode quebrar a automação inteira — o
        placeholder fica literal e o aviso é entregue.
        """
        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"title": "Olá", "message": "Oi {nome_que_nao_existe}"})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        aviso = Notification.objects.get(user=colab, title="Olá")
        assert "{nome_que_nao_existe}" in aviso.message

    def test_atribuir_treinamento(self, company, colab):
        curso = Course.objects.create(title="LGPD", company=company, order=1)
        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.ASSIGN_TRAINING, catalog.TARGET_EMPLOYEE,
                    {"course_ids": [curso.pk]})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        assert CourseProgress.objects.filter(user=colab, course=curso).exists()

    def test_reatribuir_nao_zera_o_progresso(self, company, colab):
        """
        Reexecutar a automação não pode apagar o avanço de quem já começou.
        """
        curso = Course.objects.create(title="LGPD", company=company, order=1)
        CourseProgress.objects.create(user=colab, course=curso, status="in_progress")

        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.ASSIGN_TRAINING, catalog.TARGET_EMPLOYEE,
                    {"course_ids": [curso.pk]})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        assert CourseProgress.objects.get(user=colab, course=curso).status == "in_progress"

    def test_gerar_onboarding_a_partir_do_template_configurado(self, company, colab):
        template = OnboardingTemplate.objects.create(
            company=company, name="Roteiro TI", apply_automatically=False
        )
        TemplateTask.objects.create(
            template=template, title="Criar acessos", days_offset=1, responsible="hr"
        )

        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.CREATE_ONBOARDING, catalog.TARGET_EMPLOYEE,
                    {"template_id": template.pk})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        assert OnboardingTask.objects.filter(
            employee=colab, title="Criar acessos"
        ).exists()

    def test_acao_sem_destinatario_nao_quebra(self, company, colab, django_user_model):
        """Colaborador sem gestor: a ação registra e segue."""
        sozinho = mk(django_user_model, "sozinho-aut@x.com", "colaborador", company)
        r = regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_MANAGER,
                    {"message": "x"})],
        )
        assert disparar(catalog.EMPLOYEE_CREATED, company, employee=sozinho) == 1
        assert "Sem destinatário" in AutomationRun.objects.get(rule=r).detail


# ══════════════════════════════════════════════════════════════════════════
# Gatilhos ligados aos eventos reais
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGatilhos:
    def test_cadastro_de_colaborador_dispara(
        self, api_client, company, rh, django_capture_on_commit_callbacks
    ):
        regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"title": "Automação disparou", "message": "ok"})],
        )

        api_client.force_authenticate(user=rh)
        with django_capture_on_commit_callbacks(execute=True):
            api_client.post(
                "/api/v1/auth/register/",
                {
                    "email": "gatilho@x.com", "full_name": "Gatilho",
                    "password": "SenhaForte@123", "password_confirm": "SenhaForte@123",
                },
                format="json",
            )

        assert Notification.objects.filter(
            user__email="gatilho@x.com", title="Automação disparou"
        ).exists()

    def test_desativacao_dispara(
        self, api_client, company, colab, rh, django_capture_on_commit_callbacks
    ):
        regra(
            company, catalog.EMPLOYEE_DEACTIVATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_HR,
                    {"title": "Desligamento", "message": "Revogar acessos"})],
        )

        with django_capture_on_commit_callbacks(execute=True):
            colab.is_active = False
            colab.save()

        assert Notification.objects.filter(user=rh, title="Desligamento").exists()

    def test_salvar_sem_mudar_o_estado_nao_redispara(
        self, company, colab, rh, django_capture_on_commit_callbacks
    ):
        """
        Sem a checagem de transição, cada PATCH num colaborador já ativo
        dispararia a automação de novo.
        """
        regra(
            company, catalog.EMPLOYEE_ACTIVATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_HR,
                    {"title": "Ativado", "message": "x"})],
        )

        with django_capture_on_commit_callbacks(execute=True):
            colab.phone = "11999999999"
            colab.save()

        assert not AutomationRun.objects.exists()

    def test_conclusao_de_treinamento_dispara(
        self, company, colab, gestor, django_capture_on_commit_callbacks
    ):
        curso = Course.objects.create(title="NR-10", company=company, order=1)
        regra(
            company, catalog.TRAINING_COMPLETED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_MANAGER,
                    {"title": "Treinamento concluído", "message": "{course_title}"})],
        )

        with django_capture_on_commit_callbacks(execute=True):
            progresso = CourseProgress.objects.create(
                user=colab, course=curso, status="in_progress"
            )
            progresso.status = "completed"
            progresso.save()

        aviso = Notification.objects.get(user=gestor, title="Treinamento concluído")
        assert "NR-10" in aviso.message

    def test_publicacao_de_comunicado_dispara(
        self, company, rh, colab, django_capture_on_commit_callbacks
    ):
        from apps.communications.models import Announcement

        regra(
            company, catalog.ANNOUNCEMENT_PUBLISHED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_HR,
                    {"title": "Publicado", "message": "{announcement_title}"})],
        )

        with django_capture_on_commit_callbacks(execute=True):
            com = Announcement.objects.create(
                company=company, author=rh, title="Aviso geral", content="...",
            )
            com.status = Announcement.Status.PUBLISHED
            com.published_at = timezone.now()
            com.save()

        aviso = Notification.objects.filter(user=rh, title="Publicado").first()
        assert aviso is not None
        assert "Aviso geral" in aviso.message

    def test_abertura_de_solicitacao_dispara(
        self, company, colab, rh, django_capture_on_commit_callbacks
    ):
        from apps.requests.models import HRRequest

        regra(
            company, catalog.REQUEST_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_HR,
                    {"title": "Nova solicitação", "message": "{request_subject}"})],
        )

        with django_capture_on_commit_callbacks(execute=True):
            HRRequest.objects.create(
                company=company, requester=colab,
                subject="Preciso do meu holerite", description="...",
            )

        aviso = Notification.objects.filter(user=rh, title="Nova solicitação").first()
        assert aviso is not None
        assert "holerite" in aviso.message


# ══════════════════════════════════════════════════════════════════════════
# API
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAPI:
    def test_admin_cria_automacao(self, api_client, admin, ti):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            RULES,
            {
                "name": "Boas-vindas do TI",
                "trigger_event": catalog.EMPLOYEE_CREATED,
                "conditions": [
                    {"field": "sector_id", "operator": "eq", "value": str(ti.pk)}
                ],
                "actions": [
                    {"action_type": catalog.SEND_NOTIFICATION,
                     "target": catalog.TARGET_EMPLOYEE,
                     "config": {"title": "Olá", "message": "Bem-vindo"}}
                ],
            },
            format="json",
        )
        assert resp.status_code == 201, resp.data
        criada = AutomationRule.objects.get(name="Boas-vindas do TI")
        assert criada.conditions.count() == 1
        assert criada.actions.count() == 1

    def test_rh_nao_gerencia_automacao(self, api_client, rh):
        """
        Uma regra dispara e-mails para a empresa inteira e atribui
        treinamentos em massa — é decisão de administração, não rotina.
        """
        api_client.force_authenticate(user=rh)
        assert api_client.get(RULES).status_code == 403
        assert api_client.post(RULES, {"name": "X"}, format="json").status_code == 403

    def test_colaborador_nao_acessa(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        assert api_client.get(RULES).status_code == 403

    def test_regra_sem_acao_e_rejeitada(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            RULES,
            {"name": "Vazia", "trigger_event": catalog.EMPLOYEE_CREATED},
            format="json",
        )
        assert resp.status_code == 400

    def test_evento_fora_do_catalogo_e_rejeitado(self, api_client, admin):
        """
        A lista é fechada de propósito: uma automação executa código do
        servidor, e evento livre no formulário seria uma porta aberta.
        """
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            RULES,
            {
                "name": "Inventada", "trigger_event": "servidor.formatar",
                "actions": [
                    {"action_type": catalog.SEND_NOTIFICATION,
                     "target": catalog.TARGET_EMPLOYEE,
                     "config": {"message": "x"}}
                ],
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_config_com_campo_nao_aceito_e_rejeitado(self, api_client, admin):
        """
        `config` é JSONField e alimenta execução — JSON livre aqui seria um
        campo que ninguém consegue conferir.
        """
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            RULES,
            {
                "name": "Contrabando", "trigger_event": catalog.EMPLOYEE_CREATED,
                "actions": [
                    {"action_type": catalog.SEND_NOTIFICATION,
                     "target": catalog.TARGET_EMPLOYEE,
                     "config": {"message": "ok", "comando": "rm -rf /"}}
                ],
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "comando" in str(resp.data)

    def test_notificacao_sem_mensagem_e_rejeitada(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            RULES,
            {
                "name": "Muda", "trigger_event": catalog.EMPLOYEE_CREATED,
                "actions": [
                    {"action_type": catalog.SEND_NOTIFICATION,
                     "target": catalog.TARGET_EMPLOYEE, "config": {}}
                ],
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_nome_duplicado_vira_400(self, api_client, admin, company):
        regra(company, catalog.EMPLOYEE_CREATED, nome="Repetida")
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            RULES,
            {
                "name": "Repetida", "trigger_event": catalog.EMPLOYEE_CREATED,
                "actions": [
                    {"action_type": catalog.SEND_NOTIFICATION,
                     "target": catalog.TARGET_EMPLOYEE,
                     "config": {"message": "x"}}
                ],
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_editar_substitui_condicoes_e_acoes(self, api_client, admin, company, ti):
        r = regra(
            company, catalog.EMPLOYEE_CREATED, nome="Editável",
            condicoes=[("sector_id", catalog.OP_EQUALS, str(ti.pk))],
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "antigo"})],
        )
        api_client.force_authenticate(user=admin)
        resp = api_client.patch(
            f"{RULES}{r.id}/",
            {
                "conditions": [],
                "actions": [
                    {"action_type": catalog.SEND_NOTIFICATION,
                     "target": catalog.TARGET_HR,
                     "config": {"message": "novo"}}
                ],
            },
            format="json",
        )
        assert resp.status_code == 200
        r.refresh_from_db()
        assert r.conditions.count() == 0
        assert r.actions.get().config["message"] == "novo"

    def test_historico_de_execucoes(self, api_client, admin, company, colab):
        r = regra(
            company, catalog.EMPLOYEE_CREATED,
            acoes=[(catalog.SEND_NOTIFICATION, catalog.TARGET_EMPLOYEE,
                    {"message": "x"})],
        )
        disparar(catalog.EMPLOYEE_CREATED, company, employee=colab)

        api_client.force_authenticate(user=admin)
        resp = api_client.get(f"{RULES}{r.id}/runs/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["status"] == "success"

    def test_catalogo_e_servido_pela_api(self, api_client, colab):
        """
        O app não mantém cópia da lista: uma cópia desatualizada ofereceria
        um gatilho que o backend recusa.
        """
        api_client.force_authenticate(user=colab)
        resp = api_client.get(CATALOG)
        assert resp.status_code == 200
        eventos = {e["value"] for e in resp.data["events"]}
        assert catalog.EMPLOYEE_CREATED in eventos
        assert len(resp.data["actions"]) == 4
