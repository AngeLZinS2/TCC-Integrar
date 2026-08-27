"""
A API de conexão e descoberta (P4, E2).

Duas promessas defendidas aqui:

  1. **A senha entra e não sai.** Por nenhuma rota, em nenhum formato, nem
     para quem tem permissão para tudo.
  2. **A conexão é da empresa.** Não existe id na URL para trocar: a
     relação é um-para-um com o tenant, e o tenant vem do token.
"""

import pytest

from apps.audit.models import AuditLog
from apps.companies.models import Company
from apps.integrations.models import ExternalConnection

CONEXAO = "/api/v1/integrations/connection/"
TESTE = "/api/v1/integrations/connection/test/"
DESCOBERTA = "/api/v1/integrations/discovery/"
AMOSTRA = "/api/v1/integrations/preview/"
BANCOS = "/api/v1/integrations/databases/"

SENHA = "S3nh4-secreta-do-ERP"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa Vizinha E2")


@pytest.fixture
def admin(db, django_user_model, company):
    return mk(django_user_model, "admin-e2@x.com", "company_admin", company)


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-e2@x.com", "rh_admin", company)


@pytest.fixture
def colab(db, django_user_model, company):
    return mk(django_user_model, "colab-e2@x.com", "colaborador", company)


@pytest.fixture
def admin_b(db, django_user_model, empresa_b):
    return mk(django_user_model, "admin@b-e2.com", "company_admin", empresa_b)


@pytest.fixture
def conexao(db, company):
    c = ExternalConnection(
        company=company, tipo="postgresql", host="erp.local", porta=5432,
        banco="rh", usuario="leitor",
    )
    c.senha = SENHA
    c.save()
    return c


CORPO = {
    "tipo": "postgresql",
    "host": "erp.local",
    "porta": 5432,
    "banco": "rh",
    "usuario": "integration_readonly",
    "senha": SENHA,
}


# ══════════════════════════════════════════════════════════════════════════
# A senha não sai
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSenhaNaoVaza:
    def test_nao_aparece_ao_criar(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.put(CONEXAO, CORPO, format="json")

        assert resp.status_code == 200, resp.data
        assert SENHA not in str(resp.data)
        assert "senha" not in resp.data

    def test_nao_aparece_ao_ler(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        resp = api_client.get(CONEXAO)

        assert SENHA not in str(resp.data)
        # No lugar dela vai um booleano, que basta para o formulário.
        assert resp.data["tem_senha"] is True

    def test_nao_aparece_na_auditoria(self, api_client, admin):
        """
        A seção 43 da P4 é explícita: nunca registrar credencial. Auditoria
        é justamente o log que mais gente lê depois.
        """
        api_client.force_authenticate(user=admin)
        api_client.put(CONEXAO, CORPO, format="json")

        registro = AuditLog.objects.filter(resource_type="external_connection").first()
        assert registro is not None
        assert SENHA not in str(registro.metadata)
        assert SENHA not in registro.resource_label
        # Mas registra QUE a senha mudou — isso é o que importa auditar.
        assert registro.metadata["senha_alterada"] is True

    def test_o_campo_nem_e_aceito_de_volta_como_leitura(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        corpo = api_client.get(CONEXAO).data
        # Reenviar o que veio não pode apagar nem corromper a senha.
        api_client.put(CONEXAO, {**CORPO, "senha": ""}, format="json")

        conexao.refresh_from_db()
        assert conexao.senha == SENHA
        assert "senha" not in corpo


# ══════════════════════════════════════════════════════════════════════════
# Quem pode
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPermissao:
    @pytest.mark.parametrize("rota", [CONEXAO, DESCOBERTA, BANCOS])
    def test_colaborador_nao_acessa(self, api_client, colab, rota):
        api_client.force_authenticate(user=colab)
        assert api_client.get(rota).status_code == 403

    @pytest.mark.parametrize("rota", [CONEXAO, DESCOBERTA, BANCOS])
    def test_rh_nao_acessa(self, api_client, rh, rota):
        """
        Um mapeamento errado reescreve o cadastro inteiro na próxima
        sincronização. É decisão de estrutura, não rotina de RH.
        """
        api_client.force_authenticate(user=rh)
        assert api_client.get(rota).status_code == 403

    def test_rh_nao_cria_conexao(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        assert api_client.put(CONEXAO, CORPO, format="json").status_code == 403

    def test_colaborador_recebe_403_e_nao_400(self, api_client, colab):
        """
        Payload vazio de quem não pode: 403, nunca 400. Um 400 aqui
        ensinaria o formato da requisição a quem não deveria fazê-la.
        """
        api_client.force_authenticate(user=colab)
        assert api_client.put(CONEXAO, {}, format="json").status_code == 403

    def test_admin_acessa(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        assert api_client.get(CONEXAO).status_code == 200
        assert api_client.get(BANCOS).status_code == 200


# ══════════════════════════════════════════════════════════════════════════
# Isolamento entre empresas
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIsolamento:
    def test_admin_de_outra_empresa_nao_ve_a_conexao(
        self, api_client, admin_b, conexao
    ):
        api_client.force_authenticate(user=admin_b)
        resp = api_client.get(CONEXAO)

        assert resp.status_code == 200
        assert resp.data == {"configurada": False}

    def test_cada_empresa_tem_a_sua(self, api_client, admin, admin_b, conexao):
        api_client.force_authenticate(user=admin_b)
        api_client.put(
            CONEXAO, {**CORPO, "host": "erp-da-vizinha", "senha": "outra"},
            format="json",
        )

        conexao.refresh_from_db()
        assert conexao.host == "erp.local"
        assert conexao.senha == SENHA

        da_vizinha = ExternalConnection.objects.get(company=admin_b.company)
        assert da_vizinha.host == "erp-da-vizinha"

    def test_company_no_corpo_e_ignorado(
        self, api_client, admin, empresa_b
    ):
        """
        "Nunca fazer: company_id vindo do cliente + trust." A conexão nasce
        sempre na empresa de quem pediu.
        """
        api_client.force_authenticate(user=admin)
        api_client.put(
            CONEXAO, {**CORPO, "company": empresa_b.pk}, format="json"
        )
        criada = ExternalConnection.objects.get()
        assert criada.company_id == admin.company_id

    def test_apagar_nao_alcanca_a_da_vizinha(
        self, api_client, admin_b, conexao
    ):
        api_client.force_authenticate(user=admin_b)
        resp = api_client.delete(CONEXAO)

        assert resp.status_code == 204
        # A da outra empresa continua lá: não havia o que apagar.
        assert ExternalConnection.objects.filter(pk=conexao.pk).exists()


# ══════════════════════════════════════════════════════════════════════════
# Validação do formulário
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestValidacao:
    def test_banco_nao_suportado_e_recusado(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.put(
            CONEXAO, {**CORPO, "tipo": "mongodb"}, format="json"
        )
        assert resp.status_code == 400

    def test_criar_sem_senha_e_recusado(self, api_client, admin):
        """
        Salvar sem senha criaria uma conexão que só falha no teste, muito
        depois de o administrador achar que terminou.
        """
        corpo = dict(CORPO)
        corpo.pop("senha")
        api_client.force_authenticate(user=admin)
        resp = api_client.put(CONEXAO, corpo, format="json")

        assert resp.status_code == 400
        assert "senha" in resp.data

    def test_editar_sem_senha_e_permitido(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        corpo = dict(CORPO)
        corpo["senha"] = ""
        corpo["host"] = "erp-novo.local"
        resp = api_client.put(CONEXAO, corpo, format="json")

        assert resp.status_code == 200
        conexao.refresh_from_db()
        assert conexao.host == "erp-novo.local"
        assert conexao.senha == SENHA

    @pytest.mark.parametrize("porta", [0, 70000, -1])
    def test_porta_fora_da_faixa(self, api_client, admin, porta):
        api_client.force_authenticate(user=admin)
        resp = api_client.put(CONEXAO, {**CORPO, "porta": porta}, format="json")
        assert resp.status_code == 400

    @pytest.mark.parametrize("valor", [0, 300])
    def test_timeout_fora_da_faixa(self, api_client, admin, valor):
        """
        O teste de conexão roda dentro da requisição: sem teto, um host
        inalcançável seguraria o worker do servidor web.
        """
        api_client.force_authenticate(user=admin)
        resp = api_client.put(
            CONEXAO, {**CORPO, "timeout_segundos": valor}, format="json"
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════
# Sem conexão configurada
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSemConexao:
    def test_ler_devolve_estado_normal_e_nao_erro(self, api_client, admin):
        """
        "Ainda não configurei" é um estado da tela, não um erro para o app
        tratar — daí 200 com `configurada: false` em vez de 404.
        """
        api_client.force_authenticate(user=admin)
        resp = api_client.get(CONEXAO)

        assert resp.status_code == 200
        assert resp.data["configurada"] is False

    def test_testar_sem_conexao_explica_o_que_fazer(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(TESTE)

        assert resp.status_code == 400
        assert "Configure a conexão" in resp.data["detail"]

    def test_descobrir_sem_conexao_explica_o_que_fazer(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.get(DESCOBERTA)

        assert resp.status_code == 400
        assert "Configure a conexão" in resp.data["detail"]


@pytest.mark.django_db
class TestAmostra:
    def test_colaborador_nao_ve_amostra(self, api_client, colab):
        """
        A amostra mostra DADOS do banco do cliente — nomes, e-mails, CPF.
        É a rota mais sensível do módulo.
        """
        api_client.force_authenticate(user=colab)
        assert api_client.get(AMOSTRA).status_code == 403

    def test_rh_nao_ve_amostra(self, api_client, rh):
        api_client.force_authenticate(user=rh)
        assert api_client.get(AMOSTRA).status_code == 403

    def test_sem_tabela_explica_o_que_falta(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        resp = api_client.get(AMOSTRA)

        assert resp.status_code == 400
        assert "tabela" in resp.data["detail"].lower()

    def test_sem_conexao_explica_o_que_fazer(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.get(f"{AMOSTRA}?tabela=FUNCIONARIOS")

        assert resp.status_code == 400
        assert "Configure a conexão" in resp.data["detail"]

    def test_admin_de_outra_empresa_nao_le_a_amostra(
        self, api_client, admin_b, conexao
    ):
        """
        Sem escopo, o admin da B leria os dados de funcionários da A — o
        vazamento mais direto que este módulo poderia ter.
        """
        api_client.force_authenticate(user=admin_b)
        resp = api_client.get(f"{AMOSTRA}?tabela=FUNCIONARIOS")

        assert resp.status_code == 400
        assert "Configure a conexão" in resp.data["detail"]


@pytest.mark.django_db
class TestBancosSuportados:
    def test_lista_os_quatro(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.get(BANCOS)

        chaves = {b["value"] for b in resp.data}
        assert chaves == {"postgresql", "mysql", "mariadb", "oracle"}


@pytest.mark.django_db
class TestFalhaDeConexao:
    def test_host_inalcancavel_devolve_mensagem_legivel(
        self, api_client, admin, conexao
    ):
        """
        O host aponta para lugar nenhum. O que a tela recebe precisa ser
        uma frase, não o texto cru do driver — que traz host, porta e
        usuário.
        """
        conexao.host = "127.0.0.1"
        conexao.porta = 1  # porta reservada, ninguém escuta
        conexao.timeout_segundos = 1
        conexao.save()

        api_client.force_authenticate(user=admin)
        resp = api_client.post(TESTE)

        assert resp.status_code == 400
        assert resp.data["ok"] is False
        assert SENHA not in str(resp.data)
        assert resp.data["detail"]

    def test_a_falha_fica_registrada_na_conexao(
        self, api_client, admin, conexao
    ):
        conexao.host = "127.0.0.1"
        conexao.porta = 1
        conexao.timeout_segundos = 1
        conexao.save()

        api_client.force_authenticate(user=admin)
        api_client.post(TESTE)

        conexao.refresh_from_db()
        assert conexao.status == ExternalConnection.Status.FALHA
        assert conexao.ultimo_teste_em is not None
        assert conexao.ultimo_erro
        assert SENHA not in conexao.ultimo_erro
