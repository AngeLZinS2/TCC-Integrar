"""PostgreSQL."""

from .base import Coluna, DataConnector, FalhaDeConexao, Tabela


class PostgresConnector(DataConnector):
    chave = "postgresql"
    porta_padrao = 5432

    def conectar(self) -> None:
        import psycopg2

        c = self.credenciais
        try:
            self._conexao = psycopg2.connect(
                host=c.host,
                port=c.porta or self.porta_padrao,
                dbname=c.banco,
                user=c.usuario,
                password=c.senha,
                connect_timeout=c.timeout_segundos,
                sslmode="require" if c.usar_ssl else "prefer",
                # Camada 3: a sessão inteira nasce somente-leitura. Uma
                # escrita que escapasse das camadas de cima morreria aqui,
                # no servidor do próprio cliente.
                options="-c default_transaction_read_only=on",
            )
            self._conexao.set_session(readonly=True, autocommit=True)
        except Exception as erro:
            raise FalhaDeConexao(self.traduzir_erro(erro))

    def citar(self, identificador: str) -> str:
        return '"' + str(identificador).replace('"', '""') + '"'

    def aplicar_paginacao(self, sql: str, limite: int, offset: int) -> str:
        return f"{sql} LIMIT {int(limite)} OFFSET {int(offset)}"

    def listar_tabelas(self) -> list[Tabela]:
        # Consulta de catálogo: SQL fixo, sem nada vindo do usuário. O
        # schema, quando informado, entra por parâmetro do driver.
        schema = self.credenciais.schema or "public"
        sql = (
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type IN ('BASE TABLE', 'VIEW') "
            "ORDER BY table_name"
        )
        return [
            Tabela(nome=nome, schema=esquema)
            for esquema, nome in self._catalogo(sql, (schema,))
        ]

    def listar_colunas(self, tabela: str) -> list[Coluna]:
        schema, _, nome = str(tabela).rpartition(".")
        schema = schema or self.credenciais.schema or "public"
        sql = (
            "SELECT c.column_name, c.data_type, c.is_nullable, "
            "  CASE WHEN k.column_name IS NULL THEN false ELSE true END "
            "FROM information_schema.columns c "
            "LEFT JOIN information_schema.key_column_usage k "
            "  ON k.table_schema = c.table_schema "
            " AND k.table_name = c.table_name "
            " AND k.column_name = c.column_name "
            "WHERE c.table_schema = %s AND c.table_name = %s "
            "ORDER BY c.ordinal_position"
        )
        return [
            Coluna(nome=n, tipo=t, aceita_nulo=(nulo == "YES"), e_chave=bool(chave))
            for n, t, nulo, chave in self._catalogo(sql, (schema, nome))
        ]

    def _catalogo(self, sql: str, parametros: tuple):
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
