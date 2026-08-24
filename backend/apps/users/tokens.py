"""
Revogação de sessões.

Access tokens são stateless: uma vez emitidos, valem até expirar. O que dá
para revogar de verdade é o refresh token, via blacklist do SimpleJWT.

Por isso o `ACCESS_TOKEN_LIFETIME` é curto (15 min): esse é o tamanho real
da janela em que uma sessão revogada ainda consegue chamar a API. Passada
a janela, o cliente precisa do refresh — que já está na blacklist.

A suspensão de empresa não depende disso: ela é reavaliada a cada
requisição em `CompanyAwareJWTAuthentication` e vale imediatamente.
"""

from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)


def revoke_all_sessions(user) -> int:
    """
    Coloca na blacklist todos os refresh tokens vivos do usuário.

    Usado quando a senha é alterada ou redefinida — a partir daí, nenhuma
    sessão antiga consegue renovar o acesso. Retorna quantos tokens foram
    revogados nesta chamada.
    """
    revoked = 0
    for token in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        if created:
            revoked += 1
    return revoked
