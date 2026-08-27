"""
A trava de leitura do banco externo (P4, seções 8 a 13 e 37).

A regra que este arquivo defende: **a plataforma nunca escreve no banco do
cliente**. Não é uma preferência de arquitetura — é a promessa que permite
uma empresa apontar o ERP de produção para cá.

Os testes cobrem os onze verbos que a seção 37 lista, mais o que ela não
lista e que é como um ataque real chegaria: instrução múltipla, comentário
no meio do comando, verbo escondido em CTE, e injeção pelos nomes de
tabela e coluna — que são a única entrada de texto do administrador.
"""

import pytest

from apps.integrations.guard import ConsultaBloqueada, exigir_somente_leitura
from apps.integrations.query import (
    IdentificadorInvalido,
    montar_select,
    normalizar_limite,
    normalizar_offset,
    validar_contra_schema,
    validar_identificador,
)


def citar(nome: str) -> str:
    """Citação estilo PostgreSQL, para os testes."""
    return '"' + str(nome).replace('"', '""') + '"'


# ══════════════════════════════════════════════════════════════════════════
# Os verbos da seção 37
# ══════════════════════════════════════════════════════════════════════════

class TestVerbos:
    def test_select_passa(self):
        exigir_somente_leitura("SELECT id, nome FROM funcionarios")

    def test_select_com_juncao_e_filtro_passa(self):
        exigir_somente_leitura(
            "SELECT f.nome, d.descricao FROM funcionarios f "
            "JOIN departamentos d ON f.dep_id = d.id WHERE f.ativo = 1"
        )

    def test_cte_de_leitura_passa(self):
        exigir_somente_leitura(
            "WITH ativos AS (SELECT * FROM funcionarios WHERE ativo = 1) "
            "SELECT * FROM ativos"
        )

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
            "RENAME TABLE funcionarios TO antigos",
            "GRANT ALL ON funcionarios TO publico",
            "REVOKE SELECT ON funcionarios FROM leitor",
        ],
    )
    def test_os_verbos_de_escrita_sao_bloqueados(self, sql):
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura(sql)

    @pytest.mark.parametrize(
        "sql",
        [
            "MERGE INTO funcionarios USING origem ON (1=1)",
            "REPLACE INTO funcionarios VALUES (1)",
            "CALL procedimento_perigoso()",
            "EXEC sp_qualquer",
            "LOAD DATA INFILE '/etc/passwd' INTO TABLE x",
            "COPY funcionarios FROM '/tmp/x.csv'",
        ],
    )
    def test_verbos_de_dialeto_especifico_tambem_sao_bloqueados(self, sql):
        """
        A lista da P4 não cobre MERGE, CALL nem LOAD — mas eles escrevem, e
        cada um é o verbo natural de um dos bancos suportados.
        """
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura(sql)

    def test_minuscula_e_bloqueado_igual(self):
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura("delete from funcionarios")

    def test_espacos_e_quebras_nao_disfarcam(self):
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura("\n\t  DROP\n\tTABLE funcionarios  ")


# ══════════════════════════════════════════════════════════════════════════
# Como um ataque real chegaria
# ══════════════════════════════════════════════════════════════════════════

class TestInstrucaoMultipla:
    def test_duas_instrucoes_sao_recusadas(self):
        """O exemplo literal da seção 11 da P4."""
        with pytest.raises(ConsultaBloqueada) as erro:
            exigir_somente_leitura(
                "SELECT * FROM funcionarios; DELETE FROM funcionarios;"
            )
        assert "uma instrução" in str(erro.value)

    def test_ponto_e_virgula_final_sozinho_e_aceito(self):
        # Recusar isto rejeitaria consulta legítima sem ganhar segurança.
        exigir_somente_leitura("SELECT * FROM funcionarios;")

    def test_segunda_instrucao_disfarcada_de_leitura(self):
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura(
                "SELECT 1; SELECT * FROM funcionarios"
            )


class TestComentarios:
    def test_comentario_nao_esconde_o_verbo(self):
        """
        `SELECT/**/1;DROP...` é o formato clássico de contornar um
        validador ingênuo que só olha o começo da string.
        """
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura("SELECT 1 /* nada */ ; DROP TABLE x")

    def test_comando_inteiro_comentado_nao_vira_leitura(self):
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura("-- SELECT 1\nDELETE FROM funcionarios")

    def test_comentario_de_bloco_antes_do_verbo(self):
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura("/* SELECT */ UPDATE f SET a = 1")

    def test_so_comentario_e_recusado(self):
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura("-- nada aqui")


class TestLiterais:
    def test_palavra_perigosa_dentro_de_texto_nao_bloqueia(self):
        """
        Um funcionário chamado "Delete" ou um cargo "DROP" não podem
        inviabilizar a consulta. O que vale é a estrutura, não o conteúdo.
        """
        exigir_somente_leitura(
            "SELECT * FROM funcionarios WHERE nome = 'Delete From Silva'"
        )

    def test_ponto_e_virgula_dentro_de_texto_nao_conta_como_instrucao(self):
        exigir_somente_leitura(
            "SELECT * FROM funcionarios WHERE obs = 'a; b'"
        )

    def test_aspa_escapada_nao_confunde_o_fechamento(self):
        exigir_somente_leitura(
            "SELECT * FROM funcionarios WHERE nome = 'O''Brien'"
        )

    def test_texto_aberto_com_verbo_depois_ainda_bloqueia(self):
        # Se o literal não fecha, tudo depois vira texto — e mesmo assim o
        # começo precisa ser leitura.
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura("DELETE FROM f WHERE nome = 'x")


class TestCTE:
    def test_with_seguido_de_delete_e_bloqueado(self):
        """
        PostgreSQL aceita `WITH ... DELETE`. Aceitar todo `WITH` porque ele
        "costuma ser leitura" abriria exatamente esse caminho.
        """
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura(
                "WITH alvo AS (SELECT id FROM funcionarios) "
                "DELETE FROM funcionarios WHERE id IN (SELECT id FROM alvo)"
            )

    def test_insert_dentro_de_subconsulta_e_bloqueado(self):
        with pytest.raises(ConsultaBloqueada):
            exigir_somente_leitura(
                "SELECT * FROM (INSERT INTO log VALUES (1) RETURNING *) x"
            )


# ══════════════════════════════════════════════════════════════════════════
# Injeção pelos nomes — a única entrada de texto do administrador
# ══════════════════════════════════════════════════════════════════════════

class TestIdentificadores:
    @pytest.mark.parametrize(
        "nome",
        [
            "funcionarios; DROP TABLE x",
            'funcionarios" ; DROP TABLE x --',
            "funcionarios--",
            "funcionarios/*",
            "func ionarios",
            "func(ionarios)",
            "'; DELETE FROM funcionarios; --",
            "",
            "1tabela",
            "tabela!",
        ],
    )
    def test_nome_malformado_e_recusado(self, nome):
        with pytest.raises(IdentificadorInvalido):
            validar_identificador(nome, "tabela")

    def test_nome_bem_formado_passa(self):
        for nome in ["FUNCIONARIOS", "pc_empr", "Tabela$1", "COL#1", "_x"]:
            assert validar_identificador(nome) == nome

    def test_nome_valido_mas_ausente_do_schema_e_recusado(self):
        """
        A peneira que importa: o nome pode ser perfeitamente formado e
        ainda assim não ser uma tabela do banco conectado.
        """
        with pytest.raises(IdentificadorInvalido) as erro:
            validar_contra_schema(
                "usuarios_secretos", ["FUNCIONARIOS", "CARGOS"], "tabela"
            )
        assert "não existe" in str(erro.value)

    def test_nome_qualificado_e_aceito(self):
        """
        `public.funcionarios` é o formato que a descoberta devolve no
        PostgreSQL. Rejeitá-lo quebrava a rota de colunas inteira — o
        regex validava a string toda e o ponto nunca passava.
        """
        assert validar_identificador("public.funcionarios", "tabela") == (
            "public.funcionarios"
        )

    @pytest.mark.parametrize(
        "nome",
        [
            "banco.schema.tabela",   # atravessar para outro banco
            ".funcionarios",         # parte vazia
            "public.",               # parte vazia
            "public..funcionarios",  # parte vazia no meio
            "public.func;drop",      # injeção numa das partes
        ],
    )
    def test_nome_com_ponto_malformado_e_recusado(self, nome):
        with pytest.raises(IdentificadorInvalido):
            validar_identificador(nome, "tabela")

    def test_nome_curto_encontra_a_tabela_qualificada(self):
        """
        Quem escolhe da tela vê "FUNCIONARIOS", não "public.FUNCIONARIOS".
        Exigir o qualificado transformaria a escolha num quebra-cabeça.
        """
        real = validar_contra_schema(
            "funcionarios", ["public.funcionarios", "public.cargos"], "tabela"
        )
        assert real == "public.funcionarios"

    def test_nome_curto_ambiguo_pede_o_completo(self):
        """
        Duas tabelas com o mesmo nome em schemas diferentes: escolher uma
        em silêncio leria os dados errados sem ninguém perceber.
        """
        with pytest.raises(IdentificadorInvalido) as erro:
            validar_contra_schema(
                "funcionarios",
                ["rh.funcionarios", "folha.funcionarios"],
                "tabela",
            )
        assert "mais de um schema" in str(erro.value)

    def test_nome_qualificado_exato_vence_a_busca_pelo_curto(self):
        real = validar_contra_schema(
            "folha.funcionarios",
            ["rh.funcionarios", "folha.funcionarios"],
            "tabela",
        )
        assert real == "folha.funcionarios"

    def test_schema_devolve_a_grafia_do_banco(self):
        """
        Oracle reporta em caixa alta. Usar a grafia digitada pelo usuário
        quebraria a consulta num banco sensível a caixa.
        """
        real = validar_contra_schema("funcionarios", ["FUNCIONARIOS"], "tabela")
        assert real == "FUNCIONARIOS"


class TestMontagemDaConsulta:
    def test_monta_select_simples(self):
        sql = montar_select(
            tabela="funcionarios",
            colunas=["id", "nome"],
            citar=citar,
        )
        assert sql == 'SELECT "id", "nome" FROM "funcionarios"'

    def test_cita_schema_e_tabela_separadamente(self):
        sql = montar_select(
            tabela="rh.funcionarios", colunas=["id"], citar=citar
        )
        assert sql == 'SELECT "id" FROM "rh"."funcionarios"'

    def test_sem_coluna_e_recusado(self):
        with pytest.raises(ConsultaBloqueada):
            montar_select(tabela="funcionarios", colunas=[], citar=citar)

    def test_a_propria_montagem_passa_pela_trava(self):
        """
        A consulta montada aqui é reconferida antes de sair. É redundante
        de propósito: se alguém acrescentar uma concatenação neste caminho,
        a trava reclama junto.
        """
        sql = montar_select(
            tabela="funcionarios", colunas=["id"], citar=citar
        )
        exigir_somente_leitura(sql)  # não levanta


class TestPaginacao:
    def test_limite_tem_teto(self):
        # Sem teto, um mapeamento apontado para a tabela errada traria a
        # base inteira para a memória do worker.
        assert normalizar_limite(999_999) == 5000

    def test_limite_padrao(self):
        assert normalizar_limite(None) == 1000

    @pytest.mark.parametrize("valor", [0, -1, "muitos", 1.5e400])
    def test_limite_invalido_e_recusado(self, valor):
        with pytest.raises(ConsultaBloqueada):
            normalizar_limite(valor)

    def test_offset_negativo_e_recusado(self):
        with pytest.raises(ConsultaBloqueada):
            normalizar_offset(-1)

    def test_offset_padrao(self):
        assert normalizar_offset(None) == 0
