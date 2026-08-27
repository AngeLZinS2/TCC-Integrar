"""
A conexão com o banco do cliente.

Uma por empresa. A senha nunca é gravada em texto puro e nunca sai numa
resposta de API — o serializer não a expõe, e o único caminho que a lê é
o connector, na hora de abrir a conexão.
"""

from django.conf import settings
from django.db import models

from .connectors import BANCOS_SUPORTADOS
from .crypto import cifrar, decifrar


class ExternalConnection(models.Model):
    """
    Como alcançar o banco de origem daquela empresa.

    O que este modelo NÃO tem, de propósito: nenhum campo de SQL. A P4
    (seção 10) proíbe consulta livre, e guardar SQL aqui seria o começo de
    permitir uma.
    """

    class Status(models.TextChoices):
        NAO_TESTADA = "untested", "Nunca testada"
        OK = "ok", "Conectando"
        FALHA = "failed", "Com falha"

    company = models.OneToOneField(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="external_connection",
    )

    tipo = models.CharField(
        max_length=20,
        choices=BANCOS_SUPORTADOS,
        verbose_name="Tipo do banco",
    )
    host = models.CharField(max_length=255)
    porta = models.PositiveIntegerField(null=True, blank=True)
    banco = models.CharField(
        max_length=128,
        verbose_name="Banco de dados",
        help_text="No Oracle, informe o service name.",
    )
    schema = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Opcional. Vazio usa o padrão do banco.",
    )
    usuario = models.CharField(max_length=128)

    # Cifrada. Nunca lida diretamente: use `senha`.
    senha_cifrada = models.TextField(blank=True, default="", editable=False)

    usar_ssl = models.BooleanField(default=False, verbose_name="Usar SSL")
    timeout_segundos = models.PositiveIntegerField(
        default=10,
        help_text="Tempo máximo de espera ao conectar.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Desligada, nenhuma sincronização roda.",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.NAO_TESTADA
    )
    ultimo_teste_em = models.DateTimeField(null=True, blank=True)
    ultimo_erro = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_connections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conexão externa"
        verbose_name_plural = "Conexões externas"

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.host}/{self.banco}"

    # ── Senha ──────────────────────────────────────────────────────────

    @property
    def senha(self) -> str:
        """Decifra sob demanda. Só o connector chama."""
        return decifrar(self.senha_cifrada)

    @senha.setter
    def senha(self, valor: str) -> None:
        # Valor vazio não apaga a senha guardada: o formulário de edição
        # manda o campo em branco quando o administrador não quer trocá-la.
        if valor:
            self.senha_cifrada = cifrar(valor)

    @property
    def tem_senha(self) -> bool:
        """O que a API mostra no lugar da senha."""
        return bool(self.senha_cifrada)

    def credenciais(self):
        """Monta o objeto que o connector consome."""
        from .connectors import Credenciais

        return Credenciais(
            host=self.host,
            porta=self.porta or 0,
            banco=self.banco,
            usuario=self.usuario,
            senha=self.senha,
            schema=self.schema,
            usar_ssl=self.usar_ssl,
            timeout_segundos=self.timeout_segundos,
        )

    def abrir(self):
        """Devolve o connector configurado para esta conexão."""
        from .connectors import connector_para

        return connector_para(self.tipo, self.credenciais())
