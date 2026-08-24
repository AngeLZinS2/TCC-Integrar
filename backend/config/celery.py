"""
Configuração do Celery.

O Módulo 10 da P2 é explícito: nem tudo vira task. O critério aqui é —
vai para a fila o que é lento, o que fala com serviço externo, ou o que
gera muitos registros de uma vez. Operações rápidas e locais continuam
síncronas, porque enfileirar tem custo próprio e torna o erro mais difícil
de rastrear.

Vai para a fila:
  - envio de e-mail (rede, pode falhar, precisa de retry);
  - notificação em massa (milhares de linhas);
  - publicação agendada de comunicado;
  - geração de certificado;
  - criação de tarefas de onboarding a partir de template.

Continua síncrono:
  - notificação para UMA pessoa;
  - gravação de auditoria;
  - qualquer coisa que o usuário precise ver refletida na resposta.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("onboarding")

# Toda configuração vem do settings.py, prefixada com CELERY_.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descobre tasks.py em cada app instalado.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task trivial usada pelo healthcheck do worker."""
    return "ok"
