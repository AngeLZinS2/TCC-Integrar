"""
Throttles de proteção contra força bruta.

Duas camadas complementares no login:
  - por IP     → trava um atacante martelando de um único endereço;
  - por e-mail → trava o ataque distribuído em vários IPs contra uma
                 mesma conta, que a trava por IP sozinha não pega.

O e-mail nunca entra na chave em texto claro: é reduzido a um hash, para
que a chave de cache não guarde dado pessoal.
"""

import hashlib

from rest_framework.throttling import SimpleRateThrottle


def _hash_identity(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class LoginIPThrottle(SimpleRateThrottle):
    """Limita tentativas de login por endereço de origem."""

    scope = "login_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class LoginEmailThrottle(SimpleRateThrottle):
    """
    Limita tentativas de login por conta alvo, independente do IP.

    Sem e-mail no corpo não há o que limitar — devolve None e deixa o
    serializer responder o 400 normal de campo obrigatório.
    """

    scope = "login_email"

    def get_cache_key(self, request, view):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": _hash_identity(email),
        }


class PasswordResetThrottle(SimpleRateThrottle):
    """
    Limita pedidos de recuperação de senha por IP.

    Evita que o endpoint seja usado para disparar e-mail em massa.
    """

    scope = "password_reset"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
