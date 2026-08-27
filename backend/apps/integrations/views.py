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

from . import catalog
from .connectors import BANCOS_SUPORTADOS, FalhaDeConexao
from .crypto import CredencialIlegivel
from .guard import ConsultaBloqueada
from .models import ExternalConnection, IntegrationMapping
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


class PreviewView(_BaseIntegracao):
    """
    GET /api/v1/integrations/preview/?tabela=X&limite=N

    Uma amostra das primeiras linhas — o "select modelo" que mostra ao
    administrador o que o sistema está lendo, antes de ele mapear campo
    nenhum.

    Passa pelo `ler()` do connector, e não por consulta própria: é o mesmo
    caminho que a sincronização vai usar, com as cinco camadas da trava.
    Uma leitura de amostra por um atalho seria justamente a que ninguém
    lembraria de proteger.
    """

    def get(self, request):
        try:
            conexao = self.exigir_conexao()
        except FalhaDeConexao as erro:
            return Response({"detail": str(erro)}, status=400)

        tabela = request.query_params.get("tabela")
        if not tabela:
            return Response(
                {"detail": "Informe a tabela que deseja visualizar."}, status=400
            )

        # Teto baixo: isto é uma amostra para conferência visual, não
        # exportação. Trazer mais só encheria a tela e a memória.
        try:
            limite = min(int(request.query_params.get("limite", 10)), 50)
        except (TypeError, ValueError):
            limite = 10

        try:
            with conexao.abrir() as conector:
                from .query import validar_contra_schema

                conhecidas = [
                    t.nome_completo for t in conector.schema_descoberto().values()
                ]
                real = validar_contra_schema(tabela, conhecidas, "tabela")

                colunas = conector.listar_colunas(real)
                nomes = [c.nome for c in colunas]
                linhas = conector.ler(real, nomes, limite=limite)

            return Response(
                {
                    "tabela": real,
                    "colunas": nomes,
                    "linhas": [
                        # Tudo vira texto: a tela só exibe, e data, decimal
                        # e bytes de cada banco não têm equivalente em JSON.
                        {k: ("" if v is None else str(v)) for k, v in linha.items()}
                        for linha in linhas
                    ],
                    "total_exibido": len(linhas),
                }
            )
        except (FalhaDeConexao, CredencialIlegivel, ConsultaBloqueada) as erro:
            return Response({"detail": str(erro)}, status=400)
        except Exception:
            logger.exception("Falha inesperada ao ler amostra do banco externo.")
            return Response(
                {"detail": "Não foi possível ler os dados desta tabela."},
                status=400,
            )


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


class CamposDisponiveisView(_BaseIntegracao):
    """
    GET /api/v1/integrations/fields/

    O que o sistema precisa saber de cada entidade, com rótulo, explicação
    e se é obrigatório. Vem da API para a tela não manter uma cópia — uma
    cópia desatualizada pediria um campo que o servidor já não usa.
    """

    def get(self, request):
        return Response(
            {
                "entidades": [
                    {
                        "chave": entidade,
                        "rotulo": catalog.Entidade.ROTULOS[entidade],
                        "campos": catalog.campos_de(entidade),
                    }
                    for entidade in catalog.Entidade.TODAS
                ]
            }
        )


class MappingView(_BaseIntegracao):
    """
    GET /api/v1/integrations/mappings/           → todos
    PUT /api/v1/integrations/mappings/<entidade>/ → grava um

    A gravação valida contra o banco DE VERDADE: tabela e coluna precisam
    existir agora. Aceitar um mapeamento que aponta para o vazio só adiaria
    a descoberta do erro para a primeira sincronização, quando ela custa
    muito mais.
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

    def get(self, request, entidade=None):
        conexao = self.conexao_da_empresa()
        if conexao is None:
            return Response({"mapeamentos": []})

        mapeamentos = {m.entidade: m for m in conexao.mappings.all()}
        return Response(
            {
                "mapeamentos": [
                    {
                        "entidade": chave,
                        "rotulo": catalog.Entidade.ROTULOS[chave],
                        "tabela": mapeamentos[chave].tabela if chave in mapeamentos else "",
                        "campos": mapeamentos[chave].campos if chave in mapeamentos else {},
                        "configurado": chave in mapeamentos,
                    }
                    for chave in catalog.Entidade.TODAS
                ]
            }
        )

    def put(self, request, entidade):
        if entidade not in catalog.Entidade.TODAS:
            return Response({"detail": "Entidade desconhecida."}, status=400)

        try:
            conexao = self.exigir_conexao()
        except FalhaDeConexao as erro:
            return Response({"detail": str(erro)}, status=400)

        tabela = (request.data.get("tabela") or "").strip()
        campos = request.data.get("campos") or {}

        if not tabela:
            return Response(
                {"detail": "Escolha a tabela que contém estes dados."}, status=400
            )
        if not isinstance(campos, dict):
            return Response({"detail": "Formato de campos inválido."}, status=400)

        # Só as chaves do catálogo entram. Um campo inventado no corpo não
        # vira coluna lida — o `campos` é JSON e não tem schema do Django
        # para barrar isso sozinho.
        conhecidas = catalog.chaves_de(entidade)
        campos = {
            k: str(v).strip()
            for k, v in campos.items()
            if k in conhecidas and v and str(v).strip()
        }

        faltando = [
            c["rotulo"]
            for c in catalog.campos_de(entidade)
            if c["obrigatorio"] and not campos.get(c["chave"])
        ]
        if faltando:
            return Response(
                {"detail": f"Falta apontar: {', '.join(faltando)}."}, status=400
            )

        try:
            tabela_real, campos_reais = self._conferir_no_banco(
                conexao, tabela, campos
            )
        except (FalhaDeConexao, CredencialIlegivel, ConsultaBloqueada) as erro:
            return Response({"detail": str(erro)}, status=400)
        except Exception:
            logger.exception("Falha inesperada ao validar mapeamento.")
            return Response(
                {"detail": "Não foi possível conferir o mapeamento no banco."},
                status=400,
            )

        mapeamento, _ = IntegrationMapping.objects.update_or_create(
            connection=conexao,
            entidade=entidade,
            defaults={"tabela": tabela_real, "campos": campos_reais},
        )

        audit.record(
            request.user,
            AuditLog.Action.UPDATE,
            "integration_mapping",
            resource_id=mapeamento.pk,
            resource_label=f"{catalog.Entidade.ROTULOS[entidade]} → {tabela_real}",
            # Registra QUAIS campos passaram a ser importados: é o que a
            # seção 42 pede que o administrador consiga auditar.
            metadata={"entidade": entidade, "campos": sorted(campos_reais)},
        )
        return Response(
            {
                "entidade": entidade,
                "tabela": mapeamento.tabela,
                "campos": mapeamento.campos,
                "configurado": True,
            }
        )

    def _conferir_no_banco(self, conexao, tabela, campos):
        """
        Confere que tabela e colunas existem, e devolve os nomes na grafia
        do banco — não na que o usuário digitou.
        """
        from .query import validar_contra_schema

        with conexao.abrir() as conector:
            nomes_de_tabela = [
                t.nome_completo for t in conector.schema_descoberto().values()
            ]
            tabela_real = validar_contra_schema(tabela, nomes_de_tabela, "tabela")

            colunas = [c.nome for c in conector.listar_colunas(tabela_real)]
            campos_reais = {
                chave: validar_contra_schema(coluna, colunas, "coluna")
                for chave, coluna in campos.items()
            }
        return tabela_real, campos_reais
