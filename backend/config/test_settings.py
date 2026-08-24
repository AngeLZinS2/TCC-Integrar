"""
Configurações de teste — herda de settings.py e sobrescreve o banco
para SQLite em memória, eliminando dependência de PostgreSQL no CI.
"""

from .settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Senha mais simples em testes (hashear é caro, não precisa de segurança real)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Cache local e isolado para os testes de throttling. A fixture autouse
# `clear_throttle_cache` (conftest.py) zera este cache entre os testes.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "tcc-tests",
    }
}

# E-mail em memória — `django.core.mail.outbox` permite inspecionar o que
# teria sido enviado sem nenhum envio real.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Tasks rodam inline nos testes: sem broker, e a exceção sobe para o teste
# em vez de sumir dentro do worker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Uploads dos testes vao para um diretorio temporario, isolado do
# mediafiles/ real — nenhum teste deixa arquivo para tras.
import tempfile
MEDIA_ROOT = tempfile.mkdtemp(prefix="tcc-test-media-")
