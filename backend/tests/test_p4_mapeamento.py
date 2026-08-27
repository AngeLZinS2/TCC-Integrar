"""
Mapeamento das entidades (P4, E3 / seções 15 a 18).

O mapeamento é onde o administrador diz o que cada tabela e cada coluna do
banco dele significam aqui. Duas coisas precisam ficar travadas:

  1. **Nada é aceito sem existir.** Tabela e coluna são conferidas contra
     o banco de verdade. Um mapeamento apontando para o vazio só adiaria a
     descoberta do erro para a primeira sincronização, quando ela custa
     muito mais.
  2. **O `campos` é JSON, e JSON não tem schema.** Uma chave inventada no
     corpo não pode virar coluna lida.
"""

import pytest

from apps.audit.models import AuditLog
from apps.companies.models import Company
from apps.integrations.catalog import Entidade, chaves_de, obrigatorios_de
from apps.integrations.models import ExternalConnection, IntegrationMapping

MAPEAMENTOS = "/api/v1/integrations/mappings/"
CAMPOS = "/api/v1/integrations/fields/"


def mk(model, email, role, company, **kw):
    return model.objects.create_user(
        email=email, full_name=email.split("@")[0].title(),
        password="senha@123", role=role, company=company, **kw
    )


@pytest.fixture
def empresa_b(db):
    return Company.objects.create(name="Empresa Vizinha E3")


@pytest.fixture
def admin(db, django_user_model, company):
    return mk(django_user_model, "admin-e3@x.com", "company_admin", company)


@pytest.fixture
def rh(db, django_user_model, company):
    return mk(django_user_model, "rh-e3@x.com", "rh_admin", company)


@pytest.fixture
def colab(db, django_user_model, company):
    return mk(django_user_model, "colab-e3@x.com", "colaborador", company)


@pytest.fixture
def admin_b(db, django_user_model, empresa_b):
    return mk(django_user_model, "admin@b-e3.com", "company_admin", empresa_b)


@pytest.fixture
def conexao(db, company):
    c = ExternalConnection(
        company=company, tipo="postgresql", host="erp.local", porta=5432,
        banco="rh", usuario="leitor",
    )
    c.senha = "x"
    c.save()
    return c


# ══════════════════════════════════════════════════════════════════════════
# O catálogo de campos
# ══════════════════════════════════════════════════════════════════════════

class TestCatalogo:
    def test_toda_entidade_exige_identificador_e_nome(self):
        """
        Sem identificador não dá para reconhecer o mesmo registro entre
        duas sincronizações; sem nome não dá para criar nada.
        """
        for entidade in Entidade.TODAS:
            assert set(obrigatorios_de(entidade)) == {"identificador", "nome"}

    def test_cpf_e_telefone_sao_opcionais(self):
        """
        Minimização (seção 42): dado sensível só vem se o administrador
        apontar a coluna. Nada é trazido por padrão.
        """
        obrigatorios = obrigatorios_de(Entidade.FUNCIONARIO)
        assert "cpf" not in obrigatorios
        assert "telefone" not in obrigatorios

    def test_os_rotulos_nao_usam_jargao(self):
        """
        Seção 44: o administrador não é programador. "FK source" e "target
        column" não podem aparecer.
        """
        from apps.integrations.catalog import CAMPOS

        for campos in CAMPOS.values():
            for campo in campos:
                texto = (campo["rotulo"] + campo["ajuda"]).lower()
                for jargao in ["fk", "foreign key", "target column", "query"]:
                    assert jargao not in texto, f"{campo['rotulo']} usa '{jargao}'"


@pytest.mark.django_db
class TestApiDeCampos:
    def test_devolve_as_tres_entidades_com_os_campos(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.get(CAMPOS)

        assert resp.status_code == 200
        entidades = {e["chave"] for e in resp.data["entidades"]}
        assert entidades == set(Entidade.TODAS)

        funcionarios = next(
            e for e in resp.data["entidades"] if e["chave"] == Entidade.FUNCIONARIO
        )
        # Cada campo traz rótulo, explicação e se é obrigatório: é o que a
        # tela precisa para separar os dois grupos.
        for campo in funcionarios["campos"]:
            assert campo["rotulo"] and campo["ajuda"]
            assert isinstance(campo["obrigatorio"], bool)

    def test_colaborador_nao_acessa(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        assert api_client.get(CAMPOS).status_code == 403


# ══════════════════════════════════════════════════════════════════════════
# Permissão e isolamento
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPermissao:
    def test_colaborador_nao_le_mapeamentos(self, api_client, colab):
        api_client.force_authenticate(user=colab)
        assert api_client.get(MAPEAMENTOS).status_code == 403

    def test_rh_nao_mapeia(self, api_client, rh, conexao):
        """
        Um mapeamento errado reescreve o cadastro inteiro na próxima
        sincronização. É decisão de estrutura, não rotina de RH.
        """
        api_client.force_authenticate(user=rh)
        resp = api_client.put(
            f"{MAPEAMENTOS}employee/",
            {"tabela": "X", "campos": {}},
            format="json",
        )
        assert resp.status_code == 403

    def test_admin_de_outra_empresa_nao_ve_o_mapeamento(
        self, api_client, admin_b, conexao
    ):
        IntegrationMapping.objects.create(
            connection=conexao, entidade=Entidade.SETOR,
            tabela="DEPTO", campos={"identificador": "COD", "nome": "DESC"},
        )
        api_client.force_authenticate(user=admin_b)
        resp = api_client.get(MAPEAMENTOS)

        assert resp.status_code == 200
        assert resp.data["mapeamentos"] == []


# ══════════════════════════════════════════════════════════════════════════
# Validação, sem tocar no banco externo
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestValidacao:
    def test_entidade_desconhecida_e_recusada(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        resp = api_client.put(
            f"{MAPEAMENTOS}veiculos/", {"tabela": "X"}, format="json"
        )
        assert resp.status_code == 400
        assert "desconhecida" in resp.data["detail"].lower()

    def test_sem_tabela_e_recusado(self, api_client, admin, conexao):
        api_client.force_authenticate(user=admin)
        resp = api_client.put(
            f"{MAPEAMENTOS}sector/", {"tabela": "", "campos": {}}, format="json"
        )
        assert resp.status_code == 400
        assert "tabela" in resp.data["detail"].lower()

    def test_faltando_obrigatorio_diz_qual(self, api_client, admin, conexao):
        """
        A mensagem precisa nomear o campo que falta: "dados inválidos" faria
        o administrador procurar às cegas entre nove campos.
        """
        api_client.force_authenticate(user=admin)
        resp = api_client.put(
            f"{MAPEAMENTOS}sector/",
            {"tabela": "DEPTO", "campos": {"nome": "DESCRICAO"}},
            format="json",
        )
        assert resp.status_code == 400
        assert "Código do setor" in resp.data["detail"]

    def test_sem_conexao_explica_o_que_fazer(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        resp = api_client.put(
            f"{MAPEAMENTOS}sector/",
            {"tabela": "DEPTO", "campos": {"identificador": "A", "nome": "B"}},
            format="json",
        )
        assert resp.status_code == 400
        assert "Configure a conexão" in resp.data["detail"]

    def test_banco_inalcancavel_nao_grava_o_mapeamento(
        self, api_client, admin, conexao
    ):
        """
        Se não deu para conferir contra o banco, não grava: um mapeamento
        não verificado é pior do que nenhum, porque parece pronto.
        """
        conexao.host = "127.0.0.1"
        conexao.porta = 1
        conexao.timeout_segundos = 1
        conexao.save()

        api_client.force_authenticate(user=admin)
        resp = api_client.put(
            f"{MAPEAMENTOS}sector/",
            {"tabela": "DEPTO", "campos": {"identificador": "A", "nome": "B"}},
            format="json",
        )

        assert resp.status_code == 400
        assert not IntegrationMapping.objects.exists()


@pytest.mark.django_db
class TestLeitura:
    def test_lista_as_tres_entidades_mesmo_sem_configurar(
        self, api_client, admin, conexao
    ):
        """
        A tela precisa saber o que AINDA falta configurar — devolver só o
        que existe esconderia justamente os passos pendentes.
        """
        api_client.force_authenticate(user=admin)
        resp = api_client.get(MAPEAMENTOS)

        assert len(resp.data["mapeamentos"]) == 3
        assert all(not m["configurado"] for m in resp.data["mapeamentos"])

    def test_mostra_o_que_ja_foi_configurado(self, api_client, admin, conexao):
        IntegrationMapping.objects.create(
            connection=conexao, entidade=Entidade.SETOR,
            tabela="public.DEPTO",
            campos={"identificador": "CODDEPTO", "nome": "DESCRICAO"},
        )
        api_client.force_authenticate(user=admin)
        resp = api_client.get(MAPEAMENTOS)

        setor = next(
            m for m in resp.data["mapeamentos"] if m["entidade"] == Entidade.SETOR
        )
        assert setor["configurado"] is True
        assert setor["tabela"] == "public.DEPTO"
        assert setor["campos"]["nome"] == "DESCRICAO"


@pytest.mark.django_db
class TestModelo:
    def test_um_mapeamento_por_entidade(self, conexao):
        from django.db import IntegrityError

        IntegrationMapping.objects.create(
            connection=conexao, entidade=Entidade.SETOR, tabela="A", campos={}
        )
        with pytest.raises(IntegrityError):
            IntegrationMapping.objects.create(
                connection=conexao, entidade=Entidade.SETOR, tabela="B", campos={}
            )

    def test_colunas_usadas_ignora_campo_vazio(self, conexao):
        """
        É o que a tela mostra como "campos importados" — a seção 42 pede que
        o administrador consiga ver exatamente o que está sendo trazido.
        """
        m = IntegrationMapping.objects.create(
            connection=conexao, entidade=Entidade.FUNCIONARIO, tabela="F",
            campos={"identificador": "MAT", "nome": "NOME", "cpf": ""},
        )
        assert sorted(m.colunas_usadas) == ["MAT", "NOME"]

    def test_apagar_a_conexao_leva_os_mapeamentos(self, conexao):
        IntegrationMapping.objects.create(
            connection=conexao, entidade=Entidade.SETOR, tabela="A", campos={}
        )
        conexao.delete()
        assert not IntegrationMapping.objects.exists()


@pytest.mark.django_db
class TestChavesInventadas:
    def test_chave_fora_do_catalogo_e_descartada(self, api_client, admin, conexao):
        """
        `campos` é JSONField: o Django não tem schema para barrar uma chave
        inventada. Se ela passasse, viraria coluna lida na sincronização.
        """
        conexao.host = "127.0.0.1"
        conexao.porta = 1
        conexao.timeout_segundos = 1
        conexao.save()

        api_client.force_authenticate(user=admin)
        # Falha na conferência contra o banco, mas o importante é que a
        # chave inventada nem chega lá — some na peneira do catálogo.
        resp = api_client.put(
            f"{MAPEAMENTOS}sector/",
            {
                "tabela": "DEPTO",
                "campos": {
                    "identificador": "COD",
                    "nome": "DESC",
                    "campo_inventado": "QUALQUER",
                },
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "campo_inventado" not in str(resp.data)

    def test_o_catalogo_e_a_lista_fechada(self):
        chaves = chaves_de(Entidade.SETOR)
        assert "campo_inventado" not in chaves
        assert chaves == {"identificador", "nome", "ativo"}
