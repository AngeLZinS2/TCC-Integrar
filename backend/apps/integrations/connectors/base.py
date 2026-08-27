"""
A interface que todo banco externo precisa cumprir.

O Mapping Engine recebe listas de dicionários e **nunca sabe de que banco
vieram** — é o que a seção 6 da P4 exige. Todo dialeto (aspas, paginação,
consulta de catálogo) fica preso à implementação.

Repare no que a interface NÃO tem: nenhum método que receba SQL. Trazer
dados é `ler(tabela, colunas, ...)`, e a consulta é montada por
`query.montar_select`. Um método `executar(sql)` seria a porta de entrada
que a seção 10 proíbe — e uma vez que ele existisse, alguém acabaria
chamando com texto do usuário.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..guard import ConsultaBloqueada, exigir_somente_leitura
from ..query import (
    montar_select,
    normalizar_limite,
    normalizar_offset,
    validar_contra_schema,
)


class FalhaDeConexao(Exception):
    """
    Não deu para conectar ou consultar.

    A mensagem é escrita para o administrador ler — a seção 7 pede retorno
    amigável, e o texto cru do driver costuma trazer host e usuário, que
    não devem aparecer na tela.
    """


@dataclass(frozen=True)
class Coluna:
    nome: str
    tipo: str
    aceita_nulo: bool = True
    e_chave: bool = False


@dataclass(frozen=True)
class Tabela:
    nome: str
    schema: str = ""
    colunas: list[Coluna] = field(default_factory=list)

    @property
    def nome_completo(self) -> str:
        return f"{self.schema}.{self.nome}" if self.schema else self.nome


@dataclass(frozen=True)
class Credenciais:
    """
    O que o connector precisa para abrir a conexão.

    Objeto separado do model de propósito: o connector não importa Django,
    e a senha decifrada circula só aqui — nunca dentro de um registro que
    possa acabar serializado.
    """

    host: str
    porta: int
    banco: str
    usuario: str
    senha: str
    schema: str = ""
    usar_ssl: bool = False
    timeout_segundos: int = 10


class DataConnector(ABC):
    """
    Um banco externo, em modo de leitura.

    Usar sempre como gerenciador de contexto: a conexão precisa fechar
    mesmo quando a consulta falha, senão uma sincronização com erro deixa
    conexão pendurada no servidor do cliente.
    """

    # Rótulo do dialeto, usado no `select_type` da conexão.
    chave = ""
    porta_padrao = 0

    def __init__(self, credenciais: Credenciais):
        self.credenciais = credenciais
        self._conexao = None
        self._tabelas_conhecidas: dict[str, Tabela] | None = None

    # ── Ciclo de vida ──────────────────────────────────────────────────

    def __enter__(self):
        self.conectar()
        return self

    def __exit__(self, *_):
        self.fechar()
        return False

    @abstractmethod
    def conectar(self) -> None:
        """Abre a conexão JÁ em modo somente-leitura (camada 3)."""

    def fechar(self) -> None:
        if self._conexao is not None:
            try:
                self._conexao.close()
            except Exception:
                pass  # fechar não pode virar erro de negócio
            self._conexao = None

    # ── Descoberta ─────────────────────────────────────────────────────

    @abstractmethod
    def listar_tabelas(self) -> list[Tabela]:
        """Tabelas visíveis para o usuário configurado, sem colunas."""

    @abstractmethod
    def listar_colunas(self, tabela: str) -> list[Coluna]:
        """Colunas de uma tabela, com tipo e chave."""

    def schema_descoberto(self) -> dict[str, Tabela]:
        """
        {nome em minúscula: Tabela}, com cache na instância.

        É a lista de permitidos da camada 2: um nome que não está aqui não
        entra em consulta nenhuma.
        """
        if self._tabelas_conhecidas is None:
            self._tabelas_conhecidas = {
                t.nome_completo.lower(): t for t in self.listar_tabelas()
            }
        return self._tabelas_conhecidas

    # ── Leitura ────────────────────────────────────────────────────────

    def ler(
        self,
        tabela: str,
        colunas: list[str],
        *,
        limite: int | None = None,
        offset: int | None = None,
        ordenar_por: str | None = None,
    ) -> list[dict]:
        """
        A ÚNICA forma de trazer dados do banco externo.

        Não recebe SQL. Tabela e colunas são conferidas contra o schema
        descoberto antes de qualquer coisa ser montada.
        """
        conhecidas = self.schema_descoberto()
        tabela_real = validar_contra_schema(
            tabela, [t.nome_completo for t in conhecidas.values()], "tabela"
        )

        info = conhecidas[tabela_real.lower()]
        nomes_de_coluna = [c.nome for c in (info.colunas or self.listar_colunas(tabela_real))]
        colunas_reais = [
            validar_contra_schema(c, nomes_de_coluna, "coluna") for c in colunas
        ]
        ordem_real = (
            validar_contra_schema(ordenar_por, nomes_de_coluna, "coluna")
            if ordenar_por
            else None
        )

        sql = montar_select(
            tabela=tabela_real,
            colunas=colunas_reais,
            citar=self.citar,
            ordenar_por=ordem_real,
        )
        sql = self.aplicar_paginacao(
            sql, normalizar_limite(limite), normalizar_offset(offset)
        )
        return self._executar_leitura(sql, colunas_reais)

    def _executar_leitura(self, sql: str, colunas: list[str]) -> list[dict]:
        """
        Executa. A trava roda AQUI de novo, imediatamente antes do cursor.

        É o ponto mais tarde possível: qualquer caminho que chegue ao banco
        passa por esta linha, inclusive um que alguém acrescente depois sem
        lembrar das outras camadas.
        """
        exigir_somente_leitura(sql)

        if self._conexao is None:
            raise FalhaDeConexao("A conexão não está aberta.")

        try:
            cursor = self._conexao.cursor()
            try:
                cursor.execute(sql)
                linhas = cursor.fetchall()
            finally:
                cursor.close()
        except ConsultaBloqueada:
            raise
        except Exception as erro:
            raise FalhaDeConexao(self.traduzir_erro(erro))

        return [dict(zip(colunas, linha)) for linha in linhas]

    def executar_leitura_bruta(self, sql: str, limite: int = 200) -> tuple:
        """
        Executa uma consulta escrita à mão pelo administrador.

        **Esta é a única porta do sistema que aceita SQL de fora**, e existe
        por decisão explícita de produto: alguns ERPs exigem JOIN ou filtro
        que o mapeamento estruturado não expressa.

        O que se PERDE em relação a `ler()`:

          - camada 1 (a escrita ser inconstruível): aqui há texto do usuário
          - camada 2 (lista de permitidos): não há identificador a conferir

        O que CONTINUA valendo, e passa a ser a defesa principal:

          - camada 3: a sessão está em transação somente-leitura
          - camada 4: `exigir_somente_leitura` — uma instrução, começando em
            SELECT, sem verbo de escrita em lugar nenhum
          - camada 5: a credencial recomendada só tem SELECT

        E um limite que `ler()` não precisava: as linhas são puxadas com
        `fetchmany`, e não `fetchall`. Uma consulta sem `WHERE` numa tabela
        de milhões traria tudo para a memória do servidor — e aqui o texto
        da consulta não é nosso para acrescentar `LIMIT`, porque cada banco
        escreve isso de um jeito e o SQL pode já ter o seu.
        """
        exigir_somente_leitura(sql)

        if self._conexao is None:
            raise FalhaDeConexao("A conexão não está aberta.")

        try:
            cursor = self._conexao.cursor()
            try:
                cursor.execute(sql)
                if cursor.description is None:
                    # Sem colunas de retorno: não era uma leitura de dados.
                    raise FalhaDeConexao(
                        "A consulta não devolveu nenhuma coluna. "
                        "Use um SELECT que retorne dados."
                    )
                colunas = [d[0] for d in cursor.description]
                linhas = cursor.fetchmany(limite)
            finally:
                cursor.close()
        except (ConsultaBloqueada, FalhaDeConexao):
            raise
        except Exception as erro:
            raise FalhaDeConexao(self.traduzir_erro(erro))

        return colunas, [dict(zip(colunas, linha)) for linha in linhas]

    # ── Dialeto ────────────────────────────────────────────────────────

    @abstractmethod
    def citar(self, identificador: str) -> str:
        """Envolve o identificador nas aspas do dialeto."""

    @abstractmethod
    def aplicar_paginacao(self, sql: str, limite: int, offset: int) -> str:
        """Acrescenta o recorte de linhas na sintaxe do banco."""

    def testar(self) -> None:
        """
        Abre, faz uma leitura mínima e fecha.

        Levanta `FalhaDeConexao` com mensagem legível quando não dá.
        """
        with self:
            self.listar_tabelas()

    @staticmethod
    def traduzir_erro(erro: Exception) -> str:
        """
        Transforma o erro do driver em algo que o administrador entenda.

        O texto cru costuma trazer host, porta e usuário; jogá-lo na tela
        vazaria detalhe de infraestrutura para quem estiver olhando junto.
        """
        texto = str(erro).lower()
        if "timeout" in texto or "timed out" in texto:
            return "O banco não respondeu a tempo. Confira host, porta e firewall."
        if "authentication" in texto or "password" in texto or "access denied" in texto:
            return "Usuário ou senha recusados pelo banco."
        if "does not exist" in texto or "unknown database" in texto:
            return "O banco informado não foi encontrado."
        if "could not connect" in texto or "connection refused" in texto:
            return "Não foi possível alcançar o servidor. Confira host e porta."
        if "permission denied" in texto or "insufficient privileges" in texto:
            return (
                "O usuário conectou, mas não tem permissão de leitura nas "
                "tabelas. Conceda SELECT ao usuário de integração."
            )
        return "Não foi possível concluir a operação no banco externo."
