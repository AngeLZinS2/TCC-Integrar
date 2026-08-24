# Garante que o app do Celery seja carregado junto com o Django — sem isso,
# o decorator @shared_task não encontra o broker configurado.
from .celery import app as celery_app

__all__ = ("celery_app",)
