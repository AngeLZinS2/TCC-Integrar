"""
Monta um "ERP de exemplo" para demonstrar a integração.

Cria um banco SEPARADO, com nomes de tabela e coluna no estilo dos ERPs
que as empresas de fato usam — maiúsculas, português, abreviações — e um
usuário com permissão **apenas de SELECT**. É o cenário real da P4: o
sistema não conhece a estrutura de antemão, e o administrador é quem
informa o significado de cada campo.

Repare que os nomes NÃO seguem nenhum padrão que o código conheça
(`FUNCIONARIOS`, `DEPTO`, `FUNCAO`): é isso que prova que a integração é
genérica, e não feita sob medida para um ERP específico.

    python manage.py seed_erp_exemplo
"""

from contextlib import contextmanager

import psycopg2
from django.conf import settings
from django.core.management.base import BaseCommand
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

BANCO = "erp_exemplo"
USUARIO_LEITURA = "erp_leitura"
SENHA_LEITURA = "leitura-somente-exemplo"

DEPARTAMENTOS = [
    (10, "TECNOLOGIA DA INFORMACAO", "A"),
    (20, "RECURSOS HUMANOS", "A"),
    (30, "COMERCIAL", "A"),
    (40, "LOGISTICA", "A"),
    (50, "FINANCEIRO", "I"),  # inativo de propósito
]

FUNCOES = [
    (100, "DESENVOLVEDOR JUNIOR", 10),
    (101, "DESENVOLVEDOR PLENO", 10),
    (102, "COORDENADOR DE TI", 10),
    (200, "ANALISTA DE RH", 20),
    (201, "GERENTE DE RH", 20),
    (300, "VENDEDOR", 30),
    (301, "SUPERVISOR COMERCIAL", 30),
    (400, "AUXILIAR DE LOGISTICA", 40),
]

# (matrícula, nome, e-mail, depto, função, admissão, situação, cpf, fone)
FUNCIONARIOS = [
    (4501, "ANA CAROLINA PEREIRA", "ana.pereira@exemplo.com.br", 10, 100, "2026-02-10", "A", "111.111.111-11", "11 98888-0001"),
    (4502, "BRUNO MARTINS SOUZA", "bruno.souza@exemplo.com.br", 10, 101, "2024-06-03", "A", "222.222.222-22", "11 98888-0002"),
    (4503, "CARLA DIAS RIBEIRO", "carla.ribeiro@exemplo.com.br", 10, 102, "2021-01-15", "A", "333.333.333-33", "11 98888-0003"),
    (4504, "DANIEL ALVES COSTA", "daniel.costa@exemplo.com.br", 20, 200, "2025-08-20", "A", "444.444.444-44", "11 98888-0004"),
    (4505, "ELISA MOREIRA LIMA", "elisa.lima@exemplo.com.br", 20, 201, "2019-03-11", "A", "555.555.555-55", "11 98888-0005"),
    (4506, "FABIO NUNES ROCHA", "fabio.rocha@exemplo.com.br", 30, 300, "2026-01-05", "A", "666.666.666-66", "11 98888-0006"),
    (4507, "GABRIELA SANTOS CRUZ", "gabriela.cruz@exemplo.com.br", 30, 301, "2022-09-30", "A", "777.777.777-77", "11 98888-0007"),
    (4508, "HENRIQUE BARROS MELO", "henrique.melo@exemplo.com.br", 40, 400, "2026-03-01", "A", "888.888.888-88", "11 98888-0008"),
    # Desligado: serve para demonstrar que a sincronização DESATIVA em vez
    # de apagar, preservando o histórico (seção 21 da P4).
    (4509, "IGOR TEIXEIRA PINTO", "igor.pinto@exemplo.com.br", 40, 400, "2020-05-12", "D", "999.999.999-99", "11 98888-0009"),
    # Sem e-mail: exercita a validação de campo obrigatório vazio.
    (4510, "JULIANA FREITAS ARAUJO", None, 30, 300, "2026-04-18", "A", "101.101.101-01", None),
]


class Command(BaseCommand):
    help = "Cria um banco de ERP fictício e a conexão de exemplo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa",
            default="Empresa Demo",
            help="Empresa que receberá a conexão de exemplo.",
        )

    def handle(self, *args, **options):
        base = settings.DATABASES["default"]
        admin = dict(
            host=base["HOST"], port=base["PORT"] or 5432,
            user=base["USER"], password=base["PASSWORD"],
        )

        self._criar_banco(admin)
        self._criar_estrutura(admin)
        self._criar_usuario_de_leitura(admin)
        self._criar_conexao(options["empresa"], admin)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("ERP de exemplo pronto."))
        self.stdout.write("-" * 58)
        self.stdout.write(f"  Banco:    {BANCO}")
        self.stdout.write(f"  Usuario:  {USUARIO_LEITURA}  (somente SELECT)")
        self.stdout.write(f"  Senha:    {SENHA_LEITURA}")
        self.stdout.write("  Tabelas:  FUNCIONARIOS, DEPTO, FUNCAO")
        self.stdout.write("-" * 58)
        self.stdout.write(
            "  A conexao ja esta salva. Entre como admin@empresa.com,"
        )
        self.stdout.write(
            "  abra Integracao e clique em 'Testar leitura'."
        )
        self.stdout.write("-" * 58)

    # ── Banco ──────────────────────────────────────────────────────────

    @contextmanager
    def _conectar(self, credenciais, banco):
        """
        Conexão em autocommit.

        `with psycopg2.connect(...)` abre uma TRANSAÇÃO, não gerencia o
        ciclo da conexão — e transação anula o autocommit, quebrando
        `CREATE DATABASE` e `CREATE ROLE`. Por isso o contexto é próprio.
        """
        conexao = psycopg2.connect(dbname=banco, **credenciais)
        conexao.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        try:
            yield conexao
        finally:
            conexao.close()

    def _criar_banco(self, admin):
        with self._conectar(admin, "postgres") as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (BANCO,)
                )
                if cursor.fetchone():
                    self.stdout.write(f"  banco {BANCO} ja existe")
                    return
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(BANCO))
                )
                self.stdout.write(f"  banco {BANCO} criado")

    def _criar_estrutura(self, admin):
        with self._conectar(admin, BANCO) as conexao:
            with conexao.cursor() as cursor:
                # Recriado a cada execução: é dado de demonstração, e o
                # comando precisa ser repetível sem acumular duplicata.
                cursor.execute(
                    'DROP TABLE IF EXISTS "FUNCIONARIOS", "FUNCAO", "DEPTO" CASCADE'
                )
                cursor.execute(
                    """
                    CREATE TABLE "DEPTO" (
                        "CODDEPTO"   INTEGER PRIMARY KEY,
                        "DESCRICAO"  VARCHAR(60) NOT NULL,
                        "SITUACAO"   CHAR(1) NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE "FUNCAO" (
                        "CODFUNCAO"  INTEGER PRIMARY KEY,
                        "DESCRICAO"  VARCHAR(60) NOT NULL,
                        "CODDEPTO"   INTEGER REFERENCES "DEPTO"("CODDEPTO")
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE "FUNCIONARIOS" (
                        "MATRICULA"  INTEGER PRIMARY KEY,
                        "NOMEFUNC"   VARCHAR(80) NOT NULL,
                        "EMAILCORP"  VARCHAR(120),
                        "CODDEPTO"   INTEGER REFERENCES "DEPTO"("CODDEPTO"),
                        "CODFUNCAO"  INTEGER REFERENCES "FUNCAO"("CODFUNCAO"),
                        "DTADMISSAO" DATE,
                        "SITUACAO"   CHAR(1) NOT NULL,
                        "CPF"        VARCHAR(14),
                        "FONE"       VARCHAR(20)
                    )
                    """
                )
                cursor.executemany(
                    'INSERT INTO "DEPTO" VALUES (%s, %s, %s)', DEPARTAMENTOS
                )
                cursor.executemany(
                    'INSERT INTO "FUNCAO" VALUES (%s, %s, %s)', FUNCOES
                )
                cursor.executemany(
                    'INSERT INTO "FUNCIONARIOS" '
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    FUNCIONARIOS,
                )
                self.stdout.write(
                    f"  {len(FUNCIONARIOS)} funcionarios, "
                    f"{len(DEPARTAMENTOS)} departamentos, {len(FUNCOES)} funcoes"
                )

    def _criar_usuario_de_leitura(self, admin):
        """
        Cria a conta que a P4 (seção 12) recomenda: SELECT e nada mais.

        Não é a trava principal — a plataforma já não sabe escrever —, mas
        é a camada que protege o cliente mesmo de um erro nosso.
        """
        with self._conectar(admin, BANCO) as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname = %s", (USUARIO_LEITURA,)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(
                            sql.Identifier(USUARIO_LEITURA)
                        ),
                        (SENHA_LEITURA,),
                    )
                cursor.execute(
                    sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                        sql.Identifier(BANCO), sql.Identifier(USUARIO_LEITURA)
                    )
                )
                cursor.execute(
                    sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                        sql.Identifier(USUARIO_LEITURA)
                    )
                )
                cursor.execute(
                    sql.SQL(
                        "GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}"
                    ).format(sql.Identifier(USUARIO_LEITURA))
                )
                # Sem privilégio de escrita em nada, nem em tabela futura.
                cursor.execute(
                    sql.SQL(
                        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                        "GRANT SELECT ON TABLES TO {}"
                    ).format(sql.Identifier(USUARIO_LEITURA))
                )
                self.stdout.write(
                    f"  usuario {USUARIO_LEITURA} com permissao apenas de SELECT"
                )

    # ── Conexão dentro da plataforma ───────────────────────────────────

    def _criar_conexao(self, nome_da_empresa, admin):
        from apps.companies.models import Company
        from apps.integrations.models import ExternalConnection

        empresa = Company.objects.filter(name=nome_da_empresa).first()
        if empresa is None:
            self.stdout.write(
                self.style.WARNING(
                    f"  empresa '{nome_da_empresa}' nao existe — rode seed_data antes"
                )
            )
            return

        conexao, _ = ExternalConnection.objects.get_or_create(
            company=empresa,
            defaults={"tipo": "postgresql"},
        )
        conexao.tipo = "postgresql"
        # `db` é o nome do serviço no compose: de dentro do contêiner, é
        # assim que se alcança o Postgres. "localhost" apontaria para o
        # próprio contêiner do backend.
        conexao.host = admin["host"] or "db"
        conexao.porta = int(admin["port"] or 5432)
        conexao.banco = BANCO
        conexao.schema = "public"
        conexao.usuario = USUARIO_LEITURA
        conexao.senha = SENHA_LEITURA
        conexao.is_active = True
        conexao.save()

        self.stdout.write(f"  conexao de exemplo salva em '{empresa.name}'")
