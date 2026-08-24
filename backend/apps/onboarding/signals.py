"""
Colaborador cadastrado → plano de integração gerado.

É o que fecha o ciclo do Módulo 7: o RH cadastra a pessoa e as tarefas
aparecem sozinhas, com responsáveis e prazos, sem ninguém montar a lista à
mão.
"""

import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def gerar_plano_de_integracao(sender, instance, created, **kwargs):
    if not created or instance.role != "colaborador" or not instance.company_id:
        return

    from .tasks import gerar_onboarding_do_colaborador

    criado_por_id = getattr(instance, "_registered_by_id", None)

    def disparar():
        try:
            gerar_onboarding_do_colaborador.delay(instance.pk, criado_por_id)
        except Exception:
            # Broker fora do ar não pode derrubar o cadastro do colaborador,
            # que é o que de fato importa. O plano é gerado depois, na mão
            # ou aplicando o template pela tela.
            logger.exception(
                "Não foi possível enfileirar o onboarding de %s.", instance.pk
            )

    # on_commit: enfileirar antes do COMMIT faz o worker buscar um usuário
    # que ainda não existe para ele — e a task falha por "não encontrado"
    # numa corrida que só aparece sob carga.
    transaction.on_commit(disparar)
