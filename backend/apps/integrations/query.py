"""
Construção das consultas de leitura.

Esta é a camada 1 da trava: **não existe função aqui capaz de escrever
outra coisa que não `SELECT`**. Nenhuma API do sistema recebe SQL, e o
administrador escolhe tabela e coluna de listas — a P4 proíbe campo livre
de SQL (seção 10), e um campo desses seria justamente a porta de entrada.

E a camada 2: todo identificador é conferido contra o schema descoberto
antes de entrar na consulta. É lista de permitidos, não escape de aspas —
a diferença importa, porque escape depende de acertar o dialeto e a
codificação, e a lista depende só de o nome ter vindo do próprio banco.
"""

import re

from .guard import ConsultaBloqueada, exigir_somente_leitura

# Um identificador aceitável: letra ou sublinhado, depois letras, dígitos,
# sublinhado, cifrão ou `#` (Oracle usa os dois últimos). Ponto é aceito
# para `schema.tabela`, e cada parte é validada em separado.
_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#]*$")

LIMITE_MAXIMO = 5000


class IdentificadorInvalido(ConsultaBloqueada):
    """Nome de tabela ou coluna que não veio do schema descoberto."""


def validar_identificador(nome: str, rotulo: str = "identificador") -> str:
    """
    Confere a FORMA do nome.

    Primeira peneira, e não a última: mesmo um nome bem formado ainda
    precisa constar do schema (ver `validar_contra_schema`). Aqui só se
    barra o que nem parece um identificador — parêntese, espaço, aspas,
    ponto-e-vírgula.
    """
    if not isinstance(nome, str) or not nome:
        raise IdentificadorInvalido(f"{rotulo.capitalize()} vazio.")
    if len(nome) > 128:
        raise IdentificadorInvalido(f"{rotulo.capitalize()} longo demais.")
    if not _IDENTIFICADOR.match(nome):
        raise IdentificadorInvalido(
            f"{rotulo.capitalize()} inválido: {nome!r}."
        )
    return nome


def validar_contra_schema(
    nome: str,
    permitidos,
    rotulo: str = "identificador",
) -> str:
    """
    Confere que o nome EXISTE no schema descoberto.

    Comparação sem diferenciar maiúsculas porque Oracle devolve tudo em
    caixa alta e MySQL varia conforme o sistema de arquivos. Devolve o nome
    exatamente como o banco o reportou — usar a grafia do usuário quebraria
    em banco sensível a caixa.
    """
    validar_identificador(nome, rotulo)

    por_minuscula = {str(p).lower(): str(p) for p in permitidos}
    real = por_minuscula.get(nome.lower())
    if real is None:
        raise IdentificadorInvalido(
            f"{rotulo.capitalize()} {nome!r} não existe no banco conectado."
        )
    return real


def montar_select(
    *,
    tabela: str,
    colunas: list[str],
    citar,
    limite: int | None = None,
    offset: int | None = None,
    ordenar_por: str | None = None,
) -> str:
    """
    Monta um SELECT. É a única forma de trazer dados do banco externo.

    `citar` é a função de aspas do banco (cada dialeto tem a sua), passada
    pelo connector. Os identificadores já chegam validados; a citação é a
    proteção final contra palavra reservada usada como nome de coluna.

    Paginação vira `LIMIT/OFFSET` ou `OFFSET/FETCH` conforme o banco, e por
    isso é o connector que a acrescenta — aqui fica o núcleo comum.
    """
    if not colunas:
        raise ConsultaBloqueada("Selecione ao menos uma coluna.")

    campos = ", ".join(citar(c) for c in colunas)
    sql = f"SELECT {campos} FROM {citar_tabela(tabela, citar)}"

    if ordenar_por:
        sql += f" ORDER BY {citar(ordenar_por)}"

    # A consulta que este módulo acabou de montar passa pela trava antes de
    # sair. Parece redundante — e é de propósito: se algum dia alguém
    # acrescentar uma concatenação aqui, o teste da trava quebra junto.
    exigir_somente_leitura(sql)
    return sql


def citar_tabela(tabela: str, citar) -> str:
    """Cita `schema.tabela` parte por parte, preservando o ponto."""
    partes = str(tabela).split(".")
    return ".".join(citar(p) for p in partes)


def normalizar_limite(limite: int | None) -> int:
    """
    Teto no número de linhas por página.

    Sem teto, um mapeamento apontado para a tabela errada traria a base
    inteira para a memória do worker.
    """
    if limite is None:
        return 1000
    try:
        valor = int(limite)
    except (TypeError, ValueError, OverflowError):
        # OverflowError cobre infinito: `int(float("inf"))` nao levanta
        # ValueError, e sem isto um limite absurdo virava 500.
        raise ConsultaBloqueada("Limite inválido.")
    if valor < 1:
        raise ConsultaBloqueada("Limite precisa ser maior que zero.")
    return min(valor, LIMITE_MAXIMO)


def normalizar_offset(offset: int | None) -> int:
    if offset is None:
        return 0
    try:
        valor = int(offset)
    except (TypeError, ValueError, OverflowError):
        raise ConsultaBloqueada("Deslocamento inválido.")
    if valor < 0:
        raise ConsultaBloqueada("Deslocamento não pode ser negativo.")
    return valor
