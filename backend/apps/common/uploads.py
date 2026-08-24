"""
Validação e nomeação segura de arquivos enviados.

O Módulo 20 da P2 lista o que é obrigatório aqui. A regra que governa tudo:
**nada que veio do cliente é confiável** — nem o nome, nem a extensão, nem
o content-type declarado no upload.

O que fazemos:
  - conferir a extensão contra uma allowlist (não uma denylist: lista de
    proibidos sempre deixa passar o que ninguém pensou em proibir);
  - conferir o MIME real lendo os primeiros bytes, não o cabeçalho enviado;
  - limitar o tamanho;
  - gerar um nome interno aleatório, descartando o original;
  - guardar o nome original apenas como metadado, para exibição.

O nome gerado também é o que impede path traversal: como não reaproveitamos
nenhum caractere do nome enviado, `../../etc/passwd` não tem por onde entrar.
"""

import hashlib
import uuid
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError as DjangoValidationError

# Extensão → MIMEs aceitos para ela. A allowlist é deliberadamente curta:
# são os formatos que uma biblioteca de documentos corporativos precisa.
ALLOWED_TYPES = {
    "pdf": {"application/pdf"},
    "doc": {"application/msword"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",  # OOXML é um zip; alguns detectores param aí
    },
    "xls": {"application/vnd.ms-excel"},
    "xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    },
    "ppt": {"application/vnd.ms-powerpoint"},
    "pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",
    },
    "txt": {"text/plain"},
    "csv": {"text/plain", "text/csv"},
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
}

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB

# Assinaturas de arquivo (magic numbers). Ler os bytes é o que diferencia
# um PDF de verdade de um executável renomeado para .pdf.
_MAGIC = [
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"PK\x03\x04", "application/zip"),  # docx/xlsx/pptx
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "application/msword"),  # doc/xls/ppt antigos
]


def sniff_mime(chunk: bytes) -> str:
    """MIME deduzido do conteúdo. Texto é o fallback quando não há assinatura."""
    for assinatura, mime in _MAGIC:
        if chunk.startswith(assinatura):
            return mime
    try:
        chunk.decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        return "application/octet-stream"


def extension_of(filename: str) -> str:
    """
    Extensão em minúsculas, sem ponto.

    `PurePosixPath` isola só o último componente, então um nome como
    `../../evil.pdf` devolve apenas `pdf` — o caminho é descartado.
    """
    nome = PurePosixPath((filename or "").replace("\\", "/")).name
    if "." not in nome:
        return ""
    return nome.rsplit(".", 1)[1].lower()


def safe_original_name(filename: str, limite: int = 120) -> str:
    """
    Nome original preservado apenas para exibição.

    Nunca é usado para montar caminho — só aparece na tela e no nome
    sugerido do download.
    """
    nome = PurePosixPath((filename or "").replace("\\", "/")).name
    nome = nome.replace("\x00", "").strip()
    return (nome or "arquivo")[:limite]


def validate_upload(arquivo) -> dict:
    """
    Valida o arquivo enviado e devolve os metadados a persistir.

    Levanta `DjangoValidationError` com mensagem legível — a view converte
    em 400. Retorna: extensão, MIME real, tamanho, nome original e checksum.
    """
    if arquivo is None:
        raise DjangoValidationError("Envie um arquivo.")

    tamanho = getattr(arquivo, "size", 0) or 0
    if tamanho == 0:
        raise DjangoValidationError("O arquivo está vazio.")
    if tamanho > MAX_UPLOAD_BYTES:
        limite_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise DjangoValidationError(f"O arquivo excede o limite de {limite_mb} MB.")

    extensao = extension_of(getattr(arquivo, "name", ""))
    if extensao not in ALLOWED_TYPES:
        permitidas = ", ".join(sorted(ALLOWED_TYPES))
        raise DjangoValidationError(
            f"Tipo de arquivo não permitido. Aceitos: {permitidas}."
        )

    # Lê o começo para o sniff e o arquivo inteiro para o checksum, sempre
    # devolvendo o ponteiro ao início — o storage lê o arquivo depois.
    arquivo.seek(0)
    cabecalho = arquivo.read(2048)
    mime_real = sniff_mime(cabecalho)

    if mime_real not in ALLOWED_TYPES[extensao]:
        raise DjangoValidationError(
            "O conteúdo do arquivo não corresponde à extensão informada."
        )

    digest = hashlib.sha256()
    digest.update(cabecalho)
    for bloco in iter(lambda: arquivo.read(64 * 1024), b""):
        digest.update(bloco)
    arquivo.seek(0)

    return {
        "extension": extensao,
        "mime_type": mime_real,
        "size": tamanho,
        "original_name": safe_original_name(getattr(arquivo, "name", "")),
        "checksum": digest.hexdigest(),
    }


def build_storage_path(company_id: int, scope: str, extension: str) -> str:
    """
    Caminho interno do arquivo, particionado por empresa.

    O nome é aleatório e a extensão vem da allowlist já validada — nenhum
    caractere do nome enviado pelo cliente chega até aqui.

        company_<id>/<escopo>/<uuid>.<ext>
    """
    nome_interno = f"{uuid.uuid4().hex}.{extension}" if extension else uuid.uuid4().hex
    return f"company_{int(company_id)}/{scope}/{nome_interno}"
