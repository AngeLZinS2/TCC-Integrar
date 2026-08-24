"""
Infraestrutura assíncrona: notificações, agendamento, tarefas periódicas.

Os testes rodam com `CELERY_TASK_ALWAYS_EAGER`, então a task executa inline
e qualquer exceção sobe para o teste em vez de sumir dentro do worker.
"""

import pytest
from django.core import mail
from django.utils import timezone

from apps.communications.models import Announcement
from apps.communications.tasks import (
    expirar_comunicados,
    notificar_publico_alvo,
    publicar_agendados,
)
from apps.companies.models import Company
from apps.documents.models import Document
from apps.documents.tasks import (
    arquivar_documentos_expirados,
    avisar_documentos_obrigatorios_pendentes,
)
from apps.notifications.channels import Category, notify, notify_company
from apps.notifications.models import Notification, NotificationPreference
from apps.sectors.models import Position, Sector

COMMS_URL = "/api/v1/communications/"
PREFS_URL = "/api/v1/notifications/preferences/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-async@x.com", "rh_admin", company)


@pytest.fixture
def colab(db, django_user_model, company):
    return mk(django_user_model, "colab-async@x.com", "colaborador", company)


# ══════════════════════════════════════════════════════════════════════════
# Serviço de notificação
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestServicoDeNotificacao:
    def test_notifica_um_usuario(self, colab):
        assert notify(colab, "Título", "Corpo") == 1
        assert Notification.objects.filter(user=colab, title="Título").exists()

    def test_notifica_varios_em_uma_query(self, django_user_model, company, colab):
        outro = mk(django_user_model, "outro@x.com", "colaborador", company)
        assert notify([colab, outro], "Aviso", "x") == 2

    def test_ignora_usuario_inativo(self, colab):
        colab.is_active = False
        colab.save()
        assert notify(colab, "T", "C") == 0

    def test_email_vai_para_a_fila_e_e_enviado(self, colab):
        mail.outbox.clear()
        notify(colab, "Com e-mail", "corpo", email=True)
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [colab.email]

    def test_sem_email_nao_envia_nada(self, colab):
        mail.outbox.clear()
        notify(colab, "Só in-app", "corpo", email=False)
        assert mail.outbox == []

    def test_um_email_por_destinatario_sem_copia_visivel(
        self, django_user_model, company, colab
    ):
        """Um e-mail interno não pode revelar a lista de quem mais recebeu."""
        outro = mk(django_user_model, "outro2@x.com", "colaborador", company)
        mail.outbox.clear()
        notify([colab, outro], "Aviso", "x", email=True)

        assert len(mail.outbox) == 2
        for mensagem in mail.outbox:
            assert len(mensagem.to) == 1

    def test_notify_company_alcanca_a_empresa_toda(self, company, rh, colab):
        assert notify_company(company, "Geral", "x") >= 2

    def test_notify_company_filtra_por_papel(self, company, rh, colab):
        enviados = notify_company(company, "Só RH", "x", roles=["rh_admin"])
        assert enviados == 1
        assert Notification.objects.filter(user=rh, title="Só RH").exists()
        assert not Notification.objects.filter(user=colab, title="Só RH").exists()

    def test_owner_nunca_entra_em_notificacao_de_empresa(
        self, company, owner_user, colab
    ):
        notify_company(company, "Da empresa", "x")
        assert not Notification.objects.filter(user=owner_user).exists()


@pytest.mark.django_db
class TestPreferenciasDeNotificacao:
    def test_sem_preferencia_salva_recebe_tudo(self, colab):
        """Usuário novo não pode ficar sem aviso até achar a tela."""
        assert not NotificationPreference.objects.filter(user=colab).exists()
        assert notify(colab, "T", "C", category=Category.EVENT) == 1

    def test_desligar_categoria_bloqueia_in_app(self, colab):
        NotificationPreference.objects.create(user=colab, app_events=False)
        assert notify(colab, "Evento", "x", category=Category.EVENT) == 0

    def test_desligar_uma_categoria_nao_afeta_as_outras(self, colab):
        NotificationPreference.objects.create(user=colab, app_events=False)
        assert notify(colab, "Doc", "x", category=Category.DOCUMENT) == 1

    def test_desligar_email_nao_desliga_in_app(self, colab):
        NotificationPreference.objects.create(user=colab, email_documents=False)
        mail.outbox.clear()
        assert notify(colab, "Doc", "x", category=Category.DOCUMENT, email=True) == 1
        assert mail.outbox == []

    def test_notificacao_critica_ignora_preferencia(self, colab):
        """Dá para desligar aviso de evento, não "sua empresa foi suspensa"."""
        NotificationPreference.objects.create(user=colab, app_events=False)
        assert notify(colab, "Urgente", "x", category=Category.EVENT, critical=True) == 1

    def test_api_cria_preferencia_na_primeira_visita(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        resp = api_client.get(PREFS_URL)
        assert resp.status_code == 200
        assert resp.data["app_announcements"] is True
        assert NotificationPreference.objects.filter(user=colab).exists()

    def test_api_salva_alteracao(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        resp = api_client.patch(PREFS_URL, {"email_events": True}, format="json")
        assert resp.status_code == 200
        assert NotificationPreference.objects.get(user=colab).email_events is True

    def test_preferencia_e_sempre_do_proprio_usuario(
        self, api_client, django_user_model, company, colab
    ):
        """Não há como alterar a preferência de outra pessoa: não se passa id."""
        outro = mk(django_user_model, "alvo@x.com", "colaborador", company)
        NotificationPreference.objects.create(user=outro, app_events=True)

        api_client.force_authenticate(user=colab)
        api_client.patch(PREFS_URL, {"app_events": False}, format="json")

        assert NotificationPreference.objects.get(user=outro).app_events is True
        assert NotificationPreference.objects.get(user=colab).app_events is False


# ══════════════════════════════════════════════════════════════════════════
# Agendamento e publicação de comunicados
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPublicacaoDeComunicados:
    def test_criar_sem_data_nasce_rascunho(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        resp = api_client.post(COMMS_URL, {"title": "T", "content": "C"}, format="json")
        assert resp.status_code == 201
        assert Announcement.objects.get(pk=resp.data["id"]).status == "draft"

    def test_rascunho_nao_aparece_para_o_colaborador(self, api_client, rh, colab):
        api_client.force_authenticate(user=rh)
        api_client.post(COMMS_URL, {"title": "Rascunho", "content": "C"}, format="json")

        api_client.force_authenticate(user=colab)
        titulos = [x["title"] for x in api_client.get(COMMS_URL).data["results"]]
        assert "Rascunho" not in titulos

    def test_publicar_torna_visivel_e_notifica(self, api_client, rh, colab):
        api_client.force_authenticate(user=rh)
        cid = api_client.post(COMMS_URL, {"title": "Novidade", "content": "C"}, format="json").data["id"]

        resp = api_client.post(f"{COMMS_URL}{cid}/publish/")
        assert resp.status_code == 200

        api_client.force_authenticate(user=colab)
        titulos = [x["title"] for x in api_client.get(COMMS_URL).data["results"]]
        assert "Novidade" in titulos
        assert Notification.objects.filter(user=colab, title__contains="Novidade").exists()

    def test_publicar_duas_vezes_e_recusado(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        cid = api_client.post(COMMS_URL, {"title": "T", "content": "C"}, format="json").data["id"]
        api_client.post(f"{COMMS_URL}{cid}/publish/")
        assert api_client.post(f"{COMMS_URL}{cid}/publish/").status_code == 400

    def test_colaborador_nao_publica(self, api_client, rh, colab):
        api_client.force_authenticate(user=rh)
        cid = api_client.post(COMMS_URL, {"title": "T", "content": "C"}, format="json").data["id"]

        api_client.force_authenticate(user=colab)
        assert api_client.post(f"{COMMS_URL}{cid}/publish/").status_code == 403

    def test_data_futura_agenda_em_vez_de_publicar(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        futuro = (timezone.now() + timezone.timedelta(days=1)).isoformat()
        resp = api_client.post(
            COMMS_URL, {"title": "Amanhã", "content": "C", "publish_at": futuro}, format="json"
        )
        assert Announcement.objects.get(pk=resp.data["id"]).status == "scheduled"

    def test_expiracao_antes_da_publicacao_e_rejeitada(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        agora = timezone.now()
        resp = api_client.post(
            COMMS_URL,
            {
                "title": "T", "content": "C",
                "publish_at": (agora + timezone.timedelta(days=2)).isoformat(),
                "expires_at": (agora + timezone.timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_status_nao_e_alteravel_por_patch(self, api_client, rh):
        """Publicar por PATCH pularia a notificação do público-alvo."""
        api_client.force_authenticate(user=rh)
        cid = api_client.post(COMMS_URL, {"title": "T", "content": "C"}, format="json").data["id"]
        api_client.patch(f"{COMMS_URL}{cid}/", {"status": "published"}, format="json")
        assert Announcement.objects.get(pk=cid).status == "draft"


@pytest.mark.django_db
class TestTasksDeComunicado:
    def _agendado(self, company, autor, quando, titulo="Agendado"):
        return Announcement.objects.create(
            company=company, author=autor, title=titulo, content="C",
            status=Announcement.Status.SCHEDULED, publish_at=quando,
        )

    def test_publica_o_que_ja_venceu(self, company, rh):
        passado = timezone.now() - timezone.timedelta(minutes=10)
        comunicado = self._agendado(company, rh, passado)

        assert publicar_agendados() == 1
        comunicado.refresh_from_db()
        assert comunicado.status == "published"
        assert comunicado.published_at is not None

    def test_nao_publica_antes_da_hora(self, company, rh):
        futuro = timezone.now() + timezone.timedelta(hours=2)
        comunicado = self._agendado(company, rh, futuro)

        assert publicar_agendados() == 0
        comunicado.refresh_from_db()
        assert comunicado.status == "scheduled"

    def test_rodar_duas_vezes_nao_publica_em_duplicidade(self, company, rh):
        """O Beat roda de 5 em 5 min — não pode reprocessar o já publicado."""
        passado = timezone.now() - timezone.timedelta(minutes=10)
        self._agendado(company, rh, passado)

        assert publicar_agendados() == 1
        assert publicar_agendados() == 0

    def test_notificacao_do_publico_alvo_nao_duplica(self, company, rh, colab):
        comunicado = Announcement.objects.create(
            company=company, author=rh, title="Aviso", content="C",
            status=Announcement.Status.PUBLISHED, published_at=timezone.now(),
        )
        notificar_publico_alvo(comunicado.pk)
        notificar_publico_alvo(comunicado.pk)

        assert Notification.objects.filter(
            user=colab, title__contains="Aviso"
        ).count() == 1

    def test_notificacao_respeita_a_segmentacao(
        self, django_user_model, company, rh
    ):
        ti = Sector.objects.create(name="TI", company=company)
        dev = Position.objects.create(name="Dev", sector=ti)
        qa = Position.objects.create(name="QA", sector=ti)

        alvo = mk(django_user_model, "dev-n@x.com", "colaborador", company,
                  sector=ti, position=dev)
        fora = mk(django_user_model, "qa-n@x.com", "colaborador", company,
                  sector=ti, position=qa)

        comunicado = Announcement.objects.create(
            company=company, author=rh, title="Devs", content="C",
            status=Announcement.Status.PUBLISHED, published_at=timezone.now(),
        )
        comunicado.target_sectors.add(ti)
        comunicado.target_positions.add(dev)

        notificar_publico_alvo(comunicado.pk)
        assert Notification.objects.filter(user=alvo, title__contains="Devs").exists()
        assert not Notification.objects.filter(user=fora, title__contains="Devs").exists()

    def test_expirar_tira_do_mural(self, company, rh, api_client, colab):
        comunicado = Announcement.objects.create(
            company=company, author=rh, title="Vencido", content="C",
            status=Announcement.Status.PUBLISHED,
            published_at=timezone.now() - timezone.timedelta(days=5),
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        assert expirar_comunicados() == 1
        comunicado.refresh_from_db()
        assert comunicado.status == "expired"

        api_client.force_authenticate(user=colab)
        titulos = [x["title"] for x in api_client.get(COMMS_URL).data["results"]]
        assert "Vencido" not in titulos


# ══════════════════════════════════════════════════════════════════════════
# Tarefas periódicas de documentos
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTasksDeDocumento:
    def _publicado(self, company, autor, titulo="Política", obrigatorio=True, expira=None):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.documents.models import DocumentVersion

        documento = Document.objects.create(
            company=company, title=titulo, is_required=obrigatorio,
            status=Document.Status.PUBLISHED, published_at=timezone.now(),
            expires_at=expira,
        )
        DocumentVersion.objects.create(
            document=documento, version_number=1, extension="txt",
            file=SimpleUploadedFile("p.txt", b"conteudo"),
            created_by=autor, is_active=True,
        )
        return documento

    def test_avisa_quem_nao_aceitou(self, company, rh, colab):
        documento = self._publicado(company, rh)
        assert avisar_documentos_obrigatorios_pendentes() >= 1
        assert Notification.objects.filter(
            user=colab, title__contains=documento.title
        ).exists()

    def test_nao_avisa_duas_vezes_no_mesmo_dia(self, company, rh, colab):
        """Idempotência: o Beat roda diariamente, sem repetir o lembrete."""
        self._publicado(company, rh)
        avisar_documentos_obrigatorios_pendentes()
        filtro = dict(user=colab, title__startswith="Documento pendente")
        antes = Notification.objects.filter(**filtro).count()
        assert antes == 1

        avisar_documentos_obrigatorios_pendentes()
        assert Notification.objects.filter(**filtro).count() == antes

    def test_nao_avisa_quem_ja_aceitou(self, company, rh, colab):
        from apps.documents.models import DocumentAcceptance

        documento = self._publicado(company, rh)
        DocumentAcceptance.objects.create(
            document_version=documento.active_version(), user=colab
        )
        avisar_documentos_obrigatorios_pendentes()
        assert not Notification.objects.filter(
            user=colab, title__startswith="Documento pendente"
        ).exists()

    def test_documento_informativo_nao_gera_lembrete(self, company, rh, colab):
        self._publicado(company, rh, obrigatorio=False)
        avisar_documentos_obrigatorios_pendentes()
        assert not Notification.objects.filter(
            user=colab, title__startswith="Documento pendente"
        ).exists()

    def test_nao_avisa_colaborador_de_outra_empresa(
        self, django_user_model, company, rh
    ):
        outra = Company.objects.create(name="Outra")
        de_fora = mk(django_user_model, "fora-doc@x.com", "colaborador", outra)
        self._publicado(company, rh)

        avisar_documentos_obrigatorios_pendentes()
        assert not Notification.objects.filter(
            user=de_fora, title__startswith="Documento pendente"
        ).exists()

    def test_arquiva_documento_vencido(self, company, rh):
        documento = self._publicado(
            company, rh, expira=timezone.now() - timezone.timedelta(days=1)
        )
        assert arquivar_documentos_expirados() == 1
        documento.refresh_from_db()
        assert documento.status == "archived"

    def test_nao_arquiva_documento_dentro_da_validade(self, company, rh):
        documento = self._publicado(
            company, rh, expira=timezone.now() + timezone.timedelta(days=30)
        )
        assert arquivar_documentos_expirados() == 0
        documento.refresh_from_db()
        assert documento.status == "published"

    def test_arquivado_preserva_o_historico_de_aceites(self, company, rh, colab):
        from apps.documents.models import DocumentAcceptance

        documento = self._publicado(
            company, rh, expira=timezone.now() - timezone.timedelta(days=1)
        )
        DocumentAcceptance.objects.create(
            document_version=documento.active_version(), user=colab
        )
        arquivar_documentos_expirados()

        assert DocumentAcceptance.objects.filter(user=colab).exists()


# ══════════════════════════════════════════════════════════════════════════
# Healthcheck
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestHealthcheck:
    URL = "/api/v1/health/"

    def test_responde_sem_autenticacao(self, api_client):
        """É consultado pelo Docker antes de haver sessão."""
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data["status"] == "ok"

    def test_reporta_banco_e_cache(self, api_client):
        checks = api_client.get(self.URL).data["checks"]
        assert checks["database"] == "ok"
        assert checks["cache"] == "ok"

    def test_worker_marcado_como_desabilitado_em_modo_eager(self, api_client):
        """Sem fila configurada, o worker não é requisito."""
        assert api_client.get(self.URL).data["checks"]["worker"] == "disabled"

    def test_nao_expoe_detalhe_de_infraestrutura(self, api_client):
        corpo = str(api_client.get(self.URL).data)
        assert "postgres" not in corpo.lower()
        assert "redis://" not in corpo
