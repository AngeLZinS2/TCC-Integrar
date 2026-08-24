"""
Tarefas e templates de integração (ETAPAS 12-13).

Duas preocupações guiam os testes: quem pode FECHAR uma tarefa — senão o
colaborador marcaria "conferir documentação" como feita e pularia a
conferência do RH — e quem pode VER o plano de integração dos outros, que
revela admissão, cargo e pendências de cada um.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.companies.models import Company
from apps.onboarding import services
from apps.onboarding.models import (
    OnboardingTask,
    OnboardingTaskComment,
    OnboardingTemplate,
    TemplateTask,
)
from apps.sectors.models import Position, Sector

TASKS = "/api/v1/onboarding/tasks/"
TEMPLATES = "/api/v1/onboarding/templates/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa B onboarding")


@pytest.fixture
def setor(db, company):
    return Sector.objects.create(name="Tecnologia", company=company)


@pytest.fixture
def cargo(db, setor):
    return Position.objects.create(name="Dev Júnior", sector=setor)


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-onb@x.com", "rh_admin", company)


@pytest.fixture
def gestor(db, django_user_model, company, setor):
    g = mk(django_user_model, "gestor-onb@x.com", "gestor", company, sector=setor)
    setor.manager = g
    setor.save()
    return g


@pytest.fixture
def colab(db, django_user_model, company, setor, cargo, gestor):
    return mk(
        django_user_model, "colab-onb@x.com", "colaborador", company,
        sector=setor, position=cargo, manager=gestor,
        hire_date=timezone.localdate(),
    )


@pytest.fixture
def outro_colab(db, django_user_model, company):
    return mk(django_user_model, "outro-onb@x.com", "colaborador", company)


@pytest.fixture
def tarefa(db, company, colab, rh):
    return OnboardingTask.objects.create(
        company=company, employee=colab, assigned_to=rh,
        title="Conferir documentação", due_date=timezone.localdate(),
    )


# ══════════════════════════════════════════════════════════════════════════
# Quem fecha a tarefa
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestConclusao:
    def test_responsavel_conclui(self, api_client, rh, tarefa):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            f"{TASKS}{tarefa.id}/status/", {"status": "completed"}, format="json"
        )
        assert resp.status_code == 200
        tarefa.refresh_from_db()
        assert tarefa.status == "completed"
        assert tarefa.completed_by_id == rh.pk
        assert tarefa.completed_at is not None

    def test_colaborador_nao_fecha_tarefa_do_rh(self, api_client, colab, tarefa):
        """
        A tarefa é da integração DELE, mas o responsável é o RH. Se ele
        pudesse fechar, "conferir documentação" seria concluída sem
        ninguém conferir nada.
        """
        api_client.force_authenticate(user=colab)
        resp = api_client.post(
            f"{TASKS}{tarefa.id}/status/", {"status": "completed"}, format="json"
        )
        assert resp.status_code == 403
        tarefa.refresh_from_db()
        assert tarefa.status == "pending"

    def test_colaborador_fecha_a_propria_tarefa(self, api_client, company, colab):
        minha = OnboardingTask.objects.create(
            company=company, employee=colab, assigned_to=colab, title="Enviar RG"
        )
        api_client.force_authenticate(user=colab)
        resp = api_client.post(
            f"{TASKS}{minha.id}/status/", {"status": "completed"}, format="json"
        )
        assert resp.status_code == 200

    def test_rh_fecha_qualquer_tarefa(self, api_client, company, colab, rh):
        do_colab = OnboardingTask.objects.create(
            company=company, employee=colab, assigned_to=colab, title="Enviar RG"
        )
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            f"{TASKS}{do_colab.id}/status/", {"status": "completed"}, format="json"
        )
        assert resp.status_code == 200

    def test_reabrir_limpa_a_marca_de_conclusao(self, api_client, rh, tarefa):
        """
        Deixar `completed_at` antigo faria o painel contar a tarefa como
        concluída no dia errado.
        """
        api_client.force_authenticate(user=rh)
        api_client.post(f"{TASKS}{tarefa.id}/status/", {"status": "completed"}, format="json")
        api_client.post(f"{TASKS}{tarefa.id}/status/", {"status": "pending"}, format="json")

        tarefa.refresh_from_db()
        assert tarefa.completed_at is None
        assert tarefa.completed_by_id is None

    def test_status_invalido_e_rejeitado(self, api_client, rh, tarefa):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            f"{TASKS}{tarefa.id}/status/", {"status": "aprovado"}, format="json"
        )
        assert resp.status_code == 400

    def test_conclusao_avisa_o_colaborador(self, api_client, rh, tarefa, colab):
        from apps.notifications.models import Notification

        api_client.force_authenticate(user=rh)
        api_client.post(f"{TASKS}{tarefa.id}/status/", {"status": "completed"}, format="json")

        assert Notification.objects.filter(
            user=colab, title="Etapa da sua integração concluída"
        ).exists()

    def test_nao_avisa_quando_a_pessoa_fecha_a_propria(self, api_client, company, colab):
        from apps.notifications.models import Notification

        minha = OnboardingTask.objects.create(
            company=company, employee=colab, assigned_to=colab, title="Enviar RG"
        )
        api_client.force_authenticate(user=colab)
        api_client.post(f"{TASKS}{minha.id}/status/", {"status": "completed"}, format="json")

        assert not Notification.objects.filter(
            user=colab, title="Etapa da sua integração concluída"
        ).exists()


# ══════════════════════════════════════════════════════════════════════════
# Quem enxerga o quê
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestVisibilidade:
    def test_colaborador_nao_ve_integracao_dos_colegas(
        self, api_client, company, colab, outro_colab, rh
    ):
        OnboardingTask.objects.create(
            company=company, employee=outro_colab, assigned_to=rh, title="Do colega"
        )
        OnboardingTask.objects.create(
            company=company, employee=colab, assigned_to=colab, title="Minha"
        )

        api_client.force_authenticate(user=colab)
        titulos = [t["title"] for t in api_client.get(TASKS).data["results"]]
        assert titulos == ["Minha"]

    def test_gestor_ve_a_integracao_da_equipe(
        self, api_client, company, colab, outro_colab, gestor, rh
    ):
        OnboardingTask.objects.create(
            company=company, employee=colab, assigned_to=rh, title="Da equipe"
        )
        OnboardingTask.objects.create(
            company=company, employee=outro_colab, assigned_to=rh, title="De fora"
        )

        api_client.force_authenticate(user=gestor)
        titulos = {t["title"] for t in api_client.get(TASKS).data["results"]}
        assert titulos == {"Da equipe"}

    def test_rh_ve_todas_da_empresa(
        self, api_client, company, colab, outro_colab, rh
    ):
        OnboardingTask.objects.create(company=company, employee=colab, title="A")
        OnboardingTask.objects.create(company=company, employee=outro_colab, title="B")

        api_client.force_authenticate(user=rh)
        assert api_client.get(TASKS).data["count"] == 2

    def test_nao_ve_tarefa_de_outra_empresa(
        self, api_client, django_user_model, empresa_b, company, colab
    ):
        OnboardingTask.objects.create(company=company, employee=colab, title="Da Alfa")
        rh_b = mk(django_user_model, "rh@b-onb.com", "rh_admin", empresa_b)

        api_client.force_authenticate(user=rh_b)
        assert api_client.get(TASKS).data["count"] == 0

    def test_tarefa_de_outra_empresa_nao_e_alcancavel_por_id(
        self, api_client, django_user_model, empresa_b, tarefa
    ):
        rh_b = mk(django_user_model, "rh2@b-onb.com", "rh_admin", empresa_b)
        api_client.force_authenticate(user=rh_b)
        assert api_client.get(f"{TASKS}{tarefa.id}/").status_code == 404

    def test_minha_integracao_traz_progresso(
        self, api_client, company, colab, rh
    ):
        OnboardingTask.objects.create(
            company=company, employee=colab, assigned_to=colab, title="A",
            status="completed",
        )
        OnboardingTask.objects.create(
            company=company, employee=colab, assigned_to=rh, title="B"
        )

        api_client.force_authenticate(user=colab)
        resp = api_client.get("/api/v1/onboarding/my/")
        assert resp.status_code == 200
        assert resp.data["progress"] == {
            "total": 2, "completed": 1, "pending": 1, "overdue": 0, "percent": 50
        }

    def test_colaborador_nao_acompanha_integracao_alheia(
        self, api_client, colab, outro_colab
    ):
        api_client.force_authenticate(user=colab)
        resp = api_client.get(f"/api/v1/onboarding/employees/{outro_colab.id}/")
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════
# Criação e permissão
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPermissao:
    def test_rh_cria_tarefa(self, api_client, rh, colab):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            TASKS,
            {"title": "Criar acessos", "employee": colab.id, "assigned_to": rh.id,
             "priority": "high"},
            format="json",
        )
        assert resp.status_code == 201
        assert OnboardingTask.objects.get(title="Criar acessos").company_id == rh.company_id

    def test_colaborador_nao_cria_tarefa(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        resp = api_client.post(
            TASKS, {"title": "Folga", "employee": colab.id}, format="json"
        )
        assert resp.status_code == 403

    def test_permissao_e_checada_antes_da_validacao(self, api_client, colab):
        """
        Payload vazio e sem permissão tem que dar 403, não 400 — um 400 aqui
        entregaria o formato esperado da requisição para quem não pode
        fazê-la.
        """
        api_client.force_authenticate(user=colab)
        assert api_client.post(TASKS, {}, format="json").status_code == 403

    def test_nao_atribui_tarefa_a_pessoa_de_outra_empresa(
        self, api_client, django_user_model, empresa_b, rh, colab
    ):
        """
        Se passasse, o nome e o cargo de alguém de outra empresa apareceriam
        na tela — vazamento de dado pessoal entre tenants.
        """
        de_fora = mk(django_user_model, "fora@b-onb.com", "colaborador", empresa_b)

        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            TASKS,
            {"title": "X", "employee": colab.id, "assigned_to": de_fora.id},
            format="json",
        )
        assert resp.status_code == 400
        assert "assigned_to" in resp.data

    def test_nao_cria_tarefa_para_colaborador_de_outra_empresa(
        self, api_client, django_user_model, empresa_b, rh
    ):
        de_fora = mk(django_user_model, "fora2@b-onb.com", "colaborador", empresa_b)
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            TASKS, {"title": "X", "employee": de_fora.id}, format="json"
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════
# Atraso
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAtraso:
    def test_prazo_vencido_marca_atraso(self, company, colab):
        vencida = OnboardingTask.objects.create(
            company=company, employee=colab, title="Atrasada",
            due_date=timezone.localdate() - timedelta(days=3),
        )
        assert vencida.is_overdue is True
        assert vencida.days_late == 3

    def test_tarefa_concluida_nao_conta_como_atrasada(self, company, colab):
        feita = OnboardingTask.objects.create(
            company=company, employee=colab, title="Feita",
            due_date=timezone.localdate() - timedelta(days=3),
            status="completed",
        )
        assert feita.is_overdue is False

    def test_tarefa_sem_prazo_nunca_atrasa(self, company, colab):
        sem_prazo = OnboardingTask.objects.create(
            company=company, employee=colab, title="Sem prazo"
        )
        assert sem_prazo.is_overdue is False

    def test_filtro_overdue(self, api_client, company, colab, rh):
        OnboardingTask.objects.create(
            company=company, employee=colab, title="Vencida",
            due_date=timezone.localdate() - timedelta(days=1),
        )
        OnboardingTask.objects.create(
            company=company, employee=colab, title="Em dia",
            due_date=timezone.localdate() + timedelta(days=5),
        )

        api_client.force_authenticate(user=rh)
        resp = api_client.get(f"{TASKS}?overdue=true")
        assert [t["title"] for t in resp.data["results"]] == ["Vencida"]

    def test_lembrete_agrupa_por_responsavel(self, company, colab, rh):
        from apps.notifications.models import Notification
        from apps.onboarding.tasks import avisar_tarefas_atrasadas

        for i in range(3):
            OnboardingTask.objects.create(
                company=company, employee=colab, assigned_to=rh, title=f"T{i}",
                due_date=timezone.localdate() - timedelta(days=2),
            )

        assert avisar_tarefas_atrasadas() == 1
        avisos = Notification.objects.filter(user=rh, title="Tarefas de integração atrasadas")
        assert avisos.count() == 1
        assert "3 tarefa(s)" in avisos.first().message

    def test_lembrete_nao_repete_no_mesmo_dia(self, company, colab, rh):
        from apps.notifications.models import Notification
        from apps.onboarding.tasks import avisar_tarefas_atrasadas

        OnboardingTask.objects.create(
            company=company, employee=colab, assigned_to=rh, title="T",
            due_date=timezone.localdate() - timedelta(days=1),
        )
        avisar_tarefas_atrasadas()
        assert avisar_tarefas_atrasadas() == 0
        assert Notification.objects.filter(
            user=rh, title="Tarefas de integração atrasadas"
        ).count() == 1


# ══════════════════════════════════════════════════════════════════════════
# Comentários
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestComentarios:
    def test_comentario_interno_nao_aparece_para_o_colaborador(
        self, api_client, rh, colab, tarefa
    ):
        api_client.force_authenticate(user=rh)
        api_client.post(
            f"{TASKS}{tarefa.id}/comments/",
            {"message": "Documento ilegível, cobrar de novo", "is_internal": True},
            format="json",
        )
        api_client.post(
            f"{TASKS}{tarefa.id}/comments/", {"message": "Recebido"}, format="json"
        )

        api_client.force_authenticate(user=colab)
        mensagens = [c["message"] for c in api_client.get(f"{TASKS}{tarefa.id}/comments/").data]
        assert mensagens == ["Recebido"]

    def test_rh_ve_os_internos(self, api_client, rh, tarefa):
        api_client.force_authenticate(user=rh)
        api_client.post(
            f"{TASKS}{tarefa.id}/comments/",
            {"message": "Interno", "is_internal": True}, format="json",
        )
        assert len(api_client.get(f"{TASKS}{tarefa.id}/comments/").data) == 1

    def test_colaborador_nao_marca_o_proprio_comentario_como_interno(
        self, api_client, company, colab
    ):
        """
        Deixar passar faria o comentário dele sumir da tela dele mesmo.
        """
        minha = OnboardingTask.objects.create(
            company=company, employee=colab, assigned_to=colab, title="Enviar RG"
        )
        api_client.force_authenticate(user=colab)
        resp = api_client.post(
            f"{TASKS}{minha.id}/comments/",
            {"message": "Enviei ontem", "is_internal": True}, format="json",
        )
        assert resp.status_code == 201
        assert resp.data["is_internal"] is False

    def test_detalhe_tambem_esconde_o_interno(self, api_client, rh, colab, tarefa):
        OnboardingTaskComment.objects.create(
            task=tarefa, author=rh, message="Segredo", is_internal=True
        )
        api_client.force_authenticate(user=colab)
        resp = api_client.get(f"{TASKS}{tarefa.id}/")
        assert resp.data["comments"] == []


# ══════════════════════════════════════════════════════════════════════════
# Templates
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def template(db, company, setor, cargo):
    t = OnboardingTemplate.objects.create(
        company=company, name="Desenvolvedor Júnior", sector=setor, position=cargo
    )
    TemplateTask.objects.create(
        template=t, title="Criar acessos", days_offset=1, responsible="hr", order=1
    )
    TemplateTask.objects.create(
        template=t, title="Apresentar equipe", days_offset=1, responsible="manager", order=2
    )
    TemplateTask.objects.create(
        template=t, title="Treinamento de segurança", days_offset=7,
        responsible="employee", order=3,
    )
    return t


@pytest.mark.django_db
class TestTemplates:
    def test_aplicar_gera_as_tarefas_com_prazo_relativo_a_admissao(
        self, template, colab, rh
    ):
        criadas = services.aplicar_template(template, colab, criado_por=rh)

        assert len(criadas) == 3
        por_titulo = {t.title: t for t in OnboardingTask.objects.filter(employee=colab)}
        assert por_titulo["Criar acessos"].due_date == colab.hire_date + timedelta(days=1)
        assert por_titulo["Treinamento de segurança"].due_date == (
            colab.hire_date + timedelta(days=7)
        )

    def test_responsavel_e_resolvido_por_papel(self, template, colab, rh, gestor):
        services.aplicar_template(template, colab, criado_por=rh)
        por_titulo = {t.title: t for t in OnboardingTask.objects.filter(employee=colab)}

        assert por_titulo["Criar acessos"].assigned_to_id == rh.pk
        assert por_titulo["Apresentar equipe"].assigned_to_id == gestor.pk
        assert por_titulo["Treinamento de segurança"].assigned_to_id == colab.pk

    def test_aplicar_duas_vezes_nao_duplica(self, template, colab, rh):
        services.aplicar_template(template, colab, criado_por=rh)
        segunda = services.aplicar_template(template, colab, criado_por=rh)

        assert segunda == []
        assert OnboardingTask.objects.filter(employee=colab).count() == 3

    def test_template_de_outra_empresa_e_recusado(self, template, empresa_b, django_user_model):
        de_fora = mk(django_user_model, "x@b-onb.com", "colaborador", empresa_b)
        with pytest.raises(services.OnboardingError):
            services.aplicar_template(template, de_fora)

    def test_um_aviso_por_responsavel_e_nao_um_por_tarefa(
        self, template, colab, rh
    ):
        from apps.notifications.models import Notification

        Notification.objects.all().delete()
        services.aplicar_template(template, colab, criado_por=rh)

        # O RH tem 1 tarefa, o gestor 1, o colaborador 1 — mas o que importa
        # é que ninguém receba um aviso por tarefa.
        assert Notification.objects.filter(
            user=rh, title__startswith="Integração de"
        ).count() == 1
        assert Notification.objects.filter(
            user=colab, title="Suas tarefas de integração"
        ).count() == 1

    def test_sem_gestor_a_tarefa_nasce_sem_responsavel(
        self, api_client, company, template, django_user_model, setor, cargo
    ):
        """
        Cair no RH silenciosamente esconderia que o setor está sem gestor.
        """
        sozinho = mk(
            django_user_model, "sozinho@x.com", "colaborador", company,
            sector=Sector.objects.create(name="Sem gestor", company=company),
            hire_date=timezone.localdate(),
        )
        template.sector = None
        template.position = None
        template.save()

        services.aplicar_template(template, sozinho)
        apresentar = OnboardingTask.objects.get(
            employee=sozinho, title="Apresentar equipe"
        )
        assert apresentar.assigned_to_id is None

    def test_rh_cria_template_com_tarefas(self, api_client, rh, setor):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            TEMPLATES,
            {
                "name": "Estágio", "sector": setor.id,
                "tasks": [
                    {"title": "Criar crachá", "days_offset": 0, "responsible": "hr"},
                    {"title": "Ler manual", "days_offset": 3, "responsible": "employee"},
                ],
            },
            format="json",
        )
        assert resp.status_code == 201
        assert TemplateTask.objects.filter(template__name="Estágio").count() == 2

    def test_colaborador_nao_cria_template(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        assert api_client.post(TEMPLATES, {"name": "X"}, format="json").status_code == 403

    def test_editar_template_nao_reescreve_integracao_em_andamento(
        self, api_client, template, colab, rh
    ):
        """
        Quem já começou a integração não pode ver as tarefas mudarem de
        baixo dos pés porque o RH ajustou o roteiro para os próximos.
        """
        services.aplicar_template(template, colab, criado_por=rh)
        antes = set(
            OnboardingTask.objects.filter(employee=colab).values_list("title", flat=True)
        )

        api_client.force_authenticate(user=rh)
        api_client.patch(
            f"{TEMPLATES}{template.id}/",
            {"tasks": [{"title": "Roteiro novo", "days_offset": 1, "responsible": "hr"}]},
            format="json",
        )

        depois = set(
            OnboardingTask.objects.filter(employee=colab).values_list("title", flat=True)
        )
        assert depois == antes

    def test_cargo_de_outro_setor_e_rejeitado(self, api_client, rh, company, setor, cargo):
        outro_setor = Sector.objects.create(name="Financeiro", company=company)
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            TEMPLATES,
            {"name": "Inconsistente", "sector": outro_setor.id, "position": cargo.id},
            format="json",
        )
        assert resp.status_code == 400

    def test_setor_de_outra_empresa_e_rejeitado(self, api_client, rh, empresa_b):
        de_fora = Sector.objects.create(name="De fora", company=empresa_b)
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            TEMPLATES, {"name": "X", "sector": de_fora.id}, format="json"
        )
        assert resp.status_code == 400

    def test_nome_de_template_e_unico_na_empresa(self, api_client, rh, template):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            TEMPLATES, {"name": template.name}, format="json"
        )
        assert resp.status_code == 400

    def test_mesmo_nome_em_empresas_diferentes_e_permitido(
        self, api_client, django_user_model, empresa_b, template
    ):
        rh_b = mk(django_user_model, "rh3@b-onb.com", "rh_admin", empresa_b)
        api_client.force_authenticate(user=rh_b)
        assert api_client.post(
            TEMPLATES, {"name": template.name}, format="json"
        ).status_code == 201

    def test_endpoint_apply(self, api_client, template, colab, rh):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            f"{TEMPLATES}{template.id}/apply/", {"employee": colab.id}, format="json"
        )
        assert resp.status_code == 201
        assert resp.data["created"] == 3

    def test_apply_repetido_devolve_200_sem_criar(self, api_client, template, colab, rh):
        api_client.force_authenticate(user=rh)
        api_client.post(f"{TEMPLATES}{template.id}/apply/", {"employee": colab.id}, format="json")
        resp = api_client.post(
            f"{TEMPLATES}{template.id}/apply/", {"employee": colab.id}, format="json"
        )
        assert resp.status_code == 200
        assert resp.data["created"] == 0


@pytest.mark.django_db
class TestEscolhaDeTemplate:
    def test_o_mais_especifico_vence(self, company, colab, setor, cargo):
        generico = OnboardingTemplate.objects.create(company=company, name="Geral")
        TemplateTask.objects.create(template=generico, title="Geral", days_offset=1)

        especifico = OnboardingTemplate.objects.create(
            company=company, name="Do cargo", sector=setor, position=cargo
        )
        TemplateTask.objects.create(template=especifico, title="Do cargo", days_offset=1)

        escolhidos = services.templates_para(colab)
        assert [t.name for t in escolhidos] == ["Do cargo"]

    def test_template_inativo_nao_e_aplicado(self, company, colab):
        OnboardingTemplate.objects.create(
            company=company, name="Desligado", is_active=False
        )
        assert services.templates_para(colab) == []

    def test_template_sem_aplicacao_automatica_fica_de_fora(self, company, colab):
        OnboardingTemplate.objects.create(
            company=company, name="Manual", apply_automatically=False
        )
        assert services.templates_para(colab) == []

    def test_template_de_outro_setor_nao_se_aplica(self, company, colab):
        outro = Sector.objects.create(name="Jurídico", company=company)
        OnboardingTemplate.objects.create(company=company, name="Do jurídico", sector=outro)
        assert services.templates_para(colab) == []


@pytest.mark.django_db
class TestGeracaoAutomatica:
    def test_cadastro_de_colaborador_gera_o_plano(
        self, api_client, django_user_model, company, setor, rh,
        django_capture_on_commit_callbacks,
    ):
        """
        O ciclo do Módulo 7: o RH cadastra a pessoa e as tarefas aparecem
        sozinhas, com responsáveis e prazos.
        """
        template = OnboardingTemplate.objects.create(company=company, name="Padrão")
        TemplateTask.objects.create(
            template=template, title="Criar acessos", days_offset=1, responsible="hr"
        )

        api_client.force_authenticate(user=rh)
        # A geração vai por `transaction.on_commit`, que num teste dentro de
        # atomic nunca dispararia sozinho.
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.post(
                "/api/v1/auth/register/",
                {
                    "email": "novato@x.com", "full_name": "Novato Silva",
                    "password": "SenhaForte@123", "password_confirm": "SenhaForte@123",
                    "sector": setor.id,
                },
                format="json",
            )
        assert resp.status_code == 201, resp.data

        novato = django_user_model.objects.get(email="novato@x.com")
        tarefa = OnboardingTask.objects.get(employee=novato)
        assert tarefa.title == "Criar acessos"
        assert tarefa.assigned_to_id == rh.pk
        assert tarefa.due_date == novato.hire_date + timedelta(days=1)

    def test_sem_template_o_cadastro_segue_normal(
        self, api_client, django_user_model, company, rh
    ):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            "/api/v1/auth/register/",
            {"email": "semplano@x.com", "full_name": "Sem Plano",
             "password": "SenhaForte@123", "password_confirm": "SenhaForte@123"},
            format="json",
        )
        assert resp.status_code == 201
        assert not OnboardingTask.objects.filter(employee__email="semplano@x.com").exists()
