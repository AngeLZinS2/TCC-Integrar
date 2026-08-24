import logging

# pyrefly: ignore [missing-import]
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import AuthenticationFailed, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django.db.models import Q

from apps.audit import services as audit_service
from apps.audit.models import AuditLog
from apps.common.query_params import parse_int_param

from . import rbac

from .authentication import (
    COMPANY_SUSPENDED_CODE,
    COMPANY_SUSPENDED_DETAIL,
    company_access_denied,
)
from .models import User
from .permissions import IsRHAdmin
from .serializers import (
    CustomTokenObtainPairSerializer,
    DirectoryUserSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .throttles import LoginEmailThrottle, LoginIPThrottle, PasswordResetThrottle
from .tokens import revoke_all_sessions

logger = logging.getLogger(__name__)

# Resposta única do pedido de recuperação, exista ou não a conta.
PASSWORD_RESET_NEUTRAL_DETAIL = (
    "Se existir uma conta associada a este e-mail, "
    "enviaremos instruções para recuperação."
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/v1/auth/token/

    Retorna access token, refresh token **e** dados do usuário logado.
    Isso permite que o app Flutter persista o perfil logo após o login
    sem precisar de uma segunda requisição para /me/.

    Protegido contra força bruta por dois throttles combinados: por IP e
    por e-mail alvo (ver apps/users/throttles.py).

    Resposta:
        {
            "access": "<jwt>",
            "refresh": "<jwt>",
            "user": { id, email, full_name, role, sector, position, ... }
        }
    """

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # Registra apenas o login bem-sucedido. Tentativa falha não vira
        # log de auditoria — quem trata força bruta é o throttle, e gravar
        # e-mails tentados criaria um rastro de dados sem necessidade.
        if response.status_code == 200:
            user_id = (response.data.get("user") or {}).get("id")
            if user_id:
                actor = User.objects.select_related("company").filter(pk=user_id).first()
                audit_service.record(actor, AuditLog.Action.LOGIN, "session")
        return response


class CompanyAwareTokenRefreshView(TokenRefreshView):
    """
    POST /api/v1/auth/token/refresh/

    Igual à view padrão, mas recusa renovar o acesso de usuário inativo ou
    de empresa suspensa. Sem isso, suspender uma empresa não teria efeito
    real: o usuário seguiria renovando o token por dias.
    """

    def post(self, request, *args, **kwargs):
        refresh_raw = request.data.get("refresh")
        if refresh_raw:
            try:
                token = RefreshToken(refresh_raw)
                user = User.objects.select_related("company").get(
                    pk=token.payload.get("user_id")
                )
            except (TokenError, User.DoesNotExist, ValueError):
                # Token inválido/expirado: deixa a view padrão responder o 401.
                return super().post(request, *args, **kwargs)

            # AuthenticationFailed (e não InvalidToken) para que a resposta
            # carregue code='company_suspended', o mesmo que o login e a API
            # devolvem — assim o app trata os três casos por um único código.
            if not user.is_active:
                raise AuthenticationFailed("Usuário inativo.", code="user_inactive")
            if company_access_denied(user):
                raise AuthenticationFailed(
                    COMPANY_SUSPENDED_DETAIL, code=COMPANY_SUSPENDED_CODE
                )

        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/

    Recebe o refresh token e o coloca na blacklist, encerrando a sessão de
    verdade no servidor. O access token ainda vale até expirar (15 min),
    que é a janela mínima inerente a JWT stateless.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_raw = request.data.get("refresh")
        if not refresh_raw:
            return Response(
                {"refresh": "Informe o refresh token para encerrar a sessão."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        audit_service.record(request.user, AuditLog.Action.LOGOUT, "session")
        try:
            RefreshToken(refresh_raw).blacklist()
        except TokenError:
            # Token já inválido ou já revogado — do ponto de vista do cliente,
            # o resultado desejado (sessão encerrada) está garantido.
            pass
        return Response(status=status.HTTP_205_RESET_CONTENT)


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password-reset/

    Recebe { email } e dispara o e-mail de recuperação. Responde SEMPRE com
    a mesma mensagem, exista a conta ou não, para impedir enumeração de
    usuários. Nenhum token é devolvido no corpo da resposta.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.get_user()
        if user is not None:
            self._send_reset_email(user)

        return Response(
            {"detail": PASSWORD_RESET_NEUTRAL_DETAIL}, status=status.HTTP_200_OK
        )

    def _send_reset_email(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

        try:
            send_mail(
                subject="Recuperação de senha",
                message=(
                    f"Olá, {user.full_name}.\n\n"
                    "Recebemos um pedido para redefinir a sua senha. "
                    "Use o link abaixo para escolher uma nova:\n\n"
                    f"{link}\n\n"
                    "O link expira em algumas horas e só pode ser usado uma vez.\n"
                    "Se não foi você quem pediu, ignore esta mensagem — "
                    "sua senha continua a mesma."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            # Nunca vaza o destinatário nem o token para o log.
            logger.exception("Falha ao enviar e-mail de recuperação de senha.")


class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/password-reset/confirm/

    Recebe { uid, token, new_password, new_password_confirm }, aplica os
    validadores de senha do Django e, ao trocar a senha, revoga todas as
    sessões antigas do usuário.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        revoke_all_sessions(user)
        return Response(
            {"detail": "Senha alterada com sucesso. Entre com a nova senha."},
            status=status.HTTP_200_OK,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/auth/me/ → perfil do usuário autenticado
    PATCH /api/v1/auth/me/ → atualiza full_name, sector e position

    O campo `role` é somente leitura — alteração de papel só via Django admin.
    """

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/

    Cria um novo colaborador. Requer papel rh_admin.
    O RH também pode cadastrar via Django admin; este endpoint
    serve para integrações futuras (ex.: importação de lista de contratados).
    """

    serializer_class = RegisterSerializer
    permission_classes = [IsAuthenticated, IsRHAdmin]

    def perform_create(self, serializer):
        # Empresa é sempre a do RH autenticado — nunca aceita do cliente,
        # para impedir que um RH cadastre colaborador em outra empresa.
        serializer.save(company=self.request.user.company)


class ToggleColaboradorActiveView(APIView):
    """
    POST /api/v1/auth/colaboradores/<id>/toggle-active/

    Ativa/desativa um usuário (colaborador ou rh_admin) da mesma empresa
    do RH autenticado. Nunca permite desativar o último rh_admin ativo
    da empresa, para não deixar a empresa sem administrador.
    """

    permission_classes = [IsAuthenticated, IsRHAdmin]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk, company=request.user.company)

        if target.is_active and target.role == "rh_admin":
            other_active_rh_admin = (
                User.objects.filter(company=target.company, role="rh_admin", is_active=True)
                .exclude(pk=target.pk)
                .exists()
            )
            if not other_active_rh_admin:
                return Response(
                    {"detail": "Não é possível desativar o último RH admin da empresa."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        return Response(UserSerializer(target).data)


class ToggleSectorLeaderView(APIView):
    """
    POST /api/v1/auth/colaboradores/<id>/toggle-sector-leader/

    Concede/revoga a flag de líder do setor para um colaborador da mesma
    empresa do RH autenticado. Exige que o colaborador tenha um setor
    definido — não existe "líder de setor nenhum".
    """

    permission_classes = [IsAuthenticated, IsRHAdmin]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk, company=request.user.company)

        if not target.is_sector_leader and not target.sector_id:
            return Response(
                {"detail": "O colaborador precisa ter um setor definido para virar líder do setor."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target.is_sector_leader = not target.is_sector_leader
        target.save(update_fields=["is_sector_leader"])
        return Response(UserSerializer(target).data)


class CompanyDirectoryView(generics.ListAPIView):
    """
    GET /api/v1/auth/directory/?search=&sector=&position=&is_active=

    Diretório de colegas da própria empresa (colaborador e rh_admin, nunca
    o dono do sistema). Ordenado por setor → cargo → nome.

    Continua sem paginação de propósito: a tela tem um modo organograma,
    que precisa da estrutura inteira para desenhar a hierarquia. O volume é
    limitado pelo tamanho da empresa, não pelo histórico.
    """

    serializer_class = DirectoryUserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if not user.company_id:
            return User.objects.none()

        queryset = (
            User.objects.filter(company=user.company)
            .exclude(role="owner")
            .select_related("sector", "position")
            .order_by("sector__name", "position__name", "full_name")
        )

        params = self.request.query_params

        # O diretório serve para encontrar colegas, então mostra apenas
        # gente ativa por padrão — para todo mundo, inclusive o RH.
        # Quem administra pessoas pode pedir explicitamente os desligados
        # via ?is_active=false; a gestão de cadastro em si vive em
        # /api/v1/employees/, não aqui.
        is_active = params.get("is_active")
        if is_active in ("true", "false") and user.has_perm_code(rbac.EMPLOYEES_READ):
            queryset = queryset.filter(is_active=(is_active == "true"))
        else:
            queryset = queryset.filter(is_active=True)

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) | Q(email__icontains=search)
            )

        sector_id = parse_int_param(params.get("sector"), param_name="sector")
        if sector_id:
            queryset = queryset.filter(sector_id=sector_id)

        position_id = parse_int_param(params.get("position"), param_name="position")
        if position_id:
            queryset = queryset.filter(position_id=position_id)

        return queryset
