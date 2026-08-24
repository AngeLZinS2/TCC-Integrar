"""
Painéis de RH, colaborador e gestor (ETAPA 17).

O risco aqui não é o número errado — é o painel virar uma porta lateral
para dados que a listagem não entrega. Um gestor que vê "12 colaboradores"
num painel enquanto a lista mostra 3 já vazou o tamanho do quadro; um
painel que aceita `company` por parâmetro vaza a empresa inteira.
"""

import pytest
from django.utils import timezone

from apps.communications.models import Announcement, AnnouncementRead
from apps.companies.models import Company
from apps.courses.models import Course, CourseProgress
from apps.courses.quiz_models import Option, Question, Quiz, QuizAttempt
from apps.documents.models import Document
from apps.onboarding.models import OnboardingTask
from apps.requests.models import HRRequest
from apps.sectors.models import Sector

HR = "/api/v1/dashboard/hr/"
ME = "/api/v1/dashboard/me/"
TEAM = "/api/v1/dashboard/team/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa Vizinha")


@pytest.fixture
def ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-dash@x.com", "rh_admin", company)


@pytest.fixture
def gestor(db, django_user_model, company, ti):
    g = mk(django_user_model, "gestor-dash@x.com", "gestor", company, sector=ti)
    ti.manager = g
    ti.save()
    return g


@pytest.fixture
def colab(db, django_user_model, company, ti, gestor):
    return mk(
        django_user_model, "colab-dash@x.com", "colaborador", company,
        sector=ti, manager=gestor, hire_date=timezone.localdate(),
    )


@pytest.fixture
def fora_da_equipe(db, django_user_model, company):
    return mk(django_user_model, "fora-dash@x.com", "colaborador", company)


# ══════════════════════════════════════════════════════════════════════════
# Painel do RH (Módulo 14)
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPainelRH:
    def test_colaborador_nao_acessa(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        assert api_client.get(HR).status_code == 403

    def test_gestor_nao_acessa_o_painel_da_empresa(self, api_client, gestor):
        """
        O gestor tem `dashboard.read`, mas o escopo dele é a equipe. Se
        passasse aqui, veria o quadro inteiro da empresa.
        """
        api_client.force_authenticate(user=gestor)
        assert api_client.get(HR).status_code == 403

    def test_rh_acessa(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        resp = api_client.get(HR)
        assert resp.status_code == 200
        assert set(resp.data) == {
            "requests", "documents", "trainings", "onboarding", "communication"
        }

    def test_solicitacoes_contam_por_estado(self, api_client, company, rh, colab):
        HRRequest.objects.create(
            company=company, requester=colab, subject="A", description="."
        )
        concluida = HRRequest.objects.create(
            company=company, requester=colab, subject="B", description="."
        )
        concluida.status = HRRequest.Status.COMPLETED
        concluida.save()

        api_client.force_authenticate(user=rh)
        numeros = api_client.get(HR).data["requests"]
        assert numeros["open"] == 1
        assert numeros["completed"] == 1

    def test_solicitacao_vencida_conta_como_atrasada(
        self, api_client, company, rh, colab
    ):
        vencida = HRRequest.objects.create(
            company=company, requester=colab, subject="Atrasada", description="."
        )
        vencida.due_at = timezone.now() - timezone.timedelta(days=2)
        vencida.save()

        api_client.force_authenticate(user=rh)
        assert api_client.get(HR).data["requests"]["overdue"] == 1

    def test_solicitacao_concluida_nao_conta_como_atrasada(
        self, api_client, company, rh, colab
    ):
        """Vencida e concluída já não exige ação de ninguém."""
        req = HRRequest.objects.create(
            company=company, requester=colab, subject="X", description="."
        )
        req.due_at = timezone.now() - timezone.timedelta(days=2)
        req.status = HRRequest.Status.COMPLETED
        req.save()

        api_client.force_authenticate(user=rh)
        assert api_client.get(HR).data["requests"]["overdue"] == 0

    def test_treinamentos_separam_conclusao_de_aprovacao(
        self, api_client, company, rh, colab
    ):
        """
        Treinamento sem avaliação não tem nota. Misturar as duas taxas faria
        a "aprovação" cair toda vez que alguém concluísse um treinamento
        sem quiz.
        """
        curso = Course.objects.create(title="LGPD", company=company, order=1)
        CourseProgress.objects.create(user=colab, course=curso, status="completed")

        quiz = Quiz.objects.create(course=curso, passing_score=70)
        QuizAttempt.objects.create(
            quiz=quiz, user=colab, attempt_number=1, score=100, passed=True,
            finished_at=timezone.now(),
        )

        api_client.force_authenticate(user=rh)
        numeros = api_client.get(HR).data["trainings"]
        assert numeros["completion_percent"] == 100
        assert numeros["pass_rate"] == 100
        assert numeros["quiz_attempts"] == 1

    def test_tentativa_em_aberto_nao_entra_na_taxa(
        self, api_client, company, rh, colab
    ):
        curso = Course.objects.create(title="LGPD", company=company, order=1)
        quiz = Quiz.objects.create(course=curso, passing_score=70)
        QuizAttempt.objects.create(quiz=quiz, user=colab, attempt_number=1)

        api_client.force_authenticate(user=rh)
        assert api_client.get(HR).data["trainings"]["quiz_attempts"] == 0

    def test_documentos_contam_vencidos_e_publicados(
        self, api_client, company, rh
    ):
        Document.objects.create(
            company=company, title="Vigente", status=Document.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        Document.objects.create(
            company=company, title="Vencido", status=Document.Status.PUBLISHED,
            published_at=timezone.now(),
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        Document.objects.create(company=company, title="Rascunho")

        api_client.force_authenticate(user=rh)
        numeros = api_client.get(HR).data["documents"]
        assert numeros["published"] == 2
        assert numeros["expired"] == 1
        assert numeros["drafts"] == 1

    def test_onboarding_conta_pendencias_e_atrasos(
        self, api_client, company, rh, colab
    ):
        OnboardingTask.objects.create(
            company=company, employee=colab, title="Em dia",
            due_date=timezone.localdate() + timezone.timedelta(days=3),
        )
        OnboardingTask.objects.create(
            company=company, employee=colab, title="Atrasada",
            due_date=timezone.localdate() - timezone.timedelta(days=3),
        )
        OnboardingTask.objects.create(
            company=company, employee=colab, title="Feita", status="completed"
        )
        OnboardingTask.objects.create(
            company=company, employee=colab, title="Cancelada", status="cancelled"
        )

        api_client.force_authenticate(user=rh)
        numeros = api_client.get(HR).data["onboarding"]
        # A cancelada fica de fora do total: não é pendência nem entrega.
        assert numeros["total"] == 3
        assert numeros["pending"] == 2
        assert numeros["overdue"] == 1
        assert numeros["completed"] == 1

    def test_comunicacao_conta_publicados_e_leituras(
        self, api_client, company, rh, colab
    ):
        com = Announcement.objects.create(
            company=company, author=rh, title="Aviso", content=".",
            status=Announcement.Status.PUBLISHED, published_at=timezone.now(),
        )
        AnnouncementRead.objects.create(announcement=com, user=colab)

        api_client.force_authenticate(user=rh)
        numeros = api_client.get(HR).data["communication"]
        assert numeros["published"] == 1
        assert numeros["reads"] == 1

    def test_nao_conta_dados_de_outra_empresa(
        self, api_client, django_user_model, company, empresa_b, rh
    ):
        colab_b = mk(django_user_model, "c@b-dash.com", "colaborador", empresa_b)
        HRRequest.objects.create(
            company=empresa_b, requester=colab_b, subject="Da vizinha", description="."
        )
        Document.objects.create(
            company=empresa_b, title="Da vizinha", status=Document.Status.PUBLISHED
        )

        api_client.force_authenticate(user=rh)
        dados = api_client.get(HR).data
        assert dados["requests"]["open"] == 0
        assert dados["documents"]["published"] == 0

    def test_empresa_vazia_nao_divide_por_zero(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        dados = api_client.get(HR).data
        assert dados["trainings"]["completion_percent"] == 0
        assert dados["communication"]["read_percent"] == 0
        assert dados["documents"]["acceptance_percent"] == 0


# ══════════════════════════════════════════════════════════════════════════
# Home do colaborador (Módulo 15)
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestHomeColaborador:
    def test_traz_o_primeiro_nome(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        resp = api_client.get(ME)
        assert resp.status_code == 200
        assert resp.data["greeting_name"] == colab.full_name.split(" ")[0]

    def test_progresso_do_onboarding(self, api_client, company, colab):
        OnboardingTask.objects.create(
            company=company, employee=colab, title="A", status="completed"
        )
        OnboardingTask.objects.create(company=company, employee=colab, title="B")

        api_client.force_authenticate(user=colab)
        assert api_client.get(ME).data["onboarding"]["percent"] == 50

    def test_conta_tarefas_pendentes_e_atrasadas(self, api_client, company, colab):
        OnboardingTask.objects.create(
            company=company, employee=colab, title="Atrasada",
            due_date=timezone.localdate() - timezone.timedelta(days=1),
        )
        OnboardingTask.objects.create(company=company, employee=colab, title="Sem prazo")

        api_client.force_authenticate(user=colab)
        pendencias = api_client.get(ME).data["pending"]
        assert pendencias["onboarding_tasks"] == 2
        assert pendencias["overdue_tasks"] == 1

    def test_conta_treinamentos_pendentes(self, api_client, company, colab):
        Course.objects.create(title="A", company=company, order=1)
        feito = Course.objects.create(title="B", company=company, order=2)
        CourseProgress.objects.create(user=colab, course=feito, status="completed")

        api_client.force_authenticate(user=colab)
        assert api_client.get(ME).data["pending"]["trainings"] == 1

    def test_conta_documentos_aguardando_aceite(self, api_client, company, colab):
        from apps.documents.models import DocumentVersion

        obrigatorio = Document.objects.create(
            company=company, title="Código de conduta", is_required=True,
            status=Document.Status.PUBLISHED, published_at=timezone.now(),
        )
        DocumentVersion.objects.create(
            document=obrigatorio, version_number=1, original_name="c.pdf",
            extension="pdf", is_active=True,
        )
        opcional = Document.objects.create(
            company=company, title="Opcional", is_required=False,
            status=Document.Status.PUBLISHED, published_at=timezone.now(),
        )
        DocumentVersion.objects.create(
            document=opcional, version_number=1, original_name="o.pdf",
            extension="pdf", is_active=True,
        )

        api_client.force_authenticate(user=colab)
        assert api_client.get(ME).data["pending"]["documents"] == 1

    def test_conta_notificacoes_nao_lidas(self, api_client, colab):
        from apps.notifications.models import Notification

        # O signal de boas-vindas ja deixa uma nao lida no cadastro; zerar
        # aqui deixa o teste medir o que ele diz medir.
        Notification.objects.filter(user=colab).delete()
        Notification.objects.create(user=colab, title="Nova", message=".", read=False)
        Notification.objects.create(user=colab, title="Velha", message=".", read=True)

        api_client.force_authenticate(user=colab)
        assert api_client.get(ME).data["pending"]["notifications"] == 1

    def test_nao_conta_tarefa_de_outra_pessoa(
        self, api_client, company, colab, fora_da_equipe
    ):
        OnboardingTask.objects.create(
            company=company, employee=fora_da_equipe, title="Do colega"
        )
        api_client.force_authenticate(user=colab)
        assert api_client.get(ME).data["pending"]["onboarding_tasks"] == 0

    def test_documento_de_outra_unidade_nao_entra_na_pendencia(
        self, api_client, django_user_model, company, colab
    ):
        """
        A Home usa a MESMA regra de visibilidade da biblioteca. Se
        divergisse, a pessoa veria "1 documento pendente" e não acharia o
        documento em lugar nenhum.
        """
        from apps.units.models import Unit

        from apps.documents.models import DocumentVersion

        norte = Unit.objects.create(company=company, name="Norte")
        doc = Document.objects.create(
            company=company, title="Só do Norte", is_required=True,
            status=Document.Status.PUBLISHED, published_at=timezone.now(),
        )
        DocumentVersion.objects.create(
            document=doc, version_number=1, original_name="n.pdf",
            extension="pdf", is_active=True,
        )
        doc.target_units.set([norte])

        api_client.force_authenticate(user=colab)
        assert api_client.get(ME).data["pending"]["documents"] == 0


# ══════════════════════════════════════════════════════════════════════════
# Painel do gestor (Módulo 16)
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPainelGestor:
    def test_colaborador_comum_nao_acessa(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        assert api_client.get(TEAM).status_code == 403

    def test_gestor_acessa(self, api_client, gestor):
        api_client.force_authenticate(user=gestor)
        assert api_client.get(TEAM).status_code == 200

    def test_conta_apenas_a_propria_equipe(
        self, api_client, gestor, colab, fora_da_equipe
    ):
        """
        O número do painel tem que bater com o da listagem. Divergir já é
        vazar o tamanho do quadro da empresa.
        """
        api_client.force_authenticate(user=gestor)
        assert api_client.get(TEAM).data["team_size"] == 1

    def test_estagio_do_onboarding_e_por_pessoa(
        self, api_client, django_user_model, company, ti, gestor
    ):
        """
        O spec pede "8 concluídos, 3 em andamento, 1 atrasado" — pessoas,
        não tarefas.
        """
        def na_equipe(email):
            return mk(
                django_user_model, email, "colaborador", company,
                sector=ti, manager=gestor,
            )

        pronto = na_equipe("pronto@x.com")
        OnboardingTask.objects.create(
            company=company, employee=pronto, title="A", status="completed"
        )

        andando = na_equipe("andando@x.com")
        OnboardingTask.objects.create(
            company=company, employee=andando, title="A", status="completed"
        )
        OnboardingTask.objects.create(company=company, employee=andando, title="B")

        atrasado = na_equipe("atrasado@x.com")
        OnboardingTask.objects.create(
            company=company, employee=atrasado, title="A",
            due_date=timezone.localdate() - timezone.timedelta(days=5),
        )

        na_equipe("semplano@x.com")

        api_client.force_authenticate(user=gestor)
        numeros = api_client.get(TEAM).data["onboarding"]
        assert numeros == {
            "completed": 1, "in_progress": 1, "overdue": 1, "not_started": 1
        }

    def test_categorias_somam_o_tamanho_da_equipe(
        self, api_client, gestor, colab
    ):
        api_client.force_authenticate(user=gestor)
        dados = api_client.get(TEAM).data
        soma = sum(dados["onboarding"].values())
        assert soma == dados["team_size"]

    def test_atraso_tem_prioridade_sobre_em_andamento(
        self, api_client, company, gestor, colab
    ):
        OnboardingTask.objects.create(
            company=company, employee=colab, title="Feita", status="completed"
        )
        OnboardingTask.objects.create(
            company=company, employee=colab, title="Vencida",
            due_date=timezone.localdate() - timezone.timedelta(days=1),
        )

        api_client.force_authenticate(user=gestor)
        numeros = api_client.get(TEAM).data["onboarding"]
        assert numeros["overdue"] == 1
        assert numeros["in_progress"] == 0

    def test_treinamentos_da_equipe(self, api_client, company, gestor, colab):
        curso = Course.objects.create(title="NR-10", company=company, order=1)
        CourseProgress.objects.create(user=colab, course=curso, status="completed")

        api_client.force_authenticate(user=gestor)
        numeros = api_client.get(TEAM).data["trainings"]
        assert numeros["completion_percent"] == 100

    def test_nao_conta_treinamento_de_quem_esta_fora_da_equipe(
        self, api_client, company, gestor, colab, fora_da_equipe
    ):
        curso = Course.objects.create(title="NR-10", company=company, order=1)
        CourseProgress.objects.create(
            user=fora_da_equipe, course=curso, status="completed"
        )

        api_client.force_authenticate(user=gestor)
        assert api_client.get(TEAM).data["trainings"]["assignments"] == 0

    def test_aniversariantes_nao_expoem_a_data_completa(
        self, api_client, company, gestor, colab
    ):
        """
        O ano revela a idade — informação que um painel de equipe não
        precisa carregar.
        """
        colab.birth_date = timezone.localdate().replace(day=15)
        colab.save()

        api_client.force_authenticate(user=gestor)
        aniversariantes = api_client.get(TEAM).data["birthdays"]
        assert len(aniversariantes) == 1
        assert aniversariantes[0]["birthday"] == colab.birth_date.strftime("%d/%m")
        assert "birth_date" not in aniversariantes[0]
        assert str(colab.birth_date.year) not in str(aniversariantes[0])

    def test_aniversariante_de_outra_equipe_nao_aparece(
        self, api_client, gestor, fora_da_equipe
    ):
        fora_da_equipe.birth_date = timezone.localdate().replace(day=10)
        fora_da_equipe.save()

        api_client.force_authenticate(user=gestor)
        assert api_client.get(TEAM).data["birthdays"] == []

    def test_equipe_vazia_nao_quebra(
        self, api_client, django_user_model, company
    ):
        solitario = mk(django_user_model, "solo-dash@x.com", "gestor", company)
        api_client.force_authenticate(user=solitario)
        resp = api_client.get(TEAM)
        assert resp.status_code == 200
        assert resp.data["team_size"] == 0
        assert resp.data["trainings"]["completion_percent"] == 0
