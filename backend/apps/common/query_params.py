"""
Helpers para parsing seguro de query params usados em filtros de queryset.

Query params chegam sempre como string (ou None). Passar um valor não
numérico direto para um filtro de FK/IntegerField (ex.: `.filter(sector_id=x)`)
faz o Django tentar `int(x)` durante a montagem da query e estoura um
`ValueError` não tratado pelo DRF — resultando em 500 em vez de um 400 limpo.
"""

from rest_framework.exceptions import ValidationError


def parse_int_param(value, *, param_name="id"):
    """
    Converte um query param string para int, ou retorna None se ausente/vazio.
    Levanta ValidationError (→ 400) se o valor não for um inteiro válido.
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({param_name: f"'{value}' não é um valor válido para {param_name}."})
