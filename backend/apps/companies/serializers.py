from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.users.models import User

from .models import Company


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class CompanyBootstrapSerializer(serializers.Serializer):
    """
    Cria uma empresa nova + seu primeiro RH admin numa única chamada
    transacional. Usado exclusivamente pelo dono do sistema.
    """

    name = serializers.CharField(
        max_length=150,
        validators=[UniqueValidator(queryset=Company.objects.all(), message="Já existe uma empresa com esse nome.")],
    )
    admin_email = serializers.EmailField()
    admin_full_name = serializers.CharField(max_length=150)
    admin_password = serializers.CharField(min_length=8, write_only=True)

    def validate_admin_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Já existe um usuário com esse e-mail.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            company = Company.objects.create(name=validated_data["name"])
            User.objects.create_user(
                email=validated_data["admin_email"],
                full_name=validated_data["admin_full_name"],
                password=validated_data["admin_password"],
                role="rh_admin",
                company=company,
                is_staff=True,
            )
        return company
