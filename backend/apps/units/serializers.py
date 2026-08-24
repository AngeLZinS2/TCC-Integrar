from rest_framework import serializers

from apps.common.tenant import TenantValidatedSerializerMixin

from .models import Unit


class UnitSerializer(TenantValidatedSerializerMixin, serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)
    manager_name = serializers.CharField(
        source="manager.full_name", read_only=True, default=None
    )

    class Meta:
        model = Unit
        fields = [
            "id", "name", "code", "address", "city", "state",
            "status", "manager", "manager_name", "employee_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_manager(self, manager):
        return self._check(manager, "Responsável")

    def _duplicado(self, campo, valor):
        """
        Unicidade é (company, campo), mas `company` é injetada na view e não
        está nos dados validados — o UniqueTogetherValidator do DRF não
        consegue montar a checagem sozinho, e o duplicado estouraria
        IntegrityError (500) em vez de 400.
        """
        company_id = getattr(self._actor, "company_id", None)
        if not company_id:
            return False
        conflito = Unit.objects.filter(
            company_id=company_id, **{f"{campo}__iexact": valor.strip()}
        )
        if self.instance is not None:
            conflito = conflito.exclude(pk=self.instance.pk)
        return conflito.exists()

    def validate_name(self, nome):
        if self._duplicado("name", nome):
            raise serializers.ValidationError("Já existe uma unidade com este nome.")
        return nome

    def validate_code(self, codigo):
        if codigo and self._duplicado("code", codigo):
            raise serializers.ValidationError("Já existe uma unidade com este código.")
        return codigo

    def validate_state(self, uf):
        return uf.upper().strip()
