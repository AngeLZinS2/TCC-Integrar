from rest_framework import serializers

from apps.common.tenant import TenantValidatedSerializerMixin
from apps.users.serializers import DirectoryUserSerializer

from .models import Announcement, AnnouncementRead

class AnnouncementSerializer(serializers.ModelSerializer):
    author_details = DirectoryUserSerializer(source='author', read_only=True)
    is_read = serializers.SerializerMethodField()
    read_count = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'is_urgent',
            'status', 'publish_at', 'published_at', 'expires_at',
            'target_sectors', 'target_positions', 'target_units',
            'author', 'author_details', 'created_at', 'updated_at',
            'is_read', 'read_count'
        ]
        # `status` e `published_at` mudam pelas acoes de publicar/agendar,
        # nunca por PATCH direto — senao daria para "publicar" pulando a
        # notificacao do publico-alvo.
        read_only_fields = [
            'id', 'author', 'created_at', 'updated_at', 'status', 'published_at',
        ]

    def get_is_read(self, obj) -> bool:
        # Usa a anotação da view quando existe (uma query para a lista
        # inteira); só cai na consulta individual fora desse caminho.
        annotated = getattr(obj, "_is_read", None)
        if annotated is not None:
            return annotated
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return AnnouncementRead.objects.filter(announcement=obj, user=request.user).exists()

    def get_read_count(self, obj) -> int:
        annotated = getattr(obj, "_read_count", None)
        return annotated if annotated is not None else obj.reads.count()

class AnnouncementCreateSerializer(TenantValidatedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'is_urgent',
            'publish_at', 'expires_at',
            'target_sectors', 'target_positions', 'target_units', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        publicar_em = attrs.get('publish_at')
        expira_em = attrs.get('expires_at')
        if publicar_em and expira_em and expira_em <= publicar_em:
            raise serializers.ValidationError(
                {'expires_at': 'A expiração precisa ser depois da publicação.'}
            )
        return attrs

    # Sem estas checagens, o RH conseguia segmentar um comunicado para um
    # setor ou cargo de OUTRA empresa — o comunicado ficava invisível para
    # todo mundo e o id alheio ficava gravado no registro.
    def validate_target_sectors(self, sectors):
        return self._check_many(sectors, "O setor")

    def validate_target_positions(self, positions):
        return self._check_many(positions, "O cargo")

    def validate_target_units(self, units):
        return self._check_many(units, "A unidade")

