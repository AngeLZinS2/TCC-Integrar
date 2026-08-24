import pytest
import os
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.documents.models import DocumentCategory, Document, DocumentVersion, DocumentAcceptance
from apps.companies.models import Company

pytestmark = pytest.mark.django_db

def test_listar_documentos(api_client, rh_admin_user, company):
    cat = DocumentCategory.objects.create(company=company, name="RH")
    doc = Document.objects.create(company=company, title="Manual", category=cat, is_required=True)
    
    # Fake file
    fake_file = SimpleUploadedFile("test.txt", b"file_content")
    version = DocumentVersion.objects.create(document=doc, version_number=1, file=fake_file, created_by=rh_admin_user)
    
    api_client.force_authenticate(user=rh_admin_user)
    resp = api_client.get("/api/v1/documents/")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["results"][0]["has_accepted"] == False
    assert resp.json()["results"][0]["active_version"]["version_number"] == 1

def test_download_documento_isolamento(api_client, rh_admin_user, django_user_model, company):
    cat = DocumentCategory.objects.create(company=company, name="Políticas")
    doc = Document.objects.create(company=company, title="Política", category=cat)
    fake_file = SimpleUploadedFile("policy.txt", b"secret_policy")
    version = DocumentVersion.objects.create(document=doc, version_number=1, file=fake_file, created_by=rh_admin_user)
    
    # Criar tenant B
    company_b = Company.objects.create(name="Empresa B")
    user_b = django_user_model.objects.create_user(email="b@x.com", full_name="User B", password="x", company=company_b)
    
    api_client.force_authenticate(user=user_b)
    resp = api_client.get(f"/api/v1/documents/{doc.id}/versions/{version.id}/download/")
    # User B should NOT be able to download company A's document
    assert resp.status_code == 404

def test_aceitar_documento(api_client, colaborador_user, rh_admin_user, company):
    cat = DocumentCategory.objects.create(company=company, name="Políticas")
    # Publicado: colaborador nao acessa documento em rascunho.
    doc = Document.objects.create(company=company, title="Política", category=cat,
                                  is_required=True, status=Document.Status.PUBLISHED)
    fake_file = SimpleUploadedFile("policy.txt", b"secret_policy")
    version = DocumentVersion.objects.create(document=doc, version_number=1, file=fake_file, created_by=rh_admin_user)
    
    api_client.force_authenticate(user=colaborador_user)
    resp = api_client.post(f"/api/v1/documents/{doc.id}/versions/{version.id}/accept/")
    assert resp.status_code == 200
    
    # Verifica que o aceite foi registrado
    assert DocumentAcceptance.objects.filter(document_version=version, user=colaborador_user).exists()
    
    # Listagem deve retornar has_accepted = True
    resp_list = api_client.get("/api/v1/documents/")
    assert resp_list.json()["results"][0]["has_accepted"] == True

def test_download_documento_sucesso(api_client, colaborador_user, rh_admin_user, company):
    cat = DocumentCategory.objects.create(company=company, name="Políticas")
    doc = Document.objects.create(company=company, title="Política", category=cat,
                                  status=Document.Status.PUBLISHED)
    fake_file = SimpleUploadedFile("policy_test.txt", b"secret_policy")
    version = DocumentVersion.objects.create(document=doc, version_number=1, file=fake_file, created_by=rh_admin_user)
    
    api_client.force_authenticate(user=colaborador_user)
    resp = api_client.get(f"/api/v1/documents/{doc.id}/versions/{version.id}/download/")
    
    assert resp.status_code == 200
    # O conteúdo deve ser streamado. Podemos verificar se pegamos o conteúdo certo.
    assert list(resp.streaming_content)[0] == b"secret_policy"
    
    # Limpa o arquivo de teste (já que o FileField salva no disco e pytest-django-db não limpa arquivos fisicos auto)
    if version.file and os.path.exists(version.file.path):
        os.remove(version.file.path)
