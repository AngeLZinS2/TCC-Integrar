from django.urls import path

from .views import (
    CompanyAwareTokenRefreshView,
    CompanyDirectoryView,
    CustomTokenObtainPairView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ToggleColaboradorActiveView,
    ToggleSectorLeaderView,
)

urlpatterns = [
    # ── Autenticação JWT ────────────────────────────────────────────────────
    # POST  → { email, password }   → { access, refresh, user }
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    # POST  → { refresh }           → { access }  (recusa empresa suspensa)
    path("token/refresh/", CompanyAwareTokenRefreshView.as_view(), name="token_refresh"),
    # POST  → { refresh }           → 205, revoga a sessão no servidor
    path("logout/", LogoutView.as_view(), name="logout"),

    # ── Recuperação de senha ────────────────────────────────────────────────
    # POST  → { email }                                  → mensagem neutra
    path("password-reset/", PasswordResetRequestView.as_view(), name="password_reset"),
    # POST  → { uid, token, new_password, new_password_confirm }
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),

    # ── Perfil do usuário autenticado ───────────────────────────────────────
    # GET   → dados do perfil
    # PATCH → atualiza full_name / sector / position
    path("me/", MeView.as_view(), name="user_me"),

    # ── Cadastro de novo colaborador (apenas rh_admin) ──────────────────────
    # POST  → { email, full_name, role, sector, position, password, password_confirm }
    path("register/", RegisterView.as_view(), name="user_register"),

    # ── Ativar/desativar colaborador (apenas rh_admin, mesma empresa) ───────
    path(
        "colaboradores/<int:pk>/toggle-active/",
        ToggleColaboradorActiveView.as_view(),
        name="toggle_colaborador_active",
    ),

    # ── Conceder/revogar liderança de setor (apenas rh_admin, mesma empresa) ─
    path(
        "colaboradores/<int:pk>/toggle-sector-leader/",
        ToggleSectorLeaderView.as_view(),
        name="toggle_sector_leader",
    ),

    # ── Diretório de colegas da empresa ──────────────────────────────────────
    path("directory/", CompanyDirectoryView.as_view(), name="company_directory"),
]
