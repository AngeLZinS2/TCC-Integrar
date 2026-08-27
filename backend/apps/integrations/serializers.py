"""
Serializers da conexão externa.

A regra que governa este arquivo: **a senha entra, nunca sai**. Ela é
`write_only`, e o que a tela recebe no lugar é `tem_senha` — um booleano
que basta para o formulário mostrar "senha já cadastrada" sem devolver o
valor a quem quer que esteja olhando a tela junto.
"""

from rest_framework import serializers

from .connectors import CONNECTORES
from .models import ExternalConnection


class ExternalConnectionSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
        help_text="Deixe em branco para manter a senha já cadastrada.",
    )
    tem_senha = serializers.BooleanField(read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ExternalConnection
        fields = [
            "id", "tipo", "tipo_display", "host", "porta", "banco", "schema",
            "usuario", "senha", "tem_senha", "usar_ssl", "timeout_segundos",
            "is_active", "status", "status_display",
            "ultimo_teste_em", "ultimo_erro", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "ultimo_teste_em", "ultimo_erro", "updated_at",
        ]

    def validate_tipo(self, tipo):
        if str(tipo).lower() not in CONNECTORES:
            raise serializers.ValidationError("Banco não suportado.")
        return str(tipo).lower()

    def validate_porta(self, porta):
        if porta in (None, ""):
            return None
        if not 1 <= int(porta) <= 65535:
            raise serializers.ValidationError("Porta fora da faixa válida.")
        return porta

    def validate_timeout_segundos(self, valor):
        # Teto de 60s: o teste de conexão roda dentro da requisição, e um
        # host inalcançável seguraria o worker do servidor web até o
        # timeout. Piso de 1s porque zero desliga o limite no driver.
        if not 1 <= int(valor) <= 60:
            raise serializers.ValidationError(
                "O tempo de espera deve ficar entre 1 e 60 segundos."
            )
        return valor

    def validate(self, attrs):
        """
        Na criação, a senha é obrigatória; na edição, opcional.

        Sem isto, salvar o formulário sem tocar no campo de senha criaria
        uma conexão sem credencial nenhuma — que só falharia no teste,
        muito depois de o administrador achar que tinha terminado.
        """
        criando = self.instance is None
        if criando and not attrs.get("senha"):
            raise serializers.ValidationError(
                {"senha": "Informe a senha do usuário de leitura."}
            )
        return attrs

    def create(self, validated_data):
        senha = validated_data.pop("senha", "")
        conexao = ExternalConnection(**validated_data)
        conexao.senha = senha
        conexao.save()
        return conexao

    def update(self, instance, validated_data):
        senha = validated_data.pop("senha", "")
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        # O setter ignora string vazia de propósito: o formulário manda o
        # campo em branco quando não se quer trocar a senha.
        instance.senha = senha
        instance.save()
        return instance


class TabelaSerializer(serializers.Serializer):
    """Uma tabela descoberta. Só leitura — nada disto vem do cliente."""

    nome = serializers.CharField(read_only=True)
    schema = serializers.CharField(read_only=True)
    nome_completo = serializers.CharField(read_only=True)


class ColunaSerializer(serializers.Serializer):
    nome = serializers.CharField(read_only=True)
    tipo = serializers.CharField(read_only=True)
    aceita_nulo = serializers.BooleanField(read_only=True)
    e_chave = serializers.BooleanField(read_only=True)
