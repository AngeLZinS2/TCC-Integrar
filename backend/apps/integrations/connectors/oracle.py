"""
Oracle, em modo *thin*.

O driver `oracledb` conversa direto pelo protocolo, sem Instant Client:
não exige biblioteca de sistema no contêiner, o que é o que torna o
suporte a Oracle viável aqui.
"""

from .base import Coluna, DataConnector, FalhaDeConexao, Tabela


class OracleConnector(DataConnector):
    chave = "oracle"
    porta_padrao = 1521

    def conectar(self) -> None:
        import oracledb

        c = self.credenciais
        try:
            # O campo "banco" recebe o service name — é como o Oracle
            # identifica a base, e o rótulo da tela diz isso.
            self._conexao = oracledb.connect(
                user=c.usuario,
                password=c.senha,
                dsn=f"{c.host}:{c.porta or self.porta_padrao}/{c.banco}",
                tcp_connect_timeout=c.timeout_segundos,
            )
            # Camada 3: transação somente-leitura na própria sessão.
            cursor = self._conexao.cursor()
            try:
                cursor.execute("SET TRANSACTION READ ONLY")
            finally:
                cursor.close()
        except Exception as erro:
            raise FalhaDeConexao(self.traduzir_erro(erro))

    def citar(self, identificador: str) -> str:
        return '"' + str(identificador).replace('"', '""') + '"'

    def aplicar_paginacao(self, sql: str, limite: int, offset: int) -> str:
        # Oracle 12c+. O `ORDER BY` já vem do montador quando existe.
        return f"{sql} OFFSET {int(offset)} ROWS FETCH NEXT {int(limite)} ROWS ONLY"

    def listar_tabelas(self) -> list[Tabela]:
        dono = (self.credenciais.schema or self.credenciais.usuario).upper()
        sql = (
            "SELECT owner, table_name FROM all_tables WHERE owner = :dono "
            "UNION ALL "
            "SELECT owner, view_name FROM all_views WHERE owner = :dono "
            "ORDER BY 2"
        )
        return [
            Tabela(nome=nome, schema="")
            for _, nome in self._catalogo(sql, {"dono": dono})
        ]

    def listar_colunas(self, tabela: str) -> list[Coluna]:
        dono = (self.credenciais.schema or self.credenciais.usuario).upper()
        nome_tabela = str(tabela).rpartition(".")[2].upper()
        sql = (
            "SELECT c.column_name, c.data_type, c.nullable, "
            "  CASE WHEN cc.column_name IS NULL THEN 0 ELSE 1 END "
            "FROM all_tab_columns c "
            "LEFT JOIN all_constraints ct "
            "  ON ct.owner = c.owner AND ct.table_name = c.table_name "
            " AND ct.constraint_type = 'P' "
            "LEFT JOIN all_cons_columns cc "
            "  ON cc.constraint_name = ct.constraint_name "
            " AND cc.column_name = c.column_name "
            "WHERE c.owner = :dono AND c.table_name = :tabela "
            "ORDER BY c.column_id"
        )
        return [
            Coluna(nome=n, tipo=t, aceita_nulo=(nulo == "Y"), e_chave=bool(chave))
            for n, t, nulo, chave in self._catalogo(
                sql, {"dono": dono, "tabela": nome_tabela}
            )
        ]

    def _catalogo(self, sql: str, parametros: dict):
        if self._conexao is None:
            raise FalhaDeConexao("A conexão não está aberta.")
        try:
            cursor = self._conexao.cursor()
            try:
                cursor.execute(sql, parametros)
                return cursor.fetchall()
            finally:
                cursor.close()
        except Exception as erro:
            raise FalhaDeConexao(self.traduzir_erro(erro))
