"""
Registro dos bancos suportados.

Acrescentar um banco é escrever a classe e registrá-la aqui: nem o Mapping
Engine nem as views mudam, que é o que a seção 6 da P4 pede.
"""

from .base import Coluna, Credenciais, DataConnector, FalhaDeConexao, Tabela
from .mysql import MariaDBConnector, MySQLConnector
from .oracle import OracleConnector
from .postgres import PostgresConnector

CONNECTORES = {
    PostgresConnector.chave: PostgresConnector,
    MySQLConnector.chave: MySQLConnector,
    MariaDBConnector.chave: MariaDBConnector,
    OracleConnector.chave: OracleConnector,
}

# Rótulos para a tela e para o `choices` do model.
BANCOS_SUPORTADOS = [
    (PostgresConnector.chave, "PostgreSQL"),
    (MySQLConnector.chave, "MySQL"),
    (MariaDBConnector.chave, "MariaDB"),
    (OracleConnector.chave, "Oracle"),
]


def connector_para(tipo: str, credenciais: Credenciais) -> DataConnector:
    """Instancia o connector do tipo pedido."""
    classe = CONNECTORES.get(str(tipo).lower())
    if classe is None:
        raise FalhaDeConexao(f"Banco não suportado: {tipo}.")
    return classe(credenciais)


__all__ = [
    "BANCOS_SUPORTADOS",
    "CONNECTORES",
    "Coluna",
    "Credenciais",
    "DataConnector",
    "FalhaDeConexao",
    "Tabela",
    "connector_para",
]
