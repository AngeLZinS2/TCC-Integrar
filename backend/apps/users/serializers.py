from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .authentication import COMPANY_SUSPENDED_DETAIL
from .models import User


# ---------------------------------------------------------------------------
# Leitura / atualização de perfil
# ---------------------------------------------------------------------------

class UserSerializer(serializers.ModelSerializer):
    """
    Perfil do próprio usuário (`/auth/me/`).

    A fronteira entre "o que você altera" e "o que o RH administra" é
    definida aqui, no backend. O colaborador edita apenas identificação
    pessoal — nome, telefone e foto. Tudo que define posição na empresa
    (setor, cargo, gestor, matrícula, papel, data de admissão) é read-only:
    são decisões do RH, não do próprio funcionário.
    """

    sector_name = serializers.CharField(source="sector.name", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True, default=None)
    position_name = serializers.CharField(source="position.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True, default=None)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True, default=None)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "avatar_url",
            "role",
            "company",
            "company_name",
            "sector",
            "sector_name",
            "position",
            "position_name",
            "unit",
            "unit_name",
            "manager",
            "manager_name",
            "registration_number",
            "hire_date",
            "is_active",
            "is_sector_leader",
            "permissions",
            "created_at",
        ]
        # Editáveis pelo próprio usuário: full_name, phone, avatar_url.
        read_only_fields = [
            "id", "email", "role", "created_at", "company", "company_name",
            "sector", "sector_name", "position", "position_name",
            "unit", "unit_name",
            "manager", "manager_name", "registration_number",
            "hire_date", "is_active", "is_sector_leader", "permissions",
        ]

    def get_permissions(self, obj) -> list:
        """
        Permissões efetivas do usuário, para o app montar a navegação.

        É conveniência de UX apenas: a autorização real acontece no backend,
        a cada requisição.
        """
        return sorted(obj.get_permissions())


class TenantScopedFieldsMixin:
    """
    Valida que setor, cargo, unidade e gestor informados pertencem à
    empresa de quem está fazendo a requisição.

    Reunido num mixin porque a mesma regra vale no cadastro e na edição — e
    porque esquecê-la em um dos dois abriria uma brecha de tenancy.
    """

    def validate_sector(self, sector):
        request = self.context.get("request")
        if request and sector and sector.company_id != request.user.company_id:
            raise serializers.ValidationError("Setor não pertence à sua empresa.")
        return sector

    def validate_position(self, position):
        request = self.context.get("request")
        if request and position and position.sector.company_id != request.user.company_id:
            raise serializers.ValidationError("Cargo não pertence à sua empresa.")
        return position

    def validate_unit(self, unit):
        request = self.context.get("request")
        if request and unit and unit.company_id != request.user.company_id:
            raise serializers.ValidationError("Unidade não pertence à sua empresa.")
        return unit

    def validate_manager(self, manager):
        request = self.context.get("request")
        if not request or manager is None:
            return manager
        if manager.company_id != request.user.company_id:
            raise serializers.ValidationError("O gestor precisa ser da sua empresa.")
        if manager.is_owner:
            raise serializers.ValidationError("O dono da plataforma não pode ser gestor.")
        if self.instance and manager.pk == self.instance.pk:
            raise serializers.ValidationError("Um colaborador não pode ser gestor de si mesmo.")
        return manager

    def validate_role(self, role):
        if role not in User.ASSIGNABLE_ROLES:
            raise serializers.ValidationError(
                "Papel inválido. Escolha entre: " + ", ".join(User.ASSIGNABLE_ROLES) + "."
            )
        return role

    def _validate_consistency(self, attrs):
        """
        Regras que dependem de mais de um campo ao mesmo tempo.

        Resolve cada campo contra o valor que ele terá DEPOIS de salvar —
        num PATCH parcial, o campo ausente mantém o valor atual.
        """
        def resolved(field):
            if field in attrs:
                return attrs[field]
            return getattr(self.instance, field, None)

        sector = resolved("sector")
        position = resolved("position")
        if position and sector and position.sector_id != sector.id:
            raise serializers.ValidationError(
                {"position": "O cargo escolhido não pertence ao setor selecionado."}
            )
        if position and not sector:
            raise serializers.ValidationError(
                {"sector": "Defina o setor correspondente ao cargo escolhido."}
            )

        if resolved("is_sector_leader") and not sector:
            raise serializers.ValidationError(
                {"is_sector_leader": "O colaborador precisa ter um setor definido para virar líder do setor."}
            )

        registration = resolved("registration_number")
        if registration:
            company_id = (
                self.instance.company_id
                if self.instance
                else self.context["request"].user.company_id
            )
            duplicates = User.objects.filter(
                company_id=company_id, registration_number=registration
            )
            if self.instance:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"registration_number": "Já existe um colaborador com esta matrícula na empresa."}
                )
        return attrs


# ---------------------------------------------------------------------------
# Cadastro de novo colaborador (apenas RH admin)
# ---------------------------------------------------------------------------

class RegisterSerializer(TenantScopedFieldsMixin, serializers.ModelSerializer):
    """
    Criação de um novo colaborador. Exige password com confirmação.
    Apenas RH / admin da empresa pode chamar o endpoint que usa este serializer.
    """

    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "avatar_url",
            "registration_number",
            "role",
            "sector",
            "position",
            "unit",
            "manager",
            "hire_date",
            "is_sector_leader",
            "password",
            "password_confirm",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "As senhas não conferem."})
        return self._validate_consistency(attrs)

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.setdefault("hire_date", timezone.localdate())
        user = User(**validated_data)
        user.set_password(password)

        # Quem cadastrou, para o plano de onboarding gerado a seguir sair
        # auditado com um autor em vez de "sistema". Atributo de instância,
        # não campo: é contexto da requisição, não estado do colaborador.
        request = self.context.get("request")
        ator = getattr(request, "user", None) if request else None
        if ator is not None and getattr(ator, "is_authenticated", False):
            user._registered_by_id = ator.pk

        user.save()
        return user


# ---------------------------------------------------------------------------
# Administração de colaboradores (RH / admin da empresa)
# ---------------------------------------------------------------------------


class EmployeeSerializer(TenantScopedFieldsMixin, serializers.ModelSerializer):
    """
    Leitura e edição de um colaborador pelo RH / admin da empresa.

    Não inclui senha: criação usa RegisterSerializer, e troca de senha é
    pelo fluxo de recuperação — o RH nunca define nem vê a senha de alguém
    depois do cadastro inicial.
    """

    sector_name = serializers.CharField(source="sector.name", read_only=True, default=None)
    unit_name = serializers.CharField(source="unit.name", read_only=True, default=None)
    position_name = serializers.CharField(source="position.name", read_only=True, default=None)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True, default=None)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "avatar_url",
            "registration_number",
            "role",
            "role_display",
            "sector",
            "sector_name",
            "position",
            "position_name",
            "unit",
            "unit_name",
            "manager",
            "manager_name",
            "hire_date",
            "is_active",
            "is_sector_leader",
            "last_login",
            "created_at",
        ]
        read_only_fields = [
            "id", "email", "role_display", "sector_name", "position_name",
            "manager_name", "last_login", "created_at",
            # Ativação tem endpoint próprio, com a proteção do último admin.
            "is_active",
        ]

    def validate(self, attrs):
        return self._validate_consistency(attrs)


# ---------------------------------------------------------------------------
# Diretório de colegas da empresa (colaborador e rh_admin)
# ---------------------------------------------------------------------------

class DirectoryUserSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source="sector.name", read_only=True, default=None)
    position_name = serializers.CharField(source="position.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "role",
            "sector",
            "sector_name",
            "position",
            "position_name",
        ]


# ---------------------------------------------------------------------------
# Login JWT customizado — inclui dados do usuário na resposta
# ---------------------------------------------------------------------------

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Estende o serializer padrão do simplejwt para devolver também os dados
    do usuário logado, evitando um round-trip extra para /me/.
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.company_id and not self.user.company.is_active:
            raise AuthenticationFailed(COMPANY_SUSPENDED_DETAIL, code="company_suspended")
        data["user"] = UserSerializer(self.user).data
        return data


# ---------------------------------------------------------------------------
# Recuperação de senha
# ---------------------------------------------------------------------------

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Pedido de recuperação. Valida apenas o formato do e-mail — nunca se ele
    existe, para não permitir enumeração de contas. A view responde sempre
    com a mesma mensagem neutra.
    """

    email = serializers.EmailField()

    def get_user(self):
        """Usuário elegível a receber o e-mail, ou None. Nunca levanta erro."""
        email = self.validated_data["email"].strip().lower()
        user = User.objects.select_related("company").filter(email__iexact=email).first()
        if user is None or not user.is_active:
            return None
        # Empresa suspensa não recupera senha — não teria como entrar mesmo.
        if user.role != "owner" and (user.company_id is None or not user.company.is_active):
            return None
        return user


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Redefinição efetiva da senha.

    O token é o do `default_token_generator` do Django: expira por tempo
    (PASSWORD_RESET_TIMEOUT) e deixa de valer assim que a senha muda, já
    que o hash da senha antiga entra no cálculo — ou seja, é de uso único
    sem precisar de tabela própria.
    """

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, style={"input_type": "password"})
    new_password_confirm = serializers.CharField(style={"input_type": "password"})

    # Mensagem única para uid inválido, token inválido e token expirado —
    # não dá pistas sobre qual dos três falhou.
    INVALID_DETAIL = "Link de recuperação inválido ou expirado. Solicite um novo."

    def validate(self, attrs):
        if attrs["new_password"] != attrs.pop("new_password_confirm"):
            raise serializers.ValidationError({"new_password_confirm": "As senhas não conferem."})

        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"token": self.INVALID_DETAIL})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": self.INVALID_DETAIL})

        if not user.is_active:
            raise serializers.ValidationError({"token": self.INVALID_DETAIL})

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
