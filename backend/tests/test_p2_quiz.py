"""
Avaliação de treinamento: quiz, nota mínima e tentativas.

A preocupação central destes testes é o **gabarito**: ele não pode sair do
servidor por nenhum caminho, porque quem o vê acerta tudo na tentativa
seguinte. Vários testes existem só para tentar arrancá-lo.
"""

import pytest

from apps.companies.models import Company
from apps.courses.models import Course, CourseProgress
from apps.courses.quiz_models import Option, Question, Quiz, QuizAttempt
from apps.notifications.models import Notification

COURSES = "/api/v1/courses/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa B")


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-quiz@x.com", "rh_admin", company)


@pytest.fixture
def colab(db, django_user_model, company):
    return mk(django_user_model, "colab-quiz@x.com", "colaborador", company)


@pytest.fixture
def rh_b(db, django_user_model, empresa_b):
    return mk(django_user_model, "rh@b-quiz.com", "rh_admin", empresa_b)


@pytest.fixture
def curso(db, company):
    return Course.objects.create(title="Segurança da Informação", company=company, order=1)


@pytest.fixture
def quiz(db, curso):
    """Duas perguntas, nota mínima 70% — ou seja, exige acertar as duas."""
    q = Quiz.objects.create(course=curso, passing_score=70, max_attempts=3)

    p1 = Question.objects.create(quiz=q, text="O que fazer num incidente?", order=1)
    Option.objects.create(question=p1, text="Avisar o time de segurança", is_correct=True, order=1)
    Option.objects.create(question=p1, text="Ignorar", is_correct=False, order=2)

    p2 = Question.objects.create(quiz=q, text="Senha pode ser compartilhada?", order=2)
    Option.objects.create(question=p2, text="Nunca", is_correct=True, order=1)
    Option.objects.create(question=p2, text="Com o gestor", is_correct=False, order=2)

    return q


def corretas(quiz):
    """Respostas certas, montadas a partir do banco."""
    return {
        str(p.id): [o.id for o in p.options.all() if o.is_correct]
        for p in quiz.questions.all()
    }


def erradas(quiz):
    return {
        str(p.id): [o.id for o in p.options.all() if not o.is_correct]
        for p in quiz.questions.all()
    }


def responder(api_client, user, curso, quiz, respostas):
    api_client.force_authenticate(user=user)
    inicio = api_client.post(f"{COURSES}{curso.id}/quiz/attempts/")
    assert inicio.status_code == 201, inicio.data
    tentativa_id = inicio.data["attempt"]["id"]
    return api_client.post(
        f"{COURSES}{curso.id}/quiz/attempts/{tentativa_id}/submit/",
        {"answers": respostas},
        format="json",
    )


# ══════════════════════════════════════════════════════════════════════════
# O gabarito não vaza
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGabaritoNaoVaza:
    def test_colaborador_nao_ve_qual_alternativa_e_correta(
        self, api_client, colab, curso, quiz
    ):
        api_client.force_authenticate(user=colab)
        resp = api_client.get(f"{COURSES}{curso.id}/quiz/")

        assert resp.status_code == 200
        assert "is_correct" not in str(resp.data)

    def test_iniciar_tentativa_nao_devolve_gabarito(self, api_client, colab, curso, quiz):
        api_client.force_authenticate(user=colab)
        resp = api_client.post(f"{COURSES}{curso.id}/quiz/attempts/")
        assert resp.status_code == 201, resp.data
        assert "is_correct" not in str(resp.data)

    def test_resultado_diz_se_acertou_mas_nao_qual_era_a_certa(
        self, api_client, colab, curso, quiz
    ):
        """
        Se o resultado entregasse a alternativa correta, a primeira
        tentativa viraria o gabarito da segunda.
        """
        resp = responder(api_client, colab, curso, quiz, erradas(quiz))

        assert "is_correct" in str(resp.data)  # o campo do RESULTADO por pergunta
        for resultado in resp.data["answers"]:
            assert set(resultado.keys()) == {
                "id", "question", "question_text", "is_correct"
            }

    def test_rh_ve_o_gabarito(self, api_client, rh, curso, quiz):
        """Quem monta o treinamento precisa ver as respostas certas."""
        api_client.force_authenticate(user=rh)
        resp = api_client.get(f"{COURSES}{curso.id}/quiz/")
        assert resp.status_code == 200, resp.data
        assert "is_correct" in str(resp.data)

    def test_lider_de_setor_de_outro_setor_nao_ve_gabarito(
        self, api_client, django_user_model, company, curso, quiz
    ):
        from apps.sectors.models import Sector

        outro = Sector.objects.create(name="Outro", company=company)
        lider = mk(
            django_user_model, "lider-quiz@x.com", "colaborador", company,
            sector=outro, is_sector_leader=True,
        )
        api_client.force_authenticate(user=lider)
        resp = api_client.get(f"{COURSES}{curso.id}/quiz/")
        assert resp.status_code == 200, resp.data
        assert "is_correct" not in str(resp.data)


# ══════════════════════════════════════════════════════════════════════════
# Correção e nota
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCorrecao:
    def test_todas_certas_aprova(self, api_client, colab, curso, quiz):
        resp = responder(api_client, colab, curso, quiz, corretas(quiz))

        assert resp.status_code == 200
        assert resp.data["score"] == 100
        assert resp.data["passed"] is True

    def test_todas_erradas_reprova(self, api_client, colab, curso, quiz):
        resp = responder(api_client, colab, curso, quiz, erradas(quiz))

        assert resp.data["score"] == 0
        assert resp.data["passed"] is False

    def test_metade_certa_reprova_com_minimo_70(self, api_client, colab, curso, quiz):
        perguntas = list(quiz.questions.all())
        respostas = {
            str(perguntas[0].id): [o.id for o in perguntas[0].options.all() if o.is_correct],
            str(perguntas[1].id): [o.id for o in perguntas[1].options.all() if not o.is_correct],
        }
        resp = responder(api_client, colab, curso, quiz, respostas)

        assert resp.data["score"] == 50
        assert resp.data["passed"] is False

    def test_pergunta_sem_resposta_conta_como_erro(self, api_client, colab, curso, quiz):
        resp = responder(api_client, colab, curso, quiz, {})
        assert resp.data["score"] == 0

    def test_multipla_escolha_exige_o_conjunto_exato(
        self, api_client, colab, curso, company
    ):
        """
        Marcar duas certas de três não é acerto parcial — meio-certo em
        avaliação de compliance não comprova nada.
        """
        q = Quiz.objects.create(course=curso, passing_score=100, max_attempts=5)
        pergunta = Question.objects.create(
            quiz=q, text="Quais são boas práticas?", allows_multiple=True, order=1
        )
        a = Option.objects.create(question=pergunta, text="A", is_correct=True, order=1)
        b = Option.objects.create(question=pergunta, text="B", is_correct=True, order=2)
        Option.objects.create(question=pergunta, text="C", is_correct=False, order=3)

        parcial = responder(api_client, colab, curso, q, {str(pergunta.id): [a.id]})
        assert parcial.data["passed"] is False

        completa = responder(api_client, colab, curso, q, {str(pergunta.id): [a.id, b.id]})
        assert completa.data["passed"] is True

    def test_id_de_alternativa_de_outra_pergunta_e_ignorado(
        self, api_client, colab, curso, quiz
    ):
        """Cliente adulterado não "acerta" mandando ids de outra questão."""
        perguntas = list(quiz.questions.all())
        alheia = perguntas[1].options.first().id

        respostas = {str(perguntas[0].id): [alheia], str(perguntas[1].id): []}
        resp = responder(api_client, colab, curso, quiz, respostas)
        assert resp.data["score"] == 0

    def test_nota_minima_e_respeitada(self, api_client, colab, curso, quiz):
        quiz.passing_score = 50
        quiz.save()

        perguntas = list(quiz.questions.all())
        respostas = {
            str(perguntas[0].id): [o.id for o in perguntas[0].options.all() if o.is_correct],
            str(perguntas[1].id): [],
        }
        resp = responder(api_client, colab, curso, quiz, respostas)
        assert resp.data["score"] == 50
        assert resp.data["passed"] is True


# ══════════════════════════════════════════════════════════════════════════
# Tentativas
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTentativas:
    def test_tentativas_sao_numeradas(self, api_client, colab, curso, quiz):
        primeira = responder(api_client, colab, curso, quiz, erradas(quiz))
        segunda = responder(api_client, colab, curso, quiz, erradas(quiz))

        assert primeira.data["attempt_number"] == 1
        assert segunda.data["attempt_number"] == 2

    def test_esgotar_tentativas_bloqueia(self, api_client, colab, curso, quiz):
        for _ in range(3):
            responder(api_client, colab, curso, quiz, erradas(quiz))

        api_client.force_authenticate(user=colab)
        resp = api_client.post(f"{COURSES}{curso.id}/quiz/attempts/")
        assert resp.status_code == 400
        assert "esgotou" in str(resp.data).lower()

    def test_recarregar_a_pagina_nao_consome_tentativa(self, api_client, colab, curso, quiz):
        """Tentativa aberta e não enviada é reaproveitada."""
        api_client.force_authenticate(user=colab)
        primeira = api_client.post(f"{COURSES}{curso.id}/quiz/attempts/").data["attempt"]["id"]
        segunda = api_client.post(f"{COURSES}{curso.id}/quiz/attempts/").data["attempt"]["id"]

        assert primeira == segunda
        assert QuizAttempt.objects.filter(user=colab, quiz=quiz).count() == 1

    def test_nao_reenvia_tentativa_ja_enviada(self, api_client, colab, curso, quiz):
        api_client.force_authenticate(user=colab)
        tid = api_client.post(f"{COURSES}{curso.id}/quiz/attempts/").data["attempt"]["id"]
        url = f"{COURSES}{curso.id}/quiz/attempts/{tid}/submit/"

        api_client.post(url, {"answers": erradas(quiz)}, format="json")
        resp = api_client.post(url, {"answers": corretas(quiz)}, format="json")
        assert resp.status_code == 400

    def test_aprovado_nao_tenta_de_novo(self, api_client, colab, curso, quiz):
        responder(api_client, colab, curso, quiz, corretas(quiz))

        api_client.force_authenticate(user=colab)
        resp = api_client.post(f"{COURSES}{curso.id}/quiz/attempts/")
        assert resp.status_code == 400
        assert "já foi aprovado" in str(resp.data).lower()

    def test_tentativas_ilimitadas_quando_max_e_zero(self, api_client, colab, curso, quiz):
        quiz.max_attempts = 0
        quiz.save()
        for _ in range(5):
            resp = responder(api_client, colab, curso, quiz, erradas(quiz))
            assert resp.status_code == 200

    def test_nao_envia_respostas_na_tentativa_de_outra_pessoa(
        self, api_client, django_user_model, company, colab, curso, quiz
    ):
        outro = mk(django_user_model, "outro-quiz@x.com", "colaborador", company)
        api_client.force_authenticate(user=colab)
        tid = api_client.post(f"{COURSES}{curso.id}/quiz/attempts/").data["attempt"]["id"]

        api_client.force_authenticate(user=outro)
        resp = api_client.post(
            f"{COURSES}{curso.id}/quiz/attempts/{tid}/submit/",
            {"answers": corretas(quiz)},
            format="json",
        )
        assert resp.status_code == 404

    def test_historico_mostra_as_proprias_tentativas(self, api_client, colab, curso, quiz):
        responder(api_client, colab, curso, quiz, erradas(quiz))
        api_client.force_authenticate(user=colab)
        resp = api_client.get(f"{COURSES}my-attempts/")
        assert resp.data["count"] == 1


# ══════════════════════════════════════════════════════════════════════════
# Conclusão do treinamento
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestConclusao:
    def test_nao_conclui_por_autodeclaracao_quando_ha_avaliacao(
        self, api_client, colab, curso, quiz
    ):
        """
        A mudança central da P2: antes bastava um PATCH para "concluir" um
        treinamento de compliance sem responder nada.
        """
        api_client.force_authenticate(user=colab)
        resp = api_client.patch(
            f"{COURSES}{curso.id}/progress/", {"status": "completed"}, format="json"
        )
        assert resp.status_code == 400
        assert "avaliação" in str(resp.data).lower()

    def test_aprovacao_conclui_o_treinamento(self, api_client, colab, curso, quiz):
        responder(api_client, colab, curso, quiz, corretas(quiz))

        progresso = CourseProgress.objects.get(user=colab, course=curso)
        assert progresso.status == "completed"
        assert progresso.completed_at is not None

    def test_reprovacao_nao_conclui(self, api_client, colab, curso, quiz):
        responder(api_client, colab, curso, quiz, erradas(quiz))
        progresso = CourseProgress.objects.filter(user=colab, course=curso).first()
        assert progresso is None or progresso.status != "completed"

    def test_treinamento_sem_avaliacao_continua_autodeclarado(
        self, api_client, colab, company
    ):
        """Quem não tem quiz mantém o comportamento antigo."""
        simples = Course.objects.create(title="Boas-vindas", company=company, order=2)
        api_client.force_authenticate(user=colab)
        resp = api_client.patch(
            f"{COURSES}{simples.id}/progress/", {"status": "completed"}, format="json"
        )
        assert resp.status_code == 200

    def test_avaliacao_inativa_nao_bloqueia_conclusao(self, api_client, colab, curso, quiz):
        quiz.is_active = False
        quiz.save()
        api_client.force_authenticate(user=colab)
        resp = api_client.patch(
            f"{COURSES}{curso.id}/progress/", {"status": "completed"}, format="json"
        )
        assert resp.status_code == 200

    def test_aprovado_e_notificado(self, api_client, colab, curso, quiz):
        responder(api_client, colab, curso, quiz, corretas(quiz))
        aviso = Notification.objects.filter(
            user=colab, title__startswith="Aprovado em"
        ).first()
        assert aviso is not None
        assert "100%" in aviso.message

    def test_aprovacao_nao_gera_aviso_duplicado(self, api_client, colab, curso, quiz):
        """
        O signal de CourseProgress também avisa conclusão. Sem a supressão,
        a pessoa recebia dois avisos do mesmo fato — e o genérico é o que
        não diz a nota.
        """
        responder(api_client, colab, curso, quiz, corretas(quiz))

        avisos = Notification.objects.filter(user=colab)
        assert avisos.filter(title__startswith="Aprovado em").count() == 1
        assert not avisos.filter(title="Treinamento concluído").exists()

    def test_conclusao_sem_avaliacao_mantem_o_aviso_generico(
        self, api_client, colab, company
    ):
        simples = Course.objects.create(title="Sem prova", company=company, order=3)
        api_client.force_authenticate(user=colab)
        api_client.patch(
            f"{COURSES}{simples.id}/progress/", {"status": "completed"}, format="json"
        )
        assert Notification.objects.filter(
            user=colab, title="Treinamento concluído"
        ).exists()

    def test_reprovado_e_avisado_das_tentativas_restantes(
        self, api_client, colab, curso, quiz
    ):
        responder(api_client, colab, curso, quiz, erradas(quiz))
        aviso = Notification.objects.filter(
            user=colab, title__startswith="Avaliação não aprovada"
        ).first()
        assert aviso is not None
        assert "2 tentativa" in aviso.message


# ══════════════════════════════════════════════════════════════════════════
# Certificados
# ══════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════
# Administração da avaliação
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAdministracao:
    def test_rh_cria_avaliacao(self, api_client, rh, curso):
        api_client.force_authenticate(user=rh)
        resp = api_client.put(
            f"{COURSES}{curso.id}/quiz/",
            {"title": "Prova final", "passing_score": 80, "max_attempts": 2},
            format="json",
        )
        assert resp.status_code == 200
        assert Quiz.objects.filter(course=curso, passing_score=80).exists()

    def test_colaborador_nao_cria_avaliacao(self, api_client, colab, curso):
        api_client.force_authenticate(user=colab)
        resp = api_client.put(f"{COURSES}{curso.id}/quiz/", {"title": "x"}, format="json")
        assert resp.status_code == 403

    def test_nota_minima_fora_da_faixa_e_rejeitada(self, api_client, rh, curso):
        api_client.force_authenticate(user=rh)
        resp = api_client.put(
            f"{COURSES}{curso.id}/quiz/", {"passing_score": 150}, format="json"
        )
        assert resp.status_code == 400

    def test_pergunta_precisa_de_alternativa_correta(self, api_client, rh, curso, quiz):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            f"{COURSES}{curso.id}/quiz/questions/",
            {
                "text": "Sem gabarito",
                "options": [
                    {"text": "A", "is_correct": False},
                    {"text": "B", "is_correct": False},
                ],
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_pergunta_precisa_de_duas_alternativas(self, api_client, rh, curso, quiz):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            f"{COURSES}{curso.id}/quiz/questions/",
            {"text": "Só uma", "options": [{"text": "A", "is_correct": True}]},
            format="json",
        )
        assert resp.status_code == 400

    def test_escolha_unica_nao_aceita_duas_corretas(self, api_client, rh, curso, quiz):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            f"{COURSES}{curso.id}/quiz/questions/",
            {
                "text": "Confusa",
                "allows_multiple": False,
                "options": [
                    {"text": "A", "is_correct": True},
                    {"text": "B", "is_correct": True},
                ],
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_avaliacao_de_outra_empresa_nao_e_alcancavel(
        self, api_client, rh_b, curso, quiz
    ):
        api_client.force_authenticate(user=rh_b)
        assert api_client.get(f"{COURSES}{curso.id}/quiz/").status_code == 404

    def test_avaliacao_sem_perguntas_nao_pode_ser_respondida(
        self, api_client, colab, curso
    ):
        Quiz.objects.create(course=curso, passing_score=70)
        api_client.force_authenticate(user=colab)
        resp = api_client.post(f"{COURSES}{curso.id}/quiz/attempts/")
        assert resp.status_code == 400
