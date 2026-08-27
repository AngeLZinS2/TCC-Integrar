"""
Cifra das credenciais do banco do cliente.

A P4 (seções 7 e 36) é direta: senha nunca em texto puro, nunca em log,
nunca no frontend. Aqui fica só o guardar e o ler — quem decide *se* pode
ler é o RBAC, na view.

A chave vem de `INTEGRATION_ENCRYPTION_KEY`, separada da `SECRET_KEY` do
Django de propósito. Se fossem a mesma, girar a `SECRET_KEY` — coisa que
se faz justamente por incidente de segurança — tornaria ilegível toda
credencial de integração já salva, no pior momento possível.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


class CredencialIlegivel(Exception):
    """
    O texto cifrado não abre com a chave atual.

    Acontece quando a chave mudou. É um erro de operação, não do usuário —
    a mensagem precisa dizer isso, em vez de fingir que a senha está errada.
    """


def _chave() -> bytes:
    """
    Deriva a chave Fernet a partir do valor configurado.

    Aceita um segredo de qualquer tamanho e o normaliza com SHA-256, para o
    operador não precisar gerar uma chave no formato exato do Fernet — o
    que na prática levaria alguém a reaproveitar a `SECRET_KEY`.
    """
    bruta = getattr(settings, "INTEGRATION_ENCRYPTION_KEY", "") or ""
    if not bruta:
        raise CredencialIlegivel(
            "INTEGRATION_ENCRYPTION_KEY não está configurada: sem ela o "
            "sistema não guarda credencial de integração."
        )
    digest = hashlib.sha256(bruta.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def cifrar(texto: str) -> str:
    """Devolve o texto cifrado, pronto para gravar."""
    if texto is None:
        texto = ""
    return Fernet(_chave()).encrypt(texto.encode("utf-8")).decode("ascii")


def decifrar(cifrado: str) -> str:
    """
    Lê a senha de volta. Só o connector chama isto, na hora de conectar.

    Falha nunca vaza o valor nem a chave para o log — só o fato de não ter
    aberto.
    """
    if not cifrado:
        return ""
    try:
        return Fernet(_chave()).decrypt(cifrado.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        logger.error(
            "Credencial de integração não pôde ser decifrada. "
            "A chave de criptografia provavelmente mudou."
        )
        raise CredencialIlegivel(
            "A credencial guardada não pôde ser lida. Cadastre a senha de "
            "conexão novamente."
        )
