from django.db import models


class Company(models.Model):
    """
    Empresa cliente (tenant) da plataforma. Cada empresa tem seus próprios
    setores, cargos, cursos, checklist e materiais, totalmente isolados dos
    de outras empresas.

    Uma empresa desativada (is_active=False) bloqueia o login de todos os
    seus usuários — ver CustomTokenObtainPairSerializer.validate().
    """

    name = models.CharField(max_length=150, unique=True, verbose_name="Nome")
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")

    # ── Identidade da empresa, editável pelo admin do próprio tenant ────────
    # Todos opcionais: uma empresa recém-criada precisa funcionar antes de
    # preencher o cadastro completo.
    legal_name = models.CharField(
        max_length=200, blank=True, verbose_name="Razão social",
    )
    cnpj = models.CharField(
        max_length=18, blank=True, verbose_name="CNPJ",
        help_text="Somente números ou no formato 00.000.000/0000-00.",
    )
    description = models.TextField(blank=True, verbose_name="Descrição")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    email = models.EmailField(blank=True, verbose_name="E-mail de contato")
    address = models.CharField(max_length=250, blank=True, verbose_name="Endereço")
    logo_url = models.URLField(
        blank=True, verbose_name="Logo",
        help_text="URL da logo. Upload com storage privado fica para uma fase posterior.",
    )

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["name"]

    def __str__(self) -> str:
        status = "" if self.is_active else " (inativa)"
        return f"{self.name}{status}"
