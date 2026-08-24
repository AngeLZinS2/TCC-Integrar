"""
Segmentação de conteúdo por setor, cargo e unidade.

A regra é a mesma em comunicados, eventos, documentos e treinamentos, e
reescrevê-la quatro vezes é o caminho para ela divergir num dos quatro —
que é exatamente onde um comunicado sigiloso vaza.

Semântica: os alvos AFUNILAM, não somam.

    "TI" + "Desenvolvedor"  → os desenvolvedores DE TI
                              (não todo o TI mais todos os devs da empresa)

Dentro de uma dimensão vale OU (dois setores marcados = qualquer um dos
dois). Entre dimensões vale E. Dimensão vazia não restringe nada.
"""

from django.db.models import Exists, OuterRef, Q


def _dimensao(campo_m2m, coluna_alvo, coluna_dono, valor_do_usuario, sufixo):
    """
    Monta o par de anotações de UMA dimensão.

    Devolve (anotações, condição). A condição é "não tem alvo nesta
    dimensão OU o alvo inclui o usuário".
    """
    through = campo_m2m.through.objects
    tem = f"_tem_alvo_{sufixo}"
    meu = f"_e_meu_{sufixo}"

    anotacoes = {
        tem: Exists(through.filter(**{coluna_dono: OuterRef("pk")})),
        # `or 0` para usuário sem setor/cargo/unidade: um id inexistente
        # nunca casa, então ele simplesmente não é alcançado por um alvo
        # dessa dimensão — em vez de o filtro virar NULL e derrubar a linha
        # inteira de forma silenciosa.
        meu: Exists(
            through.filter(
                **{coluna_dono: OuterRef("pk"), coluna_alvo: valor_do_usuario or 0}
            )
        ),
    }
    condicao = Q(**{tem: False}) | Q(**{meu: True})
    return anotacoes, condicao


def narrow_to_user(queryset, user, dimensoes):
    """
    Aplica o afunilamento a um queryset.

    `dimensoes` é uma lista de tuplas:
        (campo_m2m, coluna_do_alvo, coluna_do_dono, valor_no_usuario, sufixo)

    Usa `Exists` e não JOIN + distinct(): com dois M2M no mesmo `filter()`,
    o JOIN combinado produz linhas cruzadas e a condição deixa de ser um E
    real entre as dimensões — o bug que fazia um comunicado de "TI +
    Desenvolvedor" chegar em todo o TI.
    """
    anotacoes = {}
    condicao = Q()
    for campo, coluna_alvo, coluna_dono, valor, sufixo in dimensoes:
        novas, parcial = _dimensao(campo, coluna_alvo, coluna_dono, valor, sufixo)
        anotacoes.update(novas)
        condicao &= parcial

    if not anotacoes:
        return queryset
    return queryset.annotate(**anotacoes).filter(condicao)


def unit_dimension(model, campo="target_units", coluna_dono=None):
    """Atalho para a dimensão de unidade, que é igual em todos os módulos."""
    coluna_dono = coluna_dono or f"{model.__name__.lower()}_id"
    return (getattr(model, campo), "unit_id", coluna_dono, None, "unidade")


def alcanca_usuario(objeto, user, dimensoes) -> bool:
    """
    Versão pontual, para checar UM objeto sem consultar o banco de novo.

    `dimensoes` aqui é uma lista de (ids_do_alvo, valor_no_usuario).
    """
    for ids_alvo, valor in dimensoes:
        ids_alvo = set(ids_alvo or [])
        if ids_alvo and valor not in ids_alvo:
            return False
    return True
