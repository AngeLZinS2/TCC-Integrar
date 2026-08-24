from rest_framework import serializers

from .models import Material


class MaterialSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source="sector.name", read_only=True)

    class Meta:
        model = Material
        fields = ["id", "title", "file_url", "sector", "sector_name", "created_at"]

    def validate_sector(self, sector):
        request = self.context.get("request")
        if request and sector and sector.company_id != request.user.company_id:
            raise serializers.ValidationError("Setor não pertence à sua empresa.")
        return sector

    def validate(self, attrs):
        request = self.context.get("request")
        if request:
            user = request.user
            if not user.is_rh_admin and user.is_sector_leader:
                # Líder de setor só cadastra/edita material do próprio setor —
                # nunca geral (sector=None) nem de outro setor.
                sector = attrs.get("sector")
                effective_sector_id = sector.id if sector else (self.instance.sector_id if self.instance else None)
                if effective_sector_id != user.sector_id:
                    raise serializers.ValidationError(
                        {"sector": "Líderes de setor só podem cadastrar materiais do próprio setor."}
                    )
        return attrs
