"""
As credenciais do banco do cliente (P4, seções 7, 36 e 43).

A promessa: a senha do banco de produção de uma empresa entra no sistema,
é usada para ler, e não sai por lugar nenhum — nem em resposta de API, nem
em log, nem em auditoria, nem para outra empresa.
"""

import logging

import pytest

from apps.companies.models import Company
from apps.integrations.connectors import BANCOS_SUPORTADOS, connector_para
from apps.integrations.connectors.base import Credenciais, FalhaDeConexao
from apps.integrations.crypto import CredencialIlegivel, cifrar, decifrar
from apps.integrations.models import ExternalConnection

SENHA = "S3nh4-D0-ERP-em-Producao!"


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa Vizinha P4")


@pytest.fixture
def conexao(db, company):
    c = ExternalConnection(
        company=company,
        tipo="postgresql",
        host="erp.interno.local",
        porta=5432,
        banco="rh",
        usuario="integration_readonly",
    )
    c.senha = SENHA
    c.save()
    return c


class TestCifra:
    def test_ida_e_volta(self):
        assert decifrar(cifrar(SENHA)) == SENHA

    def test_o_texto_cifrado_nao_contem_a_senha(self):
        cifrado = cifrar(SENHA)
        assert SENHA not in cifrado
        assert "S3nh4" not in cifrado

    def test_duas_cifras_da_mesma_senha_sao_diferentes(self):
        """
        Fernet usa vetor aleatório. Sem isso, duas empresas com a mesma
        senha teriam o mesmo texto guardado — e quem lesse a tabela saberia
        disso sem decifrar nada.
        """
        assert cifrar(SENHA) != cifrar(SENHA)

    def test_vazio_volta_vazio(self):
        assert decifrar("") == ""

    def test_texto_corrompido_avisa_em_vez_de_estourar(self):
        with pytest.raises(CredencialIlegivel) as erro:
            decifrar("isto-nao-e-um-token-fernet")
        # A mensagem precisa dizer o que fazer, não "InvalidToken".
        assert "novamente" in str(erro.value)

    def test_a_senha_nao_aparece_no_log_quando_falha(self, caplog):
        # O LOGGING do projeto define `propagate: False` para "apps", então
        # o registro nunca chega à raiz — onde o caplog escuta por padrão.
        # Sem ligar o handler no logger certo, a asserção de que a senha não
        # vazou passaria sem ter olhado nada.
        logger = logging.getLogger("apps.integrations.crypto")
        logger.addHandler(caplog.handler)
        try:
            with caplog.at_level(logging.ERROR):
                with pytest.raises(CredencialIlegivel):
                    decifrar(cifrar(SENHA)[:-6] + "xxxxxx")
        finally:
            logger.removeHandler(caplog.handler)

        registrado = " | ".join(r.getMessage() for r in caplog.records)
        assert registrado, "nada foi registrado — o teste não olhou nada"
        assert "chave de criptografia" in registrado.lower()
        assert SENHA not in registrado


@pytest.mark.django_db
class TestModelo:
    def test_a_senha_e_gravada_cifrada(self, conexao):
        conexao.refresh_from_db()
        assert conexao.senha_cifrada
        assert SENHA not in conexao.senha_cifrada

    def test_a_senha_volta_pela_propriedade(self, conexao):
        conexao.refresh_from_db()
        assert conexao.senha == SENHA

    def test_gravar_vazio_nao_apaga_a_senha(self, conexao):
        """
        O formulário de edição manda a senha em branco quando o
        administrador não quer trocá-la. Apagar aí quebraria a conexão sem
        ninguém pedir.
        """
        conexao.senha = ""
        conexao.save()
        conexao.refresh_from_db()
        assert conexao.senha == SENHA

    def test_tem_senha_e_o_que_a_api_mostra(self, conexao):
        assert conexao.tem_senha is True

    def test_a_senha_nao_esta_na_representacao_do_objeto(self, conexao):
        assert SENHA not in str(conexao)
        assert SENHA not in repr(conexao)

    def test_uma_conexao_por_empresa(self, company, conexao):
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            ExternalConnection.objects.create(
                company=company, tipo="mysql", host="x", banco="y", usuario="z"
            )

    def test_empresas_diferentes_tem_conexoes_separadas(
        self, company, empresa_b, conexao
    ):
        outra = ExternalConnection(
            company=empresa_b, tipo="oracle", host="outro", banco="ORCL",
            usuario="leitor",
        )
        outra.senha = "senha-da-vizinha"
        outra.save()

        assert conexao.senha == SENHA
        assert outra.senha == "senha-da-vizinha"
        assert conexao.senha_cifrada != outra.senha_cifrada


@pytest.mark.django_db
class TestCredenciaisParaOConnector:
    def test_monta_o_objeto_com_a_senha_decifrada(self, conexao):
        cred = conexao.credenciais()
        assert isinstance(cred, Credenciais)
        assert cred.senha == SENHA
        assert cred.host == "erp.interno.local"

    def test_abrir_devolve_o_connector_do_tipo(self, conexao):
        from apps.integrations.connectors.postgres import PostgresConnector

        assert isinstance(conexao.abrir(), PostgresConnector)

    def test_tipo_desconhecido_e_recusado(self):
        with pytest.raises(FalhaDeConexao) as erro:
            connector_para(
                "mongodb",
                Credenciais(host="x", porta=1, banco="y", usuario="z", senha=""),
            )
        assert "não suportado" in str(erro.value)


class TestBancosSuportados:
    def test_os_quatro_pedidos_estao_disponiveis(self):
        chaves = {chave for chave, _ in BANCOS_SUPORTADOS}
        assert chaves == {"postgresql", "mysql", "mariadb", "oracle"}

    @pytest.mark.parametrize("chave", ["postgresql", "mysql", "mariadb", "oracle"])
    def test_cada_um_instancia_e_tem_o_dialeto(self, chave):
        cred = Credenciais(
            host="h", porta=0, banco="b", usuario="u", senha="p"
        )
        conector = connector_para(chave, cred)

        # A citação é o que separa os dialetos: MySQL usa crase, os outros
        # usam aspas duplas.
        citado = conector.citar("tabela")
        assert citado.startswith(("`", '"'))
        assert "tabela" in citado

        # E a paginação, que difere entre LIMIT e OFFSET/FETCH.
        paginado = conector.aplicar_paginacao("SELECT 1", 10, 5)
        assert "10" in paginado and "5" in paginado

    def test_o_driver_de_cada_banco_esta_instalado(self):
        """
        Sem isto, a falta de um driver só apareceria quando um cliente real
        tentasse conectar — e o erro seria um ImportError cru na tela.
        """
        import oracledb  # noqa: F401
        import psycopg2  # noqa: F401
        import pymysql  # noqa: F401

    def test_citacao_neutraliza_a_propria_aspa(self):
        """Nome com aspa dentro não pode fechar o identificador."""
        cred = Credenciais(host="h", porta=0, banco="b", usuario="u", senha="")

        pg = connector_para("postgresql", cred)
        assert pg.citar('tab"ela') == '"tab""ela"'

        my = connector_para("mysql", cred)
        assert my.citar("tab`ela") == "`tab``ela`"
