"""MySQL e MariaDB — mesmo protocolo, mesmo driver."""

from .base import Coluna, DataConnector, FalhaDeConexao, Tabela


class MySQLConnector(DataConnector):
    chave = "mysql"
    porta_padrao = 3306

    def conectar(self) -> None:
        import pymysql

        c = self.credenciais
        try:
            self._conexao = pymysql.connect(
                host=c.host,
                port=c.porta or self.porta_padrao,
                database=c.banco,
                user=c.usuario,
                password=c.senha,
                connect_timeout=c.timeout_segundos,
                read_timeout=c.timeout_segundos * 3,
                ssl={"ssl": {}} if c.usar_ssl else None,
                autocommit=True,
            )
            # Camada 3: a sessão passa a recusar escrita no próprio servidor.
            cursor = self._conexao.cursor()
            try:
                cursor.execute("SET SESSION TRANSACTION READ ONLY")
            finally:
                cursor.close()
        except Exception as erro:
            raise FalhaDeConexao(self.traduzir_erro(erro))

    def citar(self, identificador: str) -> str:
        # MySQL usa crase, e a escapa dobrando.
        return "`" + str(identificador).replace("`", "``") + "`"

    def aplicar_paginacao(self, sql: str, limite: int, offset: int) -> str:
        return f"{sql} LIMIT {int(limite)} OFFSET {int(offset)}"

    def listar_tabelas(self) -> list[Tabela]:
        schema = self.credenciais.schema or self.credenciais.banco
        sql = (
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema = %s ORDER BY table_name"
        )
        return [
            Tabela(nome=nome, schema="")
            for _, nome in self._catalogo(sql, (schema,))
        ]

    def listar_colunas(self, tabela: str) -> list[Coluna]:
        schema = self.credenciais.schema or self.credenciais.banco
        nome_tabela = str(tabela).rpartition(".")[2]
        sql = (
            "SELECT column_name, data_type, is_nullable, column_key "
            "FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s "
            "ORDER BY ordinal_position"
        )
        return [
            Coluna(
                nome=n, tipo=t, aceita_nulo=(nulo == "YES"), e_chave=(chave == "PRI")
            )
            for n, t, nulo, chave in self._catalogo(sql, (schema, nome_tabela))
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


class MariaDBConnector(MySQLConnector):
    """
    MariaDB fala o protocolo do MySQL.

    Existe como classe própria para o administrador reconhecer o banco dele
    na lista — "MySQL" numa empresa que usa MariaDB gera dúvida legítima
    sobre se vai funcionar.
    """

    chave = "mariadb"
