"""
Aniversariantes.

Extraído de `UpcomingBirthdaysView` para ser reaproveitado pela Home do
colaborador e pelo painel do gestor (Módulo 17: nenhuma lógica duplicada
entre views).
"""

import datetime

from django.utils import timezone


def dias_ate_aniversario(nascimento, hoje=None) -> int:
    """
    Dias até o próximo aniversário.

    29 de fevereiro em ano comum é comemorado em 1º de março — a
    alternativa seria a pessoa sumir do painel em três de cada quatro anos.
    """
    hoje = hoje or timezone.localdate()

    def nesse_ano(ano):
        try:
            return nascimento.replace(year=ano)
        except ValueError:
            return datetime.date(ano, 3, 1)

    proximo = nesse_ano(hoje.year)
    if proximo < hoje:
        proximo = nesse_ano(hoje.year + 1)
    return (proximo - hoje).days


def proximos_aniversariantes(queryset, dentro_de_dias: int = 30) -> list:
    """
    `queryset` já filtrado por empresa/ativo/etc. Devolve
    `[(dias, usuario), ...]` ordenado por proximidade.

    `localdate()` e não `now().date()` no chamador: o segundo devolve a
    data em UTC, e à noite no horário de Brasília o aniversariante já teria
    sumido do painel no próprio dia.
    """
    hoje = timezone.localdate()
    proximos = []
    for usuario in queryset.filter(birth_date__isnull=False):
        dias = dias_ate_aniversario(usuario.birth_date, hoje)
        if dias <= dentro_de_dias:
            proximos.append((dias, usuario))
    proximos.sort(key=lambda item: (item[0], item[1].full_name))
    return proximos
