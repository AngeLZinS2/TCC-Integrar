from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.common.tenant import TenantValidatedSerializerMixin
from apps.users.serializers import DirectoryUserSerializer

from .models import Event, EventAttendance

User = get_user_model()


class EventSerializer(TenantValidatedSerializerMixin, serializers.ModelSerializer):
    organizer_details = DirectoryUserSerializer(source="organizer", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    confirmed_count = serializers.IntegerField(read_only=True)
    seats_left = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)
    my_attendance = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "title", "description", "location",
            "start_at", "end_at", "capacity", "status", "status_display",
            "allows_rsvp", "target_sectors", "target_units",
            "organizer", "organizer_details",
            "confirmed_count", "seats_left", "is_full", "is_past",
            "my_attendance", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "organizer", "created_at", "updated_at", "status"]

    def get_my_attendance(self, obj) -> str | None:
        """Resposta do usuário atual, ou None se ainda não respondeu."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        respostas = self.context.get("minhas_respostas")
        if respostas is not None:
            return respostas.get(obj.id)
        registro = obj.attendances.filter(user=request.user).first()
        return registro.status if registro else None

    def validate_target_sectors(self, sectors):
        return self._check_many(sectors, "O setor")

    def validate_target_units(self, units):
        return self._check_many(units, "A unidade")


    def validate(self, attrs):
        inicio = attrs.get("start_at") or getattr(self.instance, "start_at", None)
        fim = attrs.get("end_at") or getattr(self.instance, "end_at", None)
        if inicio and fim and fim <= inicio:
            raise serializers.ValidationError(
                {"end_at": "O término precisa ser depois do início."}
            )
        if not inicio:
            raise serializers.ValidationError(
                {"start_at": "Informe a data e hora de início."}
            )

        capacidade = attrs.get("capacity")
        if capacidade is not None and self.instance:
            # Reduzir a capacidade abaixo do já confirmado deixaria pessoas
            # com presença confirmada e sem vaga — situação sem saída boa.
            confirmados = self.instance.confirmed_count
            if capacidade < confirmados:
                raise serializers.ValidationError(
                    {
                        "capacity": (
                            f"Já há {confirmados} presença(s) confirmada(s). "
                            "Cancele confirmações antes de reduzir a capacidade."
                        )
                    }
                )
        return attrs


class EventAttendanceSerializer(serializers.ModelSerializer):
    user_details = DirectoryUserSerializer(source="user", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = EventAttendance
        fields = ["id", "user", "user_details", "status", "status_display", "responded_at"]
        read_only_fields = fields


class RSVPSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=EventAttendance.Status.choices)


class BirthdaySerializer(serializers.ModelSerializer):
    """
    Painel de aniversariantes.

    Minimização de dados (Módulo 4/19): mostrar quem faz aniversário e
    quando não exige revelar o ANO de nascimento — que é dado pessoal
    sensível e permite deduzir a idade de todo o quadro. Por isso a data
    completa nunca sai daqui: só dia/mês. O e-mail também fica de fora —
    quem precisa do contato usa o Diretório.
    """

    sector_name = serializers.CharField(source="sector.name", read_only=True, default=None)
    position_name = serializers.CharField(source="position.name", read_only=True, default=None)
    birthday = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "avatar_url", "birthday", "sector_name", "position_name"]

    def get_birthday(self, obj) -> str | None:
        """Apenas dia/mês, no formato DD/MM."""
        if not obj.birth_date:
            return None
        return f"{obj.birth_date.day:02d}/{obj.birth_date.month:02d}"
