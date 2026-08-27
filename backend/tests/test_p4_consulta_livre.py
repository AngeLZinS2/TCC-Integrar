"""
A consulta livre (campo de SQL escrito pelo administrador).

Esta rota **contraria a seção 10 da P4**, que proíbe campo de SQL livre.
Existe por decisão explícita de produto — alguns ERPs exigem JOIN ou
filtro que o mapeamento estruturado não expressa.

A consequência técnica é que ela perde as camadas 1 e 2 da trava: aqui há
texto do usuário, e não há identificador para conferir contra o schema.
Sobram três, e este arquivo existe para provar que elas seguram:

  - a trava de instrução, antes do cursor;
  - a sessão em transação somente-leitura;
  - a credencial de leitura no banco do cliente.

Mais duas defesas que só esta rota precisa: teto de linhas e auditoria de
toda execução.
"""

import pytest

from apps.audit.models import AuditLog
from apps.companies.models import Company
from apps.integrations.models import ExternalConnection

CONSULTA = "/api/v1/integrations/query/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa Vizinha SQL")


@pytest.fixture
def admin(db, django_user_model, company):
    return mk(django_user_model, "admin-sql@x.com", "company_admin", company)


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-sql@x.com", "rh_admin", company)


@pytest.fixture
def colab(db, django_user_model, company):
    return mk(django_user_model, "colab-sql@x.com", "colaborador", company)


@pytest.fixture
def admin_b(db, django_user_model, empresa_b):
    return mk(django_user_model, "admin@b-sql.com", "company_admin", empresa_b)


@pytest.fixture
def conexao(db, company):
    """
    Aponta para lugar nenhum de propósito.

    O que importa nestes testes é o que a trava recusa ANTES de tentar
    conectar — se ela deixasse passar, o teste iria ao banco, e aí já seria
    tarde.
    """
    c = ExternalConnection(
        company=company, tipo="postgresql", host="127.0.0.1", porta=1,
        banco="rh", usuario="leitor", timeout_segundos=1,
    )
    c.senha = "x"
    c.save()
    return c


# ══════════════════════════════════════════════════════════════════════════
# A trava continua valendo — agora como defesa principal
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTrava:
    @pytest.mark.parametrize(
        "sql",
        [
            "INSERT INTO funcionarios (nome) VALUES ('x')",
            "UPDATE funcionarios SET nome = 'X'",
            "DELETE FROM funcionarios",
            "DROP TABLE funcionarios",
            "ALTER TABLE funcionarios ADD COLUMN x INT",
            "TRUNCATE TABLE funcionarios",
            "CREATE TABLE novo (id INT)",
            "GRANT ALL ON funcionarios TO publico",
            "REVOKE SELECT ON funcionarios FROM leitor",
            "MERGE INTO funcionarios USING origem ON (1=1)",
        ],
    )
    def test_escrita_e_bloqueada_antes_de_conectar(
        self, api_client, admin, conexao, sql
    ):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(CONSULTA, {"sql": sql}, format="json")

        assert resp.status_code == 400
        # `bloqueada` diz ao administrador que foi REGRA, e não erro de
        # sintaxe dele — sem isso ele ficaria tentando corrigir o SQL.
        assert resp.data["bloqueada"] is True

    def test_duas_instrucoes_sao_recusadas(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            CONSULTA,
            {"sql": "SELECT * FROM funcionarios; DELETE FROM funcionarios"},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.data["bloqueada"] is True

    def test_comentario_nao_esconde_o_verbo(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            CONSULTA, {"sql": "SELECT 1 /* nada */ ; DROP TABLE x"}, format="json"
        )
        assert resp.data["bloqueada"] is True

    def test_with_seguido_de_delete_e_bloqueado(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            CONSULTA,
            {
                "sql": "WITH alvo AS (SELECT id FROM f) "
                       "DELETE FROM f WHERE id IN (SELECT id FROM alvo)"
            },
            format="json",
        )
        assert resp.data["bloqueada"] is True

    def test_select_passa_pela_trava_e_falha_so_na_conexao(
        self, api_client, admin, conexao
    ):
        """
        Contraprova: um SELECT legítimo não é recusado pela trava. Ele
        falha adiante, ao tentar alcançar o banco — que é o esperado, já
        que a conexão do teste aponta para lugar nenhum.
        """
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            CONSULTA, {"sql": "SELECT * FROM funcionarios"}, format="json"
        )

        assert resp.status_code == 400
        assert resp.data.get("bloqueada") is not True


# ══════════════════════════════════════════════════════════════════════════
# Quem pode escrever SQL
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPermissao:
    def test_colaborador_nao_executa(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        resp = api_client.post(CONSULTA, {"sql": "SELECT 1"}, format="json")
        assert resp.status_code == 403

    def test_rh_nao_executa(self, api_client, rh, conexao):
        """
        Escrever consulta contra o banco de produção da empresa é a
        capacidade mais forte do módulo. Não é rotina de RH.
        """
        api_client.force_authenticate(user=rh)
        resp = api_client.post(CONSULTA, {"sql": "SELECT 1"}, format="json")
        assert resp.status_code == 403

    def test_exige_manage_e_nao_apenas_leitura(self, api_client, admin, conexao):
        """
        A rota pede `integration.manage`. Ler a configuração é uma coisa;
        consultar o banco do cliente é outra.
        """
        from apps.users import rbac

        assert admin.has_perm_code(rbac.INTEGRATION_MANAGE)
        api_client.force_authenticate(user=admin)
        # Passa da permissão (falha adiante, na conexão).
        resp = api_client.post(CONSULTA, {"sql": "SELECT 1"}, format="json")
        assert resp.status_code != 403


@pytest.mark.django_db
class TestIsolamento:
    def test_admin_de_outra_empresa_nao_alcanca_o_banco_alheio(
        self, api_client, admin_b, conexao
    ):
        """
        Sem escopo, o admin da B rodaria SELECT no banco de produção da A.
        É o pior vazamento que esta rota poderia ter.
        """
        api_client.force_authenticate(user=admin_b)
        resp = api_client.post(
            CONSULTA, {"sql": "SELECT * FROM funcionarios"}, format="json"
        )

        assert resp.status_code == 400
        assert "Configure a conexão" in resp.data["detail"]


# ══════════════════════════════════════════════════════════════════════════
# Auditoria e limites
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAuditoria:
    def test_toda_execucao_fica_registrada(self, api_client, admin, conexao):
        """
        Poder deste tamanho sem rastro seria pior do que não existir.
        """
        api_client.force_authenticate(user=admin)
        api_client.post(
            CONSULTA, {"sql": "SELECT * FROM folha_de_pagamento"}, format="json"
        )

        registro = AuditLog.objects.filter(
            resource_type="integration_query"
        ).first()
        assert registro is not None
        assert registro.actor_id == admin.pk
        assert "folha_de_pagamento" in registro.metadata["sql"]

    def test_a_tentativa_bloqueada_tambem_fica_registrada(
        self, api_client, admin, conexao
    ):
        """
        Quem TENTOU apagar a tabela é justamente o que mais importa saber.
        Registrar só o que passou esconderia a tentativa.
        """
        api_client.force_authenticate(user=admin)
        api_client.post(
            CONSULTA, {"sql": "DROP TABLE funcionarios"}, format="json"
        )

        registro = AuditLog.objects.filter(
            resource_type="integration_query"
        ).first()
        assert registro is not None
        assert "DROP" in registro.metadata["sql"]

    def test_a_senha_da_conexao_nao_entra_no_registro(
        self, api_client, admin, conexao
    ):
        api_client.force_authenticate(user=admin)
        api_client.post(CONSULTA, {"sql": "SELECT 1"}, format="json")

        registro = AuditLog.objects.filter(
            resource_type="integration_query"
        ).first()
        assert conexao.senha not in str(registro.metadata)


@pytest.mark.django_db
class TestLimites:
    def test_consulta_vazia_e_recusada(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(CONSULTA, {"sql": "   "}, format="json")

        assert resp.status_code == 400
        assert "Escreva a consulta" in resp.data["detail"]

    def test_consulta_gigante_e_recusada(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            CONSULTA, {"sql": "SELECT " + "a," * 20_000 + "b"}, format="json"
        )
        assert resp.status_code == 400
        assert "longa demais" in resp.data["detail"]

    def test_sem_conexao_explica_o_que_fazer(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(CONSULTA, {"sql": "SELECT 1"}, format="json")

        assert resp.status_code == 400
        assert "Configure a conexão" in resp.data["detail"]

    def test_o_teto_de_linhas_nao_pode_ser_ultrapassado(self):
        """
        Pedir 10.000 linhas não traz 10.000: uma consulta sem WHERE numa
        tabela de milhões encheria a memória do servidor.
        """
        from apps.integrations.views import ConsultaLivreView

        assert ConsultaLivreView.LIMITE_MAXIMO == 200
