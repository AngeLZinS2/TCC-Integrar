"""
Endpoints da conexão e da descoberta.

Nenhuma rota daqui aceita SQL — a seção 10 da P4 proíbe consulta livre, e
o que o administrador manda são nomes escolhidos de listas que vieram do
próprio banco dele.

Toda rota é escopada por `request.user.company`: a conexão é
`OneToOne` com a empresa, e o queryset nunca aceita id vindo de fora.
"""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.users import rbac

from .connectors import BANCOS_SUPORTADOS, FalhaDeConexao
from .crypto import CredencialIlegivel
from .guard import ConsultaBloqueada
from .models import ExternalConnection
from .serializers import (
    ColunaSerializer,
    ExternalConnectionSerializer,
    TabelaSerializer,
)

logger = logging.getLogger(__name__)


class _BaseIntegracao(APIView):
    """Escopo e permissão, num lugar só."""

    permission_classes = [IsAuthenticated]
    permissao_exigida = rbac.INTEGRATION_READ

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # Checado antes de qualquer leitura de corpo: quem não administra a
        # empresa recebe 403 sem aprender o formato da requisição.
        if not request.user.has_perm_code(self.permissao_exigida):
            raise PermissionDenied(
                "Apenas o administrador da empresa configura a integração."
            )

    def conexao_da_empresa(self):
        """
        A conexão desta empresa, ou None.

        Nunca por id: a relação é um-para-um com a empresa, então o tenant
        já determina o registro. Não há parâmetro que o cliente possa
        trocar para alcançar outro.
        """
        return ExternalConnection.objects.filter(
            company_id=self.request.user.company_id
        ).first()

    def exigir_conexao(self):
        conexao = self.conexao_da_empresa()
        if conexao is None:
            raise FalhaDeConexao(
                "Nenhum banco foi conectado ainda. Configure a conexão primeiro."
            )
        return conexao


class BancosSuportadosView(_BaseIntegracao):
    """
    GET /api/v1/integrations/databases/

    A lista vem da API para o app não manter uma cópia: uma cópia
    desatualizada ofereceria um banco que o servidor recusa.
    """

    def get(self, request):
        return Response(
            [{"value": chave, "label": rotulo} for chave, rotulo in BANCOS_SUPORTADOS]
        )


class ConnectionView(_BaseIntegracao):
    """
    GET  /api/v1/integrations/connection/  → a conexão, sem a senha
    PUT  /api/v1/integrations/connection/  → cria ou atualiza
    DELETE                                 → remove
    """

    def get_permissao(self):
        return (
            rbac.INTEGRATION_READ
            if self.request.method == "GET"
            else rbac.INTEGRATION_MANAGE
        )

    def initial(self, request, *args, **kwargs):
        self.permissao_exigida = self.get_permissao()
        super().initial(request, *args, **kwargs)

    def get(self, request):
        conexao = self.conexao_da_empresa()
        if conexao is None:
            # 200 com corpo vazio, e não 404: "ainda não configurei" é um
            # estado normal da tela, não um erro para o app tratar.
            return Response({"configurada": False})
        dados = ExternalConnectionSerializer(conexao).data
        dados["configurada"] = True
        return Response(dados)

    def put(self, request):
        conexao = self.conexao_da_empresa()
        serializer = ExternalConnectionSerializer(conexao, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            conexao = serializer.save(company_id=request.user.company_id)
        except CredencialIlegivel as erro:
            return Response({"detail": str(erro)}, status=status.HTTP_400_BAD_REQUEST)

        # A auditoria registra a mudança, NUNCA a credencial. Só host,
        # banco e usuário — o suficiente para saber o que mudou.
        audit.record(
            request.user,
            AuditLog.Action.UPDATE,
            "external_connection",
            resource_id=conexao.pk,
            resource_label=f"{conexao.host}/{conexao.banco}",
            metadata={
                "tipo": conexao.tipo,
                "usuario": conexao.usuario,
                "senha_alterada": bool(request.data.get("senha")),
            },
        )
        return Response(ExternalConnectionSerializer(conexao).data)

    def delete(self, request):
        conexao = self.conexao_da_empresa()
        if conexao is None:
            return Response(status=status.HTTP_204_NO_CONTENT)

        audit.record(
            request.user,
            AuditLog.Action.DELETE,
            "external_connection",
            resource_id=conexao.pk,
            resource_label=f"{conexao.host}/{conexao.banco}",
        )
        conexao.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TestConnectionView(_BaseIntegracao):
    """
    POST /api/v1/integrations/connection/test/

    Abre, lista tabelas e fecha. Grava o resultado para a tela poder
    mostrar "última verificação" sem testar de novo a cada visita.
    """

    permissao_exigida = rbac.INTEGRATION_MANAGE

    def post(self, request):
        try:
            conexao = self.exigir_conexao()
        except FalhaDeConexao as erro:
            return Response({"ok": False, "detail": str(erro)}, status=400)

        try:
            with conexao.abrir() as conector:
                tabelas = conector.listar_tabelas()
            conexao.status = ExternalConnection.Status.OK
            conexao.ultimo_erro = ""
            resposta = {
                "ok": True,
                "detail": "Conexão estabelecida.",
                "tabelas_encontradas": len(tabelas),
            }
        except (FalhaDeConexao, CredencialIlegivel, ConsultaBloqueada) as erro:
            conexao.status = ExternalConnection.Status.FALHA
            conexao.ultimo_erro = str(erro)
            resposta = {"ok": False, "detail": str(erro)}
        except Exception:
            # Erro inesperado do driver: o texto cru costuma trazer host,
            # porta e usuário, e não deve chegar à tela.
            logger.exception("Falha inesperada ao testar conexão externa.")
            conexao.status = ExternalConnection.Status.FALHA
            conexao.ultimo_erro = "Falha inesperada ao conectar."
            resposta = {"ok": False, "detail": conexao.ultimo_erro}

        conexao.ultimo_teste_em = timezone.now()
        conexao.save(update_fields=["status", "ultimo_erro", "ultimo_teste_em"])

        audit.record(
            request.user,
            AuditLog.Action.UPDATE,
            "external_connection",
            resource_id=conexao.pk,
            resource_label=f"{conexao.host}/{conexao.banco}",
            metadata={"acao": "teste", "resultado": conexao.status},
        )
        return Response(resposta, status=200 if resposta["ok"] else 400)


class DiscoveryView(_BaseIntegracao):
    """
    GET /api/v1/integrations/discovery/            → tabelas
    GET /api/v1/integrations/discovery/?tabela=X   → colunas de X

    A P4 (seção 14) pede que o sistema sugira, mas nunca assuma: aqui só
    se devolve o que o banco reportou. Quem confirma o significado é o
    administrador, no mapeamento.
    """

    def get(self, request):
        try:
            conexao = self.exigir_conexao()
        except FalhaDeConexao as erro:
            return Response({"detail": str(erro)}, status=400)

        tabela = request.query_params.get("tabela")

        try:
            with conexao.abrir() as conector:
                if tabela:
                    # `listar_colunas` recebe o nome conferido contra o
                    # schema: um nome inventado não chega ao banco.
                    from .query import validar_contra_schema

                    conhecidas = [
                        t.nome_completo for t in conector.schema_descoberto().values()
                    ]
                    real = validar_contra_schema(tabela, conhecidas, "tabela")
                    colunas = conector.listar_colunas(real)
                    return Response(
                        {
                            "tabela": real,
                            "colunas": ColunaSerializer(colunas, many=True).data,
                        }
                    )

                tabelas = conector.listar_tabelas()
                return Response(
                    {
                        "tabelas": [
                            {
                                "nome": t.nome,
                                "schema": t.schema,
                                "nome_completo": t.nome_completo,
                            }
                            for t in tabelas
                        ]
                    }
                )
        except (FalhaDeConexao, CredencialIlegivel, ConsultaBloqueada) as erro:
            return Response({"detail": str(erro)}, status=400)
        except Exception:
            logger.exception("Falha inesperada na descoberta de schema.")
            return Response(
                {"detail": "Não foi possível ler a estrutura do banco."}, status=400
            )
