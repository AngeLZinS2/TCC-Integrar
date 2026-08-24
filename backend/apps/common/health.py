"""
Healthcheck da aplicação.

Público de propósito: é consultado pelo Docker e por qualquer balanceador
antes de haver sessão. Por isso não revela nada além de "o serviço
responde" — nomes de host, versões e credenciais ficam de fora.
"""

import logging

from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def _check_database() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        logger.exception("Healthcheck: banco indisponível.")
        return False


def _check_cache() -> bool:
    try:
        cache.set("healthcheck", "1", 10)
        return cache.get("healthcheck") == "1"
    except Exception:
        logger.exception("Healthcheck: cache indisponível.")
        return False


def _check_worker() -> bool | None:
    """
    True/False se der para perguntar ao broker; None quando não há fila
    configurada (ambiente de teste ou modo síncrono) — nesse caso o worker
    não é um requisito e não deve derrubar o healthcheck.
    """
    from django.conf import settings

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        return None
    try:
        from config.celery import app

        replies = app.control.ping(timeout=1.0)
        return bool(replies)
    except Exception:
        logger.exception("Healthcheck: não foi possível falar com o worker.")
        return False


class HealthCheckView(APIView):
    """
    GET /api/v1/health/

    200 quando banco e cache respondem. O worker entra no relatório mas
    não derruba o status: a API continua servindo leitura mesmo com a fila
    parada, e marcar o container como unhealthy causaria um restart que não
    resolveria nada.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        database_ok = _check_database()
        cache_ok = _check_cache()
        worker_ok = _check_worker()

        essenciais_ok = database_ok and cache_ok

        corpo = {
            "status": "ok" if essenciais_ok else "degraded",
            "checks": {
                "database": "ok" if database_ok else "fail",
                "cache": "ok" if cache_ok else "fail",
                "worker": {True: "ok", False: "fail", None: "disabled"}[worker_ok],
            },
        }
        return Response(
            corpo,
            status=status.HTTP_200_OK if essenciais_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
