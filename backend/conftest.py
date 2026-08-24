"""
Fixtures globais do pytest-django.

O banco é SQLite em memória (definido em config/test_settings.py),
portanto nenhuma instância de PostgreSQL é necessária para rodar os testes.
"""

import pytest


# ── Isolamento de throttling entre testes ────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """
    Zera o cache antes e depois de cada teste.

    Os throttles de login guardam o histórico de tentativas no cache, que é
    compartilhado por todo o processo do pytest. Sem esta limpeza, um teste
    que faz login "gastaria" tentativas do teste seguinte.
    """
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


# ── Fixture de empresa (tenant) ──────────────────────────────────────────────

@pytest.fixture
def company(db):
    """Empresa padrão à qual os usuários de teste pertencem."""
    from apps.companies.models import Company
    return Company.objects.create(name="Empresa Teste")


# ── Fixtures de usuários ─────────────────────────────────────────────────────

@pytest.fixture
def rh_admin_user(db, django_user_model, company):
    """Usuário RH Admin pronto para autenticação nos testes."""
    return django_user_model.objects.create_user(
        email="rh@example.com",
        full_name="RH Admin",
        password="senha@123",
        role="rh_admin",
        company=company,
        is_staff=True,
    )


@pytest.fixture
def colaborador_user(db, django_user_model, company):
    """Usuário Colaborador pronto para autenticação nos testes."""
    return django_user_model.objects.create_user(
        email="colaborador@example.com",
        full_name="João Silva",
        password="senha@123",
        role="colaborador",
        company=company,
    )


@pytest.fixture
def owner_user(db, django_user_model):
    """Usuário Dono do Sistema — não pertence a nenhuma empresa."""
    return django_user_model.objects.create_user(
        email="owner@example.com",
        full_name="Dono do Sistema",
        password="senha@123",
        role="owner",
        is_staff=True,
    )


# ── Fixture de cliente HTTP ──────────────────────────────────────────────────

@pytest.fixture
def api_client():
    """APIClient do DRF sem autenticação prévia."""
    from rest_framework.test import APIClient
    return APIClient()
