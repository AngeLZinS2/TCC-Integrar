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

    Aceita `schema.tabela`, validando CADA PARTE em separado — o ponto é o
    único caractere que atravessa as partes, e nada além dele. Validar a
    string inteira contra um regex sem ponto rejeitava todo nome
    qualificado, que é exatamente o formato que a descoberta devolve no
    PostgreSQL.

    Primeira peneira, e não a última: mesmo um nome bem formado ainda
    precisa constar do schema (ver `validar_contra_schema`).
    """
    if not isinstance(nome, str) or not nome:
        raise IdentificadorInvalido(f"{rotulo.capitalize()} vazio.")
    if len(nome) > 260:
        raise IdentificadorInvalido(f"{rotulo.capitalize()} longo demais.")

    partes = nome.split(".")
    if len(partes) > 2:
        # `a.b.c` não é schema.tabela: ou é engano, ou é tentativa de
        # atravessar para outro banco.
        raise IdentificadorInvalido(
            f"{rotulo.capitalize()} inválido: {nome!r}."
        )

    for parte in partes:
        if not parte or len(parte) > 128 or not _IDENTIFICADOR.match(parte):
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

    permitidos = [str(p) for p in permitidos]
    por_minuscula = {p.lower(): p for p in permitidos}

    # Nome exato (qualificado ou não), do jeito que o banco reportou.
    real = por_minuscula.get(nome.lower())
    if real is not None:
        return real

    # Nome curto quando a lista guarda `schema.tabela`: quem escolhe da
    # tela vê "FUNCIONARIOS", não "public.FUNCIONARIOS", e exigir o
    # qualificado transformaria a escolha num quebra-cabeça.
    if "." not in nome:
        curto = nome.lower()
        candidatos = [
            p for p in permitidos if p.lower().rsplit(".", 1)[-1] == curto
        ]
        if len(candidatos) == 1:
            return candidatos[0]
        if len(candidatos) > 1:
            # Dois schemas com a mesma tabela: escolher um em silêncio
            # leria os dados errados sem ninguém perceber.
            raise IdentificadorInvalido(
                f"{rotulo.capitalize()} {nome!r} existe em mais de um schema. "
                f"Informe o nome completo, por exemplo {candidatos[0]!r}."
            )

    raise IdentificadorInvalido(
        f"{rotulo.capitalize()} {nome!r} não existe no banco conectado."
    )


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
