"""
Solicitações de RH: numeração, máquina de estados, atribuição, comentários,
notas internas e anexos seguros.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.companies.models import Company
from apps.notifications.models import Notification
from apps.requests.models import HRRequest, RequestAttachment, RequestHistory

URL = "/api/v1/requests/"
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\ntrailer\n%%EOF\n"
EXE_BYTES = b"MZ\x90\x00" + b"\x00" * 32


def pdf(nome="comprovante.pdf"):
    return SimpleUploadedFile(nome, PDF_BYTES, content_type="application/pdf")


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
    return mk(django_user_model, "rh-fluxo@x.com", "rh_admin", company)


@pytest.fixture
def colab(db, django_user_model, company):
    return mk(django_user_model, "colab-fluxo@x.com", "colaborador", company)


@pytest.fixture
def rh_b(db, django_user_model, empresa_b):
    return mk(django_user_model, "rh@b.com", "rh_admin", empresa_b)


def abrir(api_client, autor, **extra):
    api_client.force_authenticate(user=autor)
    corpo = {"subject": "Assunto", "description": "Detalhes", "category": "other"}
    corpo.update(extra)
    resp = api_client.post(URL, corpo, format="json")
    assert resp.status_code == 201, resp.data
    return resp.data


# ══════════════════════════════════════════════════════════════════════════
# Numeração
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestNumeracao:
    def test_numero_e_sequencial_e_legivel(self, api_client, colab):
        """O número é lido no telefone com o RH — precisa ser ditável."""
        primeira = abrir(api_client, colab)["number"]
        segunda = abrir(api_client, colab)["number"]

        from django.utils import timezone

        ano = timezone.localdate().year
        assert primeira == f"SOL-{ano}-000001"
        assert segunda == f"SOL-{ano}-000002"

    def test_cada_empresa_tem_a_propria_serie(self, api_client, colab, rh_b):
        """Uma empresa não deduz o volume da outra pelo número."""
        from django.utils import timezone

        ano = timezone.localdate().year
        abrir(api_client, colab)
        abrir(api_client, colab)
        numero_b = abrir(api_client, rh_b)["number"]

        assert numero_b == f"SOL-{ano}-000001"

    def test_numero_nao_e_editavel(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        resp = api_client.patch(f"{URL}{rid}/", {"number": "SOL-9999-999999"}, format="json")
        assert HRRequest.objects.get(pk=rid).number != "SOL-9999-999999"


# ══════════════════════════════════════════════════════════════════════════
# Prazo (SLA)
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPrazo:
    def test_prazo_deriva_da_prioridade(self, api_client, colab):
        urgente = abrir(api_client, colab, priority="urgent")
        normal = abrir(api_client, colab, priority="normal")

        assert HRRequest.objects.get(pk=urgente["id"]).due_at < (
            HRRequest.objects.get(pk=normal["id"]).due_at
        )

    def test_atrasada_quando_passa_do_prazo(self, api_client, colab):
        from django.utils import timezone

        rid = abrir(api_client, colab)["id"]
        solicitacao = HRRequest.objects.get(pk=rid)
        solicitacao.due_at = timezone.now() - timezone.timedelta(hours=1)
        solicitacao.save()

        assert solicitacao.is_overdue is True

    def test_concluida_nunca_conta_como_atrasada(self, api_client, colab, rh):
        from django.utils import timezone

        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        api_client.patch(f"{URL}{rid}/status/", {"status": "completed"}, format="json")

        solicitacao = HRRequest.objects.get(pk=rid)
        solicitacao.due_at = timezone.now() - timezone.timedelta(days=5)
        solicitacao.save()
        assert solicitacao.is_overdue is False


# ══════════════════════════════════════════════════════════════════════════
# Máquina de estados
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestFluxoDeStatus:
    def test_fluxo_completo(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)

        for destino in ["in_review", "in_progress", "completed"]:
            resp = api_client.patch(f"{URL}{rid}/status/", {"status": destino}, format="json")
            assert resp.status_code == 200, resp.data
            assert resp.data["status"] == destino

    def test_concluida_marca_as_datas(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        api_client.patch(f"{URL}{rid}/status/", {"status": "completed"}, format="json")

        solicitacao = HRRequest.objects.get(pk=rid)
        assert solicitacao.resolved_at is not None
        assert solicitacao.closed_at is not None

    def test_nao_reabre_solicitacao_concluida(self, api_client, colab, rh):
        """Fechar é terminal — reabrir faria o histórico mentir."""
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        api_client.patch(f"{URL}{rid}/status/", {"status": "completed"}, format="json")

        resp = api_client.patch(f"{URL}{rid}/status/", {"status": "in_progress"}, format="json")
        assert resp.status_code == 400

    def test_nao_reabre_solicitacao_cancelada(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        api_client.patch(f"{URL}{rid}/status/", {"status": "cancelled"}, format="json")

        resp = api_client.patch(f"{URL}{rid}/status/", {"status": "received"}, format="json")
        assert resp.status_code == 400

    def test_colaborador_cancela_a_propria(self, api_client, colab):
        rid = abrir(api_client, colab)["id"]
        resp = api_client.patch(f"{URL}{rid}/status/", {"status": "cancelled"}, format="json")
        assert resp.status_code == 200

    def test_colaborador_nao_conclui_a_propria(self, api_client, colab):
        """Concluir é decisão do RH, não de quem pediu."""
        rid = abrir(api_client, colab)["id"]
        resp = api_client.patch(f"{URL}{rid}/status/", {"status": "completed"}, format="json")
        assert resp.status_code == 403

    def test_status_nao_muda_por_patch_direto(self, api_client, colab, rh):
        """PATCH direto pularia a validação de transição e a notificação."""
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        api_client.patch(f"{URL}{rid}/", {"status": "completed"}, format="json")
        assert HRRequest.objects.get(pk=rid).status == "received"

    def test_cada_transicao_entra_no_historico(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        api_client.patch(f"{URL}{rid}/status/", {"status": "in_progress"}, format="json")

        acoes = list(
            RequestHistory.objects.filter(request_id=rid).values_list("action_type", flat=True)
        )
        assert "created" in acoes
        assert "status_changed" in acoes

    def test_solicitante_e_notificado_da_mudanca(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        api_client.patch(f"{URL}{rid}/status/", {"status": "in_progress"}, format="json")

        assert Notification.objects.filter(
            user=colab, title__startswith="Solicitação SOL-"
        ).exists()

    def test_nao_notifica_quem_fez_a_propria_mudanca(self, api_client, colab):
        rid = abrir(api_client, colab)["id"]
        Notification.objects.filter(user=colab).delete()
        api_client.patch(f"{URL}{rid}/status/", {"status": "cancelled"}, format="json")

        assert not Notification.objects.filter(
            user=colab, title__startswith="Solicitação SOL-"
        ).exists()


# ══════════════════════════════════════════════════════════════════════════
# Atribuição
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAtribuicao:
    def test_rh_atribui_e_o_responsavel_e_notificado(
        self, api_client, django_user_model, company, colab, rh
    ):
        outro_rh = mk(django_user_model, "rh2-fluxo@x.com", "rh_admin", company)
        rid = abrir(api_client, colab)["id"]

        api_client.force_authenticate(user=rh)
        resp = api_client.patch(f"{URL}{rid}/assign/", {"assigned_to": outro_rh.id}, format="json")
        assert resp.status_code == 200
        assert Notification.objects.filter(
            user=outro_rh, title__contains="atribuída a você"
        ).exists()

    def test_atribuicao_entra_no_historico(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        api_client.patch(f"{URL}{rid}/assign/", {"assigned_to": rh.id}, format="json")

        assert RequestHistory.objects.filter(request_id=rid, action_type="assigned").exists()

    def test_nao_atribui_a_usuario_de_outra_empresa(self, api_client, colab, rh, rh_b):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        resp = api_client.patch(f"{URL}{rid}/assign/", {"assigned_to": rh_b.id}, format="json")
        assert resp.status_code == 400

    def test_colaborador_nao_atribui(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        resp = api_client.patch(f"{URL}{rid}/assign/", {"assigned_to": rh.id}, format="json")
        assert resp.status_code == 403

    def test_responsavel_enxerga_a_solicitacao_de_outra_pessoa(
        self, api_client, django_user_model, company, colab, rh
    ):
        """Gestor atribuído acompanha o caso sem ganhar a fila inteira."""
        gestor = mk(django_user_model, "gestor-fluxo@x.com", "gestor", company)
        rid = abrir(api_client, colab)["id"]

        api_client.force_authenticate(user=rh)
        api_client.patch(f"{URL}{rid}/assign/", {"assigned_to": gestor.id}, format="json")

        api_client.force_authenticate(user=gestor)
        assert api_client.get(f"{URL}{rid}/").status_code == 200

    def test_gestor_nao_ve_solicitacao_que_nao_e_dele(self, api_client, django_user_model, company, colab):
        gestor = mk(django_user_model, "g2-fluxo@x.com", "gestor", company)
        rid = abrir(api_client, colab)["id"]

        api_client.force_authenticate(user=gestor)
        assert api_client.get(f"{URL}{rid}/").status_code == 404


# ══════════════════════════════════════════════════════════════════════════
# Comentários e notas internas
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestComentarios:
    def test_colaborador_comenta_e_o_rh_e_avisado(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        Notification.objects.filter(user=rh).delete()

        resp = api_client.post(f"{URL}{rid}/comments/", {"text": "Alguma novidade?"}, format="multipart")
        assert resp.status_code == 201
        assert Notification.objects.filter(user=rh, title__contains="Novo comentário").exists()

    def test_rh_comenta_e_o_solicitante_e_avisado(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        Notification.objects.filter(user=colab).delete()

        api_client.force_authenticate(user=rh)
        api_client.post(f"{URL}{rid}/comments/", {"text": "Estamos vendo."}, format="multipart")
        assert Notification.objects.filter(user=colab, title__contains="Novo comentário").exists()

    def test_nota_interna_nao_aparece_para_o_solicitante(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        api_client.post(
            f"{URL}{rid}/comments/",
            {"text": "Conferir com o jurídico antes", "is_internal": True},
            format="multipart",
        )

        api_client.force_authenticate(user=colab)
        corpo = str(api_client.get(f"{URL}{rid}/").data)
        assert "jurídico" not in corpo

    def test_nota_interna_aparece_para_o_rh(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        api_client.post(
            f"{URL}{rid}/comments/",
            {"text": "Nota reservada", "is_internal": True},
            format="multipart",
        )
        assert "Nota reservada" in str(api_client.get(f"{URL}{rid}/").data)

    def test_nota_interna_nao_notifica_o_solicitante(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        Notification.objects.filter(user=colab).delete()

        api_client.force_authenticate(user=rh)
        api_client.post(
            f"{URL}{rid}/comments/", {"text": "interna", "is_internal": True}, format="multipart"
        )
        assert not Notification.objects.filter(
            user=colab, title__contains="Novo comentário"
        ).exists()

    def test_colaborador_nao_cria_nota_interna(self, api_client, colab):
        rid = abrir(api_client, colab)["id"]
        resp = api_client.post(
            f"{URL}{rid}/comments/", {"text": "x", "is_internal": True}, format="multipart"
        )
        assert resp.status_code == 400

    def test_nao_comenta_em_solicitacao_de_outra_empresa(self, api_client, colab, rh_b):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh_b)
        resp = api_client.post(f"{URL}{rid}/comments/", {"text": "x"}, format="multipart")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════
# Anexos
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAnexos:
    def _comentar_com_anexo(self, api_client, autor, rid, arquivo=None):
        api_client.force_authenticate(user=autor)
        return api_client.post(
            f"{URL}{rid}/comments/",
            {"text": "Segue o comprovante", "attachments": [arquivo or pdf()]},
            format="multipart",
        )

    def test_anexa_arquivo_valido(self, api_client, colab):
        rid = abrir(api_client, colab)["id"]
        resp = self._comentar_com_anexo(api_client, colab, rid)

        assert resp.status_code == 201
        assert len(resp.data["attachments"]) == 1
        assert resp.data["attachments"][0]["original_name"] == "comprovante.pdf"

    def test_recusa_executavel_disfarcado(self, api_client, colab):
        rid = abrir(api_client, colab)["id"]
        disfarcado = SimpleUploadedFile("nota.pdf", EXE_BYTES, content_type="application/pdf")
        resp = self._comentar_com_anexo(api_client, colab, rid, disfarcado)
        assert resp.status_code == 400

    def test_nome_do_arquivo_nunca_vira_caminho(self, api_client, colab):
        rid = abrir(api_client, colab)["id"]
        malicioso = SimpleUploadedFile(
            "../../../etc/passwd.pdf", PDF_BYTES, content_type="application/pdf"
        )
        self._comentar_com_anexo(api_client, colab, rid, malicioso)

        anexo = RequestAttachment.objects.get()
        assert ".." not in anexo.file.name
        assert anexo.file.name.startswith("company_")

    def test_baixa_o_proprio_anexo(self, api_client, colab):
        rid = abrir(api_client, colab)["id"]
        anexo_id = self._comentar_com_anexo(api_client, colab, rid).data["attachments"][0]["id"]

        resp = api_client.get(f"{URL}{rid}/attachments/{anexo_id}/download/")
        assert resp.status_code == 200
        assert b"".join(resp.streaming_content) == PDF_BYTES

    def test_outra_empresa_nao_baixa_mesmo_com_o_id(self, api_client, colab, rh_b):
        rid = abrir(api_client, colab)["id"]
        anexo_id = self._comentar_com_anexo(api_client, colab, rid).data["attachments"][0]["id"]

        api_client.force_authenticate(user=rh_b)
        resp = api_client.get(f"{URL}{rid}/attachments/{anexo_id}/download/")
        assert resp.status_code == 404

    def test_colega_sem_acesso_a_solicitacao_nao_baixa(
        self, api_client, django_user_model, company, colab
    ):
        outro = mk(django_user_model, "curioso@x.com", "colaborador", company)
        rid = abrir(api_client, colab)["id"]
        anexo_id = self._comentar_com_anexo(api_client, colab, rid).data["attachments"][0]["id"]

        api_client.force_authenticate(user=outro)
        assert api_client.get(f"{URL}{rid}/attachments/{anexo_id}/download/").status_code == 404

    def test_anexo_de_nota_interna_nao_vaza_para_o_solicitante(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            f"{URL}{rid}/comments/",
            {"text": "reservado", "is_internal": True, "attachments": [pdf("interno.pdf")]},
            format="multipart",
        )
        anexo_id = resp.data["attachments"][0]["id"]

        api_client.force_authenticate(user=colab)
        assert api_client.get(f"{URL}{rid}/attachments/{anexo_id}/download/").status_code == 404

    def test_listagem_nao_expone_o_caminho_do_arquivo(self, api_client, colab):
        rid = abrir(api_client, colab)["id"]
        self._comentar_com_anexo(api_client, colab, rid)

        corpo = str(api_client.get(f"{URL}{rid}/").data)
        assert "company_" not in corpo


# ══════════════════════════════════════════════════════════════════════════
# Isolamento e filtros
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIsolamentoEFiltros:
    def test_rh_nao_ve_solicitacao_de_outra_empresa(self, api_client, colab, rh_b, rh):
        abrir(api_client, colab)
        api_client.force_authenticate(user=rh_b)
        assert api_client.get(URL).data["count"] == 0

    def test_colaborador_so_ve_as_proprias(
        self, api_client, django_user_model, company, colab
    ):
        outro = mk(django_user_model, "outro-fluxo@x.com", "colaborador", company)
        abrir(api_client, colab)
        abrir(api_client, outro)

        api_client.force_authenticate(user=colab)
        assert api_client.get(URL).data["count"] == 1

    def test_rh_ve_a_fila_inteira(self, api_client, django_user_model, company, colab, rh):
        outro = mk(django_user_model, "outro2-fluxo@x.com", "colaborador", company)
        abrir(api_client, colab)
        abrir(api_client, outro)

        api_client.force_authenticate(user=rh)
        assert api_client.get(URL).data["count"] == 2

    def test_filtro_abertas(self, api_client, colab, rh):
        rid = abrir(api_client, colab)["id"]
        abrir(api_client, colab)

        api_client.force_authenticate(user=rh)
        api_client.patch(f"{URL}{rid}/status/", {"status": "completed"}, format="json")
        assert api_client.get(URL, {"status": "open"}).data["count"] == 1

    def test_filtro_por_prioridade(self, api_client, colab, rh):
        abrir(api_client, colab, priority="urgent")
        abrir(api_client, colab, priority="low")

        api_client.force_authenticate(user=rh)
        assert api_client.get(URL, {"priority": "urgent"}).data["count"] == 1

    def test_filtro_invalido_retorna_400_nao_500(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        assert api_client.get(URL, {"assigned_to": "abc"}).status_code == 400

    def test_listagem_e_paginada(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        resp = api_client.get(URL)
        assert "count" in resp.data and "results" in resp.data

    def test_nao_e_possivel_excluir_solicitacao(self, api_client, colab, rh):
        """Histórico de atendimento não se apaga pela API."""
        rid = abrir(api_client, colab)["id"]
        api_client.force_authenticate(user=rh)
        assert api_client.delete(f"{URL}{rid}/").status_code == 405
