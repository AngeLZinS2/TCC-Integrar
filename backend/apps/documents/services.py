"""
Regras de documentos compartilhadas entre views e painéis.
"""

from .models import DocumentAcceptance


def pendentes_de_aceite(user):
    """
    Documentos obrigatórios que `user` ainda precisa aceitar.

    Mora aqui, e não dentro da view, porque a Home do colaborador conta o
    mesmo conjunto. Duplicar a regra já tinha produzido divergência: a Home
    contava documento SEM versão publicada, que a listagem (corretamente)
    escondia — a pessoa via "1 documento pendente" e não achava o documento
    em lugar nenhum.

    O aceite é por VERSÃO: publicar uma versão nova reabre a exigência para
    todo mundo.
    """
    from .views import documentos_visiveis

    aceitos = DocumentAcceptance.objects.filter(user=user).values_list(
        "document_version_id", flat=True
    )
    return (
        documentos_visiveis(user)
        .filter(is_required=True, versions__is_active=True)
        .exclude(versions__id__in=aceitos)
        .distinct()
    )
