"""
Django settings for the Onboarding project.

All sensitive values are loaded from the .env file via django-environ.
Never commit real values — use .env.example as reference.
"""

from datetime import timedelta
from pathlib import Path

import environ

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Environment ───────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000", "http://localhost:8080"]),
)
environ.Env.read_env(BASE_DIR / ".env")

# ── Core ─────────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ── Applications ──────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Django built-ins
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "apps.companies",
    "apps.users",
    "apps.sectors",
    "apps.courses",
    "apps.checklist",
    "apps.materials",
    "apps.notifications",
    "apps.dashboard",
    "apps.audit",
    "apps.requests",
    "apps.communications",
    "apps.events",
    "apps.documents",
    "apps.onboarding",
    "apps.units",
    "apps.automations",
    "django_celery_beat",
]

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",          # deve ficar antes do CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# ── Templates ────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Database ─────────────────────────────────────────────────────────────────
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://onboarding_user:onboarding_pass@localhost:5432/onboarding_db",
    )
}

# ── Auth ─────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# ── Static / Media ────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Estende o JWTAuthentication padrão para reavaliar company.is_active
        # a cada requisição — assim a suspensão de uma empresa vale na hora.
        "apps.users.authentication.CompanyAwareJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Proteção contra força bruta. Os escopos são consumidos pelas classes
    # em apps/users/throttles.py.
    "DEFAULT_THROTTLE_RATES": {
        "login_ip": env("THROTTLE_LOGIN_IP", default="5/min"),
        "login_email": env("THROTTLE_LOGIN_EMAIL", default="5/min"),
        "password_reset": env("THROTTLE_PASSWORD_RESET", default="3/min"),
    },
}

# ── SimpleJWT ─────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    # 15 min (antes 60): é a janela em que uma sessão revogada — por logout ou
    # por troca de senha — ainda consegue chamar a API, já que access token é
    # stateless e não entra em blacklist. Suspensão de empresa não depende
    # dessa janela: é checada a cada request na autenticação.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    # Ligado junto com o app token_blacklist: o refresh antigo morre assim que
    # é rotacionado, impedindo reuso de um token capturado.
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    # Necessário para o Painel RH rastrear quem acessou o sistema (User.last_login).
    # Usuários que nunca logaram desde esta configuração ficam com last_login=null
    # até o próximo login — não há como retroagir o histórico.
    "UPDATE_LAST_LOGIN": True,
}

# ── E-mail ────────────────────────────────────────────────────────────────────
# Em desenvolvimento cai no console; em produção, configure EMAIL_BACKEND SMTP
# e as credenciais via .env.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="nao-responda@onboarding.local")

# Validade do link de recuperação de senha (3 horas).
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT", default=60 * 60 * 3)

# Base usada para montar o link de recuperação enviado por e-mail.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:8080")

# ── CORS ─────────────────────────────────────────────────────────────────────
# Em desenvolvimento (DEBUG=True), libera origens de qualquer porta do Flutter Web
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=DEBUG)
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000", "http://localhost:8080"])
CORS_ALLOW_CREDENTIALS = True

# ── drf-spectacular (Swagger/OpenAPI) ─────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Onboarding API",
    "DESCRIPTION": "API do sistema de integração de colaboradores",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ── Celery / Redis ────────────────────────────────────────────────────────────
# Broker e backend de resultado. Em desenvolvimento sem Redis no ar, o modo
# EAGER (abaixo) executa as tasks em processo, para o sistema não travar.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Tarefa devolvida à fila se o worker morrer no meio — evita perder trabalho
# num deploy ou reinício.
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Teto de segurança: nenhuma task pode rodar indefinidamente.
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 5
CELERY_TASK_TIME_LIMIT = 60 * 10

# Com EAGER ligado a task roda inline e levanta a exceção no chamador — é o
# modo usado nos testes e num ambiente sem Redis. Fora isso, vai para a fila.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True

# Agendador persistido no banco, para o Beat sobreviver a reinícios.
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Tarefas periodicas (Modulo 11). Horarios em TIME_ZONE (America/Sao_Paulo).
# Cada task e idempotente: se o Beat disparar duas vezes, ninguem recebe
# aviso em dobro.
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "documentos-obrigatorios-pendentes": {
        "task": "apps.documents.tasks.avisar_documentos_obrigatorios_pendentes",
        # 9h da manha: o aviso chega no comeco do expediente, nao de
        # madrugada quando ninguem vai ler.
        "schedule": crontab(hour=9, minute=0),
    },
    "arquivar-documentos-expirados": {
        "task": "apps.documents.tasks.arquivar_documentos_expirados",
        "schedule": crontab(hour=1, minute=0),
    },
    "publicar-comunicados-agendados": {
        "task": "apps.communications.tasks.publicar_agendados",
        # De 5 em 5 min: e a granularidade util para um agendamento que o
        # RH marca em hora cheia.
        "schedule": crontab(minute="*/5"),
    },
    "onboarding-tarefas-atrasadas": {
        "task": "apps.onboarding.tasks.avisar_tarefas_atrasadas",
        # 9h05: logo depois do aviso de documentos, para as duas cobrancas
        # do dia chegarem juntas e nao pingarem ao longo da manha.
        "schedule": crontab(hour=9, minute=5),
    },
}

# ── Cache (Redis) ─────────────────────────────────────────────────────────────
# Substitui o LocMemCache, que é por processo — com mais de um worker, o
# throttle de login contava separado em cada um, multiplicando o limite.
REDIS_CACHE_URL = env("REDIS_CACHE_URL", default="")
if REDIS_CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_CACHE_URL,
        }
    }

# ── Logging estruturado ───────────────────────────────────────────────────────
# Módulo 30: o mínimo para conseguir investigar falha de worker, de envio de
# e-mail e de automação sem adivinhação.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "apps": {"level": env("LOG_LEVEL", default="INFO"), "handlers": ["console"], "propagate": False},
        "celery": {"level": "INFO", "handlers": ["console"], "propagate": False},
    },
}
