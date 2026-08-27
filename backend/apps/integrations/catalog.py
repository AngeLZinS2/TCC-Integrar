"""
O que a plataforma precisa saber sobre cada entidade.

Este catálogo é o vocabulário do lado de CÁ: os campos que o sistema usa.
O que está do lado de lá — nome de tabela, nome de coluna — vem do banco
do cliente, e é o administrador quem liga um ao outro.

A separação entre obrigatório e opcional é exigência da seção 15 da P4, e
tem consequência prática: sem o identificador não dá para reconhecer a
mesma pessoa entre duas sincronizações, e sem o nome não dá para criar
ninguém. O resto é enriquecimento.

Princípio de minimização (seção 42): CPF e telefone só são sincronizados
se o administrador apontar a coluna. Nada é trazido por padrão.
"""


class Entidade:
    FUNCIONARIO = "employee"
    SETOR = "sector"
    CARGO = "position"

    ROTULOS = {
        FUNCIONARIO: "Funcionários",
        SETOR: "Setores",
        CARGO: "Cargos",
    }

    TODAS = [FUNCIONARIO, SETOR, CARGO]
    # Escrito à mão em vez de derivado de `ROTULOS`: dentro do corpo de uma
    # classe, a compreensão de lista não enxerga os atributos irmãos.
    CHOICES = [
        (FUNCIONARIO, "Funcionários"),
        (SETOR, "Setores"),
        (CARGO, "Cargos"),
    ]


def _campo(chave, rotulo, ajuda, obrigatorio=False):
    return {
        "chave": chave,
        "rotulo": rotulo,
        "ajuda": ajuda,
        "obrigatorio": obrigatorio,
    }


# Os rótulos falam a língua de quem configura, não a do banco: a seção 44
# da P4 pede "Campo que identifica o setor", e não "FK source".
CAMPOS = {
    Entidade.FUNCIONARIO: [
        _campo(
            "identificador", "Matrícula ou código do funcionário",
            "O número que não muda quando a pessoa troca de cargo ou de nome. "
            "É por ele que o sistema reconhece o mesmo funcionário em cada "
            "sincronização.",
            obrigatorio=True,
        ),
        _campo("nome", "Nome completo", "Como o nome aparece no sistema.", obrigatorio=True),
        _campo(
            "email", "E-mail corporativo",
            "Usado para o primeiro acesso. Sem ele, o funcionário entra no "
            "sistema mas não recebe aviso por e-mail.",
        ),
        _campo(
            "ativo", "Situação (ativo ou desligado)",
            "A coluna que diz se a pessoa ainda trabalha na empresa. Quem "
            "aparece como desligado é desativado aqui, nunca apagado.",
        ),
        _campo(
            "setor", "Campo que identifica o setor",
            "A coluna que guarda o código do setor na tabela de funcionários.",
        ),
        _campo(
            "cargo", "Campo que identifica o cargo",
            "A coluna que guarda o código do cargo na tabela de funcionários.",
        ),
        _campo("data_admissao", "Data de admissão", "Usada para calcular os prazos da integração."),
        _campo("telefone", "Telefone", "Opcional. Só traga se for usar."),
        _campo(
            "cpf", "CPF",
            "Opcional. Dado sensível: só traga se o processo realmente "
            "precisar dele.",
        ),
    ],
    Entidade.SETOR: [
        _campo(
            "identificador", "Código do setor",
            "O código que a tabela de funcionários usa para apontar o setor.",
            obrigatorio=True,
        ),
        _campo("nome", "Nome do setor", "Como o setor aparece no sistema.", obrigatorio=True),
        _campo("ativo", "Situação", "A coluna que diz se o setor ainda existe."),
    ],
    Entidade.CARGO: [
        _campo(
            "identificador", "Código do cargo",
            "O código que a tabela de funcionários usa para apontar o cargo.",
            obrigatorio=True,
        ),
        _campo("nome", "Nome do cargo", "Como o cargo aparece no sistema.", obrigatorio=True),
        _campo("ativo", "Situação", "A coluna que diz se o cargo ainda existe."),
        _campo(
            "setor", "Campo que identifica o setor",
            "Quando o cargo pertence a um setor. Deixe em branco se na sua "
            "empresa o cargo não tem setor.",
        ),
    ],
}


def campos_de(entidade: str) -> list[dict]:
    return CAMPOS.get(entidade, [])


def obrigatorios_de(entidade: str) -> list[str]:
    return [c["chave"] for c in campos_de(entidade) if c["obrigatorio"]]


def chaves_de(entidade: str) -> set:
    return {c["chave"] for c in campos_de(entidade)}
