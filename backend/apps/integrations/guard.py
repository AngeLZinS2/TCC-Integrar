"""
A trava de leitura do banco externo.

A P4 chama isto de regra fundamental da arquitetura: a plataforma nunca
escreve no banco do cliente. Ela é garantida em CAMADAS, e esta aqui é a
quarta — a última rede, não a principal.

    1. Nenhuma API aceita SQL. A consulta nasce de `query.py`, que só sabe
       escrever SELECT: não existe caminho de código que emita outro verbo.
    2. Tabela e coluna são conferidas contra o schema descoberto — lista de
       permitidos, e não escape de aspas.
    3. A sessão abre em transação somente-leitura, onde o banco suporta.
    4. **Este módulo**: antes de executar, confere que é UMA instrução e que
       ela começa em SELECT.
    5. A credencial recomendada ao cliente tem apenas SELECT.

Por que a 4 não pode ser a principal: validar SQL por texto é uma corrida
contra comentários, codificação, unicode e sintaxe específica de cada
banco — quem valida precisa estar certo sempre, quem ataca precisa achar
uma brecha uma vez. A garantia forte está em 1 e 2, onde a escrita é
*inconstruível*. Esta camada existe para o caso de eu estar errado sobre
isso.
"""

import re


class ConsultaBloqueada(Exception):
    """A consulta não passou na trava. Nunca vira 500: a view converte."""


# Verbos que modificam dados, estrutura ou permissão. A lista da seção 8 da
# P4, mais os que aparecem em dialeto específico (MERGE no Oracle e no SQL
# Server, REPLACE e LOAD no MySQL, UPSERT no SQLite).
VERBOS_DE_ESCRITA = frozenset({
    "insert", "update", "delete", "drop", "alter", "truncate", "create",
    "rename", "grant", "revoke", "merge", "replace", "upsert", "call",
    "exec", "execute", "do", "load", "lock", "set", "begin", "commit",
    "rollback", "savepoint", "comment", "flashback", "purge", "analyze",
    "vacuum", "copy", "attach", "detach", "reindex", "cluster", "refresh",
    "prepare", "deallocate", "declare", "handler", "install", "uninstall",
    "reset", "shutdown", "kill",
})

# Só isto pode abrir uma instrução. `WITH` entra porque um CTE de leitura é
# SELECT legítimo — mas ele passa por uma checagem extra abaixo, já que
# Postgres aceita `WITH ... DELETE`.
VERBOS_DE_LEITURA = frozenset({"select", "with"})

_COMENTARIO_DE_LINHA = re.compile(r"--[^\n]*")
_COMENTARIO_DE_BLOCO = re.compile(r"/\*.*?\*/", re.DOTALL)
_ESPACOS = re.compile(r"\s+")


def _sem_literais(sql: str) -> str:
    """
    Troca o conteúdo das aspas por vazio.

    Um `;` ou a palavra `delete` DENTRO de um literal são texto, não
    comando — e recusar por causa deles rejeitaria consulta legítima. O que
    interessa é a estrutura em volta.
    """
    resultado = []
    i = 0
    tamanho = len(sql)
    while i < tamanho:
        c = sql[i]
        if c in ("'", '"', "`"):
            fecha = c
            i += 1
            while i < tamanho:
                # Aspa dobrada é escape do próprio delimitador.
                if sql[i] == fecha:
                    if i + 1 < tamanho and sql[i + 1] == fecha:
                        i += 2
                        continue
                    i += 1
                    break
                # Barra invertida escapa o próximo caractere no MySQL.
                if sql[i] == "\\" and i + 1 < tamanho:
                    i += 2
                    continue
                i += 1
            resultado.append(f"{fecha}{fecha}")
            continue
        resultado.append(c)
        i += 1
    return "".join(resultado)


def _normalizar(sql: str) -> str:
    """Tira comentários e literais, e achata os espaços."""
    limpo = _sem_literais(sql)
    limpo = _COMENTARIO_DE_BLOCO.sub(" ", limpo)
    limpo = _COMENTARIO_DE_LINHA.sub(" ", limpo)
    return _ESPACOS.sub(" ", limpo).strip()


def _palavras(sql_normalizado: str) -> list[str]:
    return re.findall(r"[A-Za-z_]+", sql_normalizado.lower())


def exigir_somente_leitura(sql: str) -> None:
    """
    Levanta `ConsultaBloqueada` se `sql` não for uma única leitura.

    Não devolve nada de propósito: quem chama não deve poder confundir um
    valor de retorno com "passou". Ou levanta, ou seguiu.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise ConsultaBloqueada("Consulta vazia.")

    normalizado = _normalizar(sql)
    if not normalizado:
        raise ConsultaBloqueada("Consulta vazia depois de remover comentários.")

    # ── Uma instrução só ────────────────────────────────────────────────
    # `;` no fim é aceito; no meio significa segunda instrução. É o caso do
    # "SELECT ...; DELETE FROM ..." que a seção 11 da P4 cita.
    corpo = normalizado.rstrip(";").strip()
    if ";" in corpo:
        raise ConsultaBloqueada(
            "Só é permitida uma instrução por consulta."
        )

    palavras = _palavras(corpo)
    if not palavras:
        raise ConsultaBloqueada("Consulta sem instrução reconhecível.")

    # ── Começa em SELECT ────────────────────────────────────────────────
    primeira = palavras[0]
    if primeira not in VERBOS_DE_LEITURA:
        raise ConsultaBloqueada(
            f"Operação '{primeira.upper()}' não é permitida: o banco externo "
            "é usado somente para leitura."
        )

    # ── Nenhum verbo de escrita em lugar nenhum ─────────────────────────
    # Cobre `WITH x AS (...) DELETE ...` do Postgres, subconsulta com
    # `INSERT` e qualquer construção que comece inocente e termine
    # escrevendo. Um falso positivo aqui custa uma consulta recusada; um
    # falso negativo custa o banco do cliente.
    for palavra in palavras:
        if palavra in VERBOS_DE_ESCRITA:
            raise ConsultaBloqueada(
                f"Operação '{palavra.upper()}' não é permitida: o banco "
                "externo é usado somente para leitura."
            )
