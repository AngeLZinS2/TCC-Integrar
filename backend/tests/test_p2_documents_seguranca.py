"""
Segurança de documentos: upload, download autorizado, versionamento e aceite.

O Módulo 27 pede atenção especial a ARQUIVOS: mesmo conhecendo o id, um
usuário da Empresa A não pode baixar arquivo da Empresa B. É o que a maior
parte destes testes exercita.
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.common.uploads import build_storage_path, extension_of, sniff_mime
from apps.companies.models import Company
from apps.documents.models import Document, DocumentAcceptance, DocumentVersion

DOCS_URL = "/api/v1/documents/"

# Bytes reais, não texto solto: a validação lê a assinatura do arquivo.
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
EXE_BYTES = b"MZ\x90\x00" + b"\x00" * 64


def pdf(nome="politica.pdf"):
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
    return mk(django_user_model, "rh-doc@x.com", "rh_admin", company)


@pytest.fixture
def colaborador(db, django_user_model, company):
    return mk(django_user_model, "colab-doc@x.com", "colaborador", company)


@pytest.fixture
def rh_b(db, django_user_model, empresa_b):
    return mk(django_user_model, "rh@empresab.com", "rh_admin", empresa_b)


def criar_documento_publicado(api_client, autor, titulo="Política", obrigatorio=False):
    """Cria + faz upload + publica, devolvendo (documento, versão)."""
    api_client.force_authenticate(user=autor)
    resp = api_client.post(
        DOCS_URL, {"title": titulo, "is_required": obrigatorio}, format="json"
    )
    assert resp.status_code == 201, resp.data
    doc_id = resp.data["id"]

    resp = api_client.post(
        f"{DOCS_URL}{doc_id}/versions/", {"file": pdf()}, format="multipart"
    )
    assert resp.status_code == 201, resp.data

    resp = api_client.post(f"{DOCS_URL}{doc_id}/publish/")
    assert resp.status_code == 200, resp.data

    documento = Document.objects.get(pk=doc_id)
    return documento, documento.versions.get(is_active=True)


# ══════════════════════════════════════════════════════════════════════════
# Validação do arquivo enviado
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestValidacaoDeUpload:
    def test_aceita_pdf_valido(self, api_client, rh):
        documento, versao = criar_documento_publicado(api_client, rh)
        assert versao.mime_type == "application/pdf"
        assert versao.size_bytes > 0
        assert len(versao.checksum) == 64

    def test_recusa_extensao_fora_da_allowlist(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        doc_id = api_client.post(DOCS_URL, {"title": "x"}, format="json").data["id"]
        arquivo = SimpleUploadedFile("virus.exe", EXE_BYTES, content_type="application/pdf")

        resp = api_client.post(
            f"{DOCS_URL}{doc_id}/versions/", {"file": arquivo}, format="multipart"
        )
        assert resp.status_code == 400

    def test_recusa_executavel_disfarcado_de_pdf(self, api_client, rh):
        """
        O ataque clássico: renomear .exe para .pdf e declarar o content-type
        certo. Só ler os bytes pega isso.
        """
        api_client.force_authenticate(user=rh)
        doc_id = api_client.post(DOCS_URL, {"title": "x"}, format="json").data["id"]
        disfarcado = SimpleUploadedFile(
            "inocente.pdf", EXE_BYTES, content_type="application/pdf"
        )

        resp = api_client.post(
            f"{DOCS_URL}{doc_id}/versions/", {"file": disfarcado}, format="multipart"
        )
        assert resp.status_code == 400
        assert "não corresponde" in str(resp.data)

    def test_recusa_arquivo_vazio(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        doc_id = api_client.post(DOCS_URL, {"title": "x"}, format="json").data["id"]
        vazio = SimpleUploadedFile("vazio.pdf", b"", content_type="application/pdf")

        resp = api_client.post(
            f"{DOCS_URL}{doc_id}/versions/", {"file": vazio}, format="multipart"
        )
        assert resp.status_code == 400

    def test_recusa_arquivo_acima_do_limite(self, api_client, rh, monkeypatch):
        from apps.common import uploads

        monkeypatch.setattr(uploads, "MAX_UPLOAD_BYTES", 100)
        api_client.force_authenticate(user=rh)
        doc_id = api_client.post(DOCS_URL, {"title": "x"}, format="json").data["id"]
        grande = SimpleUploadedFile(
            "grande.pdf", PDF_BYTES + b"\x00" * 500, content_type="application/pdf"
        )

        resp = api_client.post(
            f"{DOCS_URL}{doc_id}/versions/", {"file": grande}, format="multipart"
        )
        assert resp.status_code == 400
        assert "limite" in str(resp.data).lower()


@pytest.mark.django_db
class TestNomeDeArquivoSeguro:
    def test_path_traversal_no_nome_nao_escapa_do_diretorio(self, api_client, rh):
        """`../../etc/passwd.pdf` não pode virar caminho — o nome é descartado."""
        api_client.force_authenticate(user=rh)
        doc_id = api_client.post(DOCS_URL, {"title": "x"}, format="json").data["id"]
        malicioso = SimpleUploadedFile(
            "../../../etc/passwd.pdf", PDF_BYTES, content_type="application/pdf"
        )

        resp = api_client.post(
            f"{DOCS_URL}{doc_id}/versions/", {"file": malicioso}, format="multipart"
        )
        assert resp.status_code == 201

        versao = DocumentVersion.objects.get(document_id=doc_id)
        assert ".." not in versao.file.name
        assert "etc" not in versao.file.name
        assert versao.file.name.startswith("company_")

    def test_arquivo_fica_particionado_por_empresa(self, api_client, rh, company):
        _, versao = criar_documento_publicado(api_client, rh)
        assert versao.file.name.startswith(f"company_{company.id}/documents/")

    def test_nome_interno_nao_reaproveita_o_nome_enviado(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        doc_id = api_client.post(DOCS_URL, {"title": "x"}, format="json").data["id"]
        api_client.post(
            f"{DOCS_URL}{doc_id}/versions/",
            {"file": pdf("meu documento confidencial.pdf")},
            format="multipart",
        )
        versao = DocumentVersion.objects.get(document_id=doc_id)
        assert "confidencial" not in versao.file.name
        # Mas o original fica guardado para exibição.
        assert versao.original_name == "meu documento confidencial.pdf"

    def test_helpers_de_nome(self):
        assert extension_of("../../evil.PDF") == "pdf"
        assert extension_of("sem_extensao") == ""
        assert sniff_mime(PDF_BYTES) == "application/pdf"
        assert sniff_mime(PNG_BYTES) == "image/png"
        assert build_storage_path(7, "documents", "pdf").startswith("company_7/documents/")


# ══════════════════════════════════════════════════════════════════════════
# Download autorizado — o coração do Módulo 27
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestDownloadAutorizado:
    def test_colaborador_da_empresa_baixa_documento_publicado(
        self, api_client, rh, colaborador
    ):
        documento, versao = criar_documento_publicado(api_client, rh)

        api_client.force_authenticate(user=colaborador)
        resp = api_client.get(f"{DOCS_URL}{documento.id}/versions/{versao.id}/download/")
        assert resp.status_code == 200
        assert b"".join(resp.streaming_content) == PDF_BYTES

    def test_usuario_de_outra_empresa_nao_baixa_mesmo_sabendo_o_id(
        self, api_client, rh, rh_b
    ):
        """O cenário exato do Módulo 27: id conhecido, download bloqueado."""
        documento, versao = criar_documento_publicado(api_client, rh)

        api_client.force_authenticate(user=rh_b)
        resp = api_client.get(f"{DOCS_URL}{documento.id}/versions/{versao.id}/download/")
        assert resp.status_code == 404

    def test_sem_autenticacao_nao_baixa(self, api_client, rh):
        documento, versao = criar_documento_publicado(api_client, rh)
        api_client.force_authenticate(user=None)
        resp = api_client.get(f"{DOCS_URL}{documento.id}/versions/{versao.id}/download/")
        assert resp.status_code == 401

    def test_colaborador_nao_baixa_documento_ainda_em_rascunho(
        self, api_client, rh, colaborador
    ):
        api_client.force_authenticate(user=rh)
        doc_id = api_client.post(DOCS_URL, {"title": "Rascunho"}, format="json").data["id"]
        api_client.post(f"{DOCS_URL}{doc_id}/versions/", {"file": pdf()}, format="multipart")
        versao = DocumentVersion.objects.get(document_id=doc_id)

        api_client.force_authenticate(user=colaborador)
        resp = api_client.get(f"{DOCS_URL}{doc_id}/versions/{versao.id}/download/")
        assert resp.status_code == 404

    def test_versao_de_outro_documento_nao_e_servida(self, api_client, rh):
        """Trocar o version_id na URL não pode alcançar outro documento."""
        doc_a, versao_a = criar_documento_publicado(api_client, rh, "A")
        doc_b, versao_b = criar_documento_publicado(api_client, rh, "B")

        api_client.force_authenticate(user=rh)
        resp = api_client.get(f"{DOCS_URL}{doc_a.id}/versions/{versao_b.id}/download/")
        assert resp.status_code == 404

    def test_download_e_registrado_na_auditoria(self, api_client, rh, colaborador):
        from apps.audit.models import AuditLog

        documento, versao = criar_documento_publicado(api_client, rh)
        api_client.force_authenticate(user=colaborador)
        api_client.get(f"{DOCS_URL}{documento.id}/versions/{versao.id}/download/")

        assert AuditLog.objects.filter(
            resource_type="document_download", actor=colaborador
        ).exists()

    def test_listagem_nao_expone_o_caminho_do_arquivo(self, api_client, rh, colaborador):
        documento, versao = criar_documento_publicado(api_client, rh)
        api_client.force_authenticate(user=colaborador)
        corpo = str(api_client.get(DOCS_URL).data)

        assert versao.file.name not in corpo
        assert "company_" not in corpo


# ══════════════════════════════════════════════════════════════════════════
# Versionamento
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestVersionamento:
    def test_segunda_versao_incrementa_e_desativa_a_anterior(self, api_client, rh):
        documento, v1 = criar_documento_publicado(api_client, rh)

        api_client.force_authenticate(user=rh)
        api_client.post(
            f"{DOCS_URL}{documento.id}/versions/",
            {"file": pdf("v2.pdf"), "change_note": "Revisão anual"},
            format="multipart",
        )

        v1.refresh_from_db()
        v2 = documento.versions.get(version_number=2)
        assert v1.is_active is False
        assert v2.is_active is True
        assert v2.change_note == "Revisão anual"

    def test_versao_antiga_nao_e_apagada(self, api_client, rh):
        documento, v1 = criar_documento_publicado(api_client, rh)
        api_client.force_authenticate(user=rh)
        api_client.post(
            f"{DOCS_URL}{documento.id}/versions/", {"file": pdf()}, format="multipart"
        )

        assert documento.versions.count() == 2
        assert DocumentVersion.objects.filter(pk=v1.pk).exists()

    def test_nao_publica_documento_sem_arquivo(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        doc_id = api_client.post(DOCS_URL, {"title": "Vazio"}, format="json").data["id"]
        resp = api_client.post(f"{DOCS_URL}{doc_id}/publish/")
        assert resp.status_code == 400

    def test_colaborador_nao_envia_versao(self, api_client, rh, colaborador):
        documento, _ = criar_documento_publicado(api_client, rh)
        api_client.force_authenticate(user=colaborador)
        resp = api_client.post(
            f"{DOCS_URL}{documento.id}/versions/", {"file": pdf()}, format="multipart"
        )
        assert resp.status_code == 403

    def test_colaborador_nao_cria_documento(self, api_client, colaborador):
        api_client.force_authenticate(user=colaborador)
        resp = api_client.post(DOCS_URL, {"title": "x"}, format="json")
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════
# Aceite
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAceite:
    def test_aceite_registra_usuario_versao_e_ip(self, api_client, rh, colaborador):
        documento, versao = criar_documento_publicado(api_client, rh, obrigatorio=True)

        api_client.force_authenticate(user=colaborador)
        resp = api_client.post(f"{DOCS_URL}{documento.id}/versions/{versao.id}/accept/")
        assert resp.status_code == 200

        aceite = DocumentAcceptance.objects.get(user=colaborador, document_version=versao)
        assert aceite.ip_address is not None
        assert aceite.accepted_at is not None

    def test_aceitar_duas_vezes_nao_duplica(self, api_client, rh, colaborador):
        documento, versao = criar_documento_publicado(api_client, rh, obrigatorio=True)
        url = f"{DOCS_URL}{documento.id}/versions/{versao.id}/accept/"

        api_client.force_authenticate(user=colaborador)
        api_client.post(url)
        resp = api_client.post(url)

        assert resp.data["already"] is True
        assert DocumentAcceptance.objects.filter(user=colaborador).count() == 1

    def test_nova_versao_exige_novo_aceite(self, api_client, rh, colaborador):
        """O comportamento central do Módulo 5: v1 aceita, v2 volta a pendente."""
        documento, v1 = criar_documento_publicado(api_client, rh, obrigatorio=True)

        api_client.force_authenticate(user=colaborador)
        api_client.post(f"{DOCS_URL}{documento.id}/versions/{v1.id}/accept/")
        antes = api_client.get(f"{DOCS_URL}{documento.id}/").data
        assert antes["has_accepted"] is True
        assert antes["pending_acceptance"] is False

        api_client.force_authenticate(user=rh)
        api_client.post(
            f"{DOCS_URL}{documento.id}/versions/", {"file": pdf()}, format="multipart"
        )

        api_client.force_authenticate(user=colaborador)
        depois = api_client.get(f"{DOCS_URL}{documento.id}/").data
        assert depois["has_accepted"] is False
        assert depois["pending_acceptance"] is True

    def test_aceite_da_v1_permanece_no_historico(self, api_client, rh, colaborador):
        documento, v1 = criar_documento_publicado(api_client, rh, obrigatorio=True)
        api_client.force_authenticate(user=colaborador)
        api_client.post(f"{DOCS_URL}{documento.id}/versions/{v1.id}/accept/")

        api_client.force_authenticate(user=rh)
        api_client.post(
            f"{DOCS_URL}{documento.id}/versions/", {"file": pdf()}, format="multipart"
        )

        assert DocumentAcceptance.objects.filter(document_version=v1, user=colaborador).exists()

    def test_nao_aceita_versao_que_nao_e_mais_a_vigente(self, api_client, rh, colaborador):
        documento, v1 = criar_documento_publicado(api_client, rh, obrigatorio=True)
        api_client.force_authenticate(user=rh)
        api_client.post(
            f"{DOCS_URL}{documento.id}/versions/", {"file": pdf()}, format="multipart"
        )

        api_client.force_authenticate(user=colaborador)
        resp = api_client.post(f"{DOCS_URL}{documento.id}/versions/{v1.id}/accept/")
        assert resp.status_code == 400

    def test_usuario_de_outra_empresa_nao_aceita(self, api_client, rh, rh_b):
        documento, versao = criar_documento_publicado(api_client, rh, obrigatorio=True)
        api_client.force_authenticate(user=rh_b)
        resp = api_client.post(f"{DOCS_URL}{documento.id}/versions/{versao.id}/accept/")
        assert resp.status_code == 404

    def test_pendentes_lista_so_o_que_falta_aceitar(self, api_client, rh, colaborador):
        obrigatorio, versao = criar_documento_publicado(
            api_client, rh, "Código de Conduta", obrigatorio=True
        )
        criar_documento_publicado(api_client, rh, "Informativo", obrigatorio=False)

        api_client.force_authenticate(user=colaborador)
        titulos = [d["title"] for d in api_client.get(f"{DOCS_URL}pending/").data["results"]]
        assert titulos == ["Código de Conduta"]

        api_client.post(f"{DOCS_URL}{obrigatorio.id}/versions/{versao.id}/accept/")
        assert api_client.get(f"{DOCS_URL}pending/").data["results"] == []

    def test_pendentes_nao_vaza_documento_de_outra_empresa(
        self, api_client, rh, rh_b, colaborador
    ):
        criar_documento_publicado(api_client, rh_b, "Da Empresa B", obrigatorio=True)
        api_client.force_authenticate(user=colaborador)
        assert api_client.get(f"{DOCS_URL}pending/").data["results"] == []


# ══════════════════════════════════════════════════════════════════════════
# Isolamento na listagem
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIsolamentoDeDocumentos:
    def test_listagem_so_traz_documentos_da_propria_empresa(self, api_client, rh, rh_b):
        criar_documento_publicado(api_client, rh, "Da Empresa A")
        criar_documento_publicado(api_client, rh_b, "Da Empresa B")

        api_client.force_authenticate(user=rh)
        titulos = [d["title"] for d in api_client.get(DOCS_URL).data["results"]]
        assert "Da Empresa A" in titulos
        assert "Da Empresa B" not in titulos

    def test_nao_edita_documento_de_outra_empresa(self, api_client, rh, rh_b):
        documento, _ = criar_documento_publicado(api_client, rh_b, "Da B")
        api_client.force_authenticate(user=rh)
        resp = api_client.patch(
            f"{DOCS_URL}{documento.id}/", {"title": "Invadido"}, format="json"
        )
        assert resp.status_code == 404

    def test_categoria_de_outra_empresa_e_rejeitada(self, api_client, rh, empresa_b):
        from apps.documents.models import DocumentCategory

        alheia = DocumentCategory.objects.create(company=empresa_b, name="Alheia")
        api_client.force_authenticate(user=rh)
        resp = api_client.post(
            DOCS_URL, {"title": "x", "category": alheia.id}, format="json"
        )
        assert resp.status_code == 400

    def test_listagem_e_paginada(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        resp = api_client.get(DOCS_URL)
        assert "count" in resp.data and "results" in resp.data
