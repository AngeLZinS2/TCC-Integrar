"""
Autenticação JWT ciente do tenant.

O SimpleJWT padrão valida apenas a assinatura do token e `user.is_active`.
Isso deixa um buraco: quando o dono da plataforma suspende uma empresa,
quem já estava logado continua usando a API normalmente até o token expirar.

Esta classe fecha esse buraco reavaliando `company.is_active` a cada
requisição, de forma que a suspensão tenha efeito imediato.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings

COMPANY_SUSPENDED_DETAIL = (
    "Esta empresa está temporariamente suspensa. "
    "Entre em contato com o administrador da sua empresa."
)
COMPANY_SUSPENDED_CODE = "company_suspended"


def company_access_denied(user) -> bool:
    """
    True quando o usuário não pode acessar a API por causa da empresa.

    O dono da plataforma (role='owner') não pertence a nenhuma empresa e
    por isso nunca é bloqueado por esta regra.
    """
    if user.role == "owner":
        return False
    return user.company_id is None or not user.company.is_active


class CompanyAwareJWTAuthentication(JWTAuthentication):
    """
    JWTAuthentication + checagem de empresa ativa.

    `get_user` é reescrito (em vez de chamar super()) apenas para trazer a
    empresa no mesmo SELECT — sem isso, cada requisição autenticada faria
    uma query extra só para ler `company.is_active`.
    """

    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken("Token não contém identificação de usuário.")

        try:
            user = self.user_model.objects.select_related("company").get(
                **{api_settings.USER_ID_FIELD: user_id}
            )
        except self.user_model.DoesNotExist:
            raise AuthenticationFailed("Usuário não encontrado.", code="user_not_found")

        if not user.is_active:
            raise AuthenticationFailed("Usuário inativo.", code="user_inactive")

        if company_access_denied(user):
            raise AuthenticationFailed(
                COMPANY_SUSPENDED_DETAIL, code=COMPANY_SUSPENDED_CODE
            )

        return user
