from rest_framework import serializers

from apps.users.models import User

from .models import Position, Sector


class PositionSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    collaborators_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Position
        fields = [
            "id",
            "name",
            "description",
            "sector",
            "sector_name",
            "is_active",
            "collaborators_count",
        ]

    def validate_sector(self, sector):
        request = self.context.get("request")
        if request and sector.company_id != request.user.company_id:
            raise serializers.ValidationError("Setor não pertence à sua empresa.")
        return sector

    def validate(self, attrs):
        """Nome de cargo não pode repetir dentro do mesmo setor."""
        sector = attrs.get("sector") or getattr(self.instance, "sector", None)
        name = attrs.get("name") or getattr(self.instance, "name", None)
        if sector and name:
            duplicates = Position.objects.filter(sector=sector, name__iexact=name)
            if self.instance:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"name": "Já existe um cargo com este nome neste setor."}
                )
        return attrs


class SectorSerializer(serializers.ModelSerializer):
    positions = PositionSerializer(many=True, read_only=True)
    positions_count = serializers.IntegerField(read_only=True)
    collaborators_count = serializers.IntegerField(read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True, default=None)

    class Meta:
        model = Sector
        fields = [
            "id",
            "name",
            "description",
            "manager",
            "manager_name",
            "is_active",
            "positions",
            "positions_count",
            "collaborators_count",
        ]

    def validate_manager(self, manager):
        """
        O gestor precisa ser da mesma empresa e não pode ser o dono da
        plataforma — que não pertence a empresa nenhuma.
        """
        request = self.context.get("request")
        if not request or manager is None:
            return manager
        if manager.company_id != request.user.company_id:
            raise serializers.ValidationError("O gestor precisa ser da sua empresa.")
        if manager.is_owner:
            raise serializers.ValidationError("O dono da plataforma não pode gerir setores.")
        return manager

    def validate_name(self, name):
        """Nome de setor é único por empresa — checado aqui para dar 400 legível."""
        request = self.context.get("request")
        if not request:
            return name
        duplicates = Sector.objects.filter(
            company_id=request.user.company_id, name__iexact=name.strip()
        )
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("Já existe um setor com este nome na sua empresa.")
        return name.strip()


class SectorManagerOptionSerializer(serializers.ModelSerializer):
    """Lista enxuta para o seletor de gestor — sem expor dados desnecessários."""

    class Meta:
        model = User
        fields = ["id", "full_name", "role"]
