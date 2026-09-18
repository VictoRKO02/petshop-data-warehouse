from pathlib import Path
import os
import subprocess
import sys
import time
import re
import socket


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT = Path(__file__).resolve().parent.parent


def carregar_arquivo_env(caminho=ROOT / ".env"):
    """Carrega pares simples CHAVE=VALOR sem sobrescrever o ambiente do usuário."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


carregar_arquivo_env()

COMPOSE_ORIGINAL = ROOT / "docker-compose.yml"
COMPOSE_TESTE = ROOT / "docker-compose.test.yml"

PROJECT_NAME = "dw_petshop_teste"

HOST = "127.0.0.1"
PORT = 5434

ADMIN_USER = os.getenv("POSTGRES_USER", "postgres")
ADMIN_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

DATABASE = "petshop_dw"

PET_USER = "pet_user"
PET_PASSWORD = "123456"

EXPECTED_COUNTS = {
    "dim_tempo": 6,
    "dim_produto": 17,
    "dim_estado_civil": 6,
    "dim_loja": 3,
    "fato_vendas": 1382,
    "fato_concorrente": 6,
}


# ============================================================
# SQL DO DW FINAL
# ============================================================

SQL_DW_FINAL = r"""
BEGIN;

DROP SCHEMA IF EXISTS dw_final CASCADE;

CREATE SCHEMA dw_final;


-- ============================================================
-- 1. DIMENSÃO TEMPO
-- ============================================================

CREATE TABLE dw_final.dim_tempo (
    pk_tempo BIGSERIAL PRIMARY KEY,
    quadrimestre SMALLINT NOT NULL,
    ano SMALLINT NOT NULL,
    UNIQUE (ano, quadrimestre)
);

INSERT INTO dw_final.dim_tempo (
    quadrimestre,
    ano
)
SELECT DISTINCT
    quadrimestre,
    ano
FROM public.dim_tempo
WHERE quadrimestre IS NOT NULL
  AND ano IS NOT NULL
ORDER BY
    ano,
    quadrimestre;


-- ============================================================
-- 2. DIMENSÃO PRODUTO
-- Unifica produtos repetidos entre as fontes
-- ============================================================

CREATE TABLE dw_final.dim_produto (
    pk_produto BIGSERIAL PRIMARY KEY,
    nome_produto VARCHAR(255) NOT NULL,
    categoria VARCHAR(255) NOT NULL
);

INSERT INTO dw_final.dim_produto (
    nome_produto,
    categoria
)
SELECT
    MIN(TRIM(nome_produto)) AS nome_produto,

    COALESCE(
        MIN(TRIM(categoria))
        FILTER (
            WHERE NULLIF(TRIM(categoria), '') IS NOT NULL
              AND UPPER(TRIM(categoria)) <> 'SEM CATEGORIA'
        ),
        'SEM CATEGORIA'
    ) AS categoria

FROM public.dim_produto

WHERE NULLIF(TRIM(nome_produto), '') IS NOT NULL

GROUP BY
    UPPER(TRIM(nome_produto))

ORDER BY
    MIN(TRIM(nome_produto));


-- ============================================================
-- 3. DIMENSÃO ESTADO CIVIL
-- ============================================================

CREATE TABLE dw_final.dim_estado_civil (
    pk_estado_civil BIGSERIAL PRIMARY KEY,
    estado_civil VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO dw_final.dim_estado_civil (
    estado_civil
)
SELECT DISTINCT
    COALESCE(
        NULLIF(UPPER(TRIM(estado_civil)), ''),
        'NAO INFORMADO'
    )
FROM public.dim_cliente
ORDER BY 1;


-- ============================================================
-- 4. DIMENSÃO LOJA
-- Uma unidade por cidade
-- ============================================================

CREATE TABLE dw_final.dim_loja (
    pk_loja BIGSERIAL PRIMARY KEY,
    nome_loja VARCHAR(150) NOT NULL,
    cidade VARCHAR(100) NOT NULL UNIQUE
);

INSERT INTO dw_final.dim_loja (
    nome_loja,
    cidade
)
SELECT
    MIN(TRIM(g.cidade)) AS nome_loja,
    MIN(TRIM(g.cidade)) AS cidade

FROM public.fato_vendas f

JOIN public.dim_geografia g
    ON f.sk_geografia = g.sk_geografia

WHERE NULLIF(TRIM(g.cidade), '') IS NOT NULL

GROUP BY
    UPPER(TRIM(g.cidade))

ORDER BY
    MIN(TRIM(g.cidade));


-- ============================================================
-- 5. FATO VENDAS
--
-- Granularidade:
-- Tempo x Produto x Estado Civil x Loja
-- ============================================================

CREATE TABLE dw_final.fato_vendas (
    id_vendas BIGSERIAL PRIMARY KEY,

    pk_tempo BIGINT NOT NULL,
    pk_estado_civil BIGINT NOT NULL,
    pk_produto BIGINT NOT NULL,
    pk_loja BIGINT NOT NULL,

    quantidade BIGINT NOT NULL,
    valor_total NUMERIC(18,2) NOT NULL,

    FOREIGN KEY (pk_tempo)
        REFERENCES dw_final.dim_tempo(pk_tempo),

    FOREIGN KEY (pk_estado_civil)
        REFERENCES dw_final.dim_estado_civil(pk_estado_civil),

    FOREIGN KEY (pk_produto)
        REFERENCES dw_final.dim_produto(pk_produto),

    FOREIGN KEY (pk_loja)
        REFERENCES dw_final.dim_loja(pk_loja)
);


INSERT INTO dw_final.fato_vendas (
    pk_tempo,
    pk_estado_civil,
    pk_produto,
    pk_loja,
    quantidade,
    valor_total
)
SELECT
    dt_final.pk_tempo,
    dec.pk_estado_civil,
    dp_final.pk_produto,
    dl.pk_loja,

    SUM(COALESCE(f.quantidade, 0)),
    SUM(COALESCE(f.valor_venda, 0))

FROM public.fato_vendas f


JOIN public.dim_tempo dt_origem
    ON f.sk_tempo = dt_origem.sk_tempo

JOIN dw_final.dim_tempo dt_final
    ON dt_final.ano = dt_origem.ano
   AND dt_final.quadrimestre = dt_origem.quadrimestre


JOIN public.dim_cliente c
    ON f.sk_cliente = c.sk_cliente

JOIN dw_final.dim_estado_civil dec
    ON dec.estado_civil =
       COALESCE(
           NULLIF(UPPER(TRIM(c.estado_civil)), ''),
           'NAO INFORMADO'
       )


JOIN public.dim_produto dp_origem
    ON f.sk_produto = dp_origem.sk_produto

JOIN dw_final.dim_produto dp_final
    ON UPPER(TRIM(dp_origem.nome_produto))
       = UPPER(TRIM(dp_final.nome_produto))


JOIN public.dim_geografia g
    ON f.sk_geografia = g.sk_geografia

JOIN dw_final.dim_loja dl
    ON UPPER(TRIM(g.cidade))
       = UPPER(TRIM(dl.cidade))


GROUP BY
    dt_final.pk_tempo,
    dec.pk_estado_civil,
    dp_final.pk_produto,
    dl.pk_loja;


-- ============================================================
-- 6. FATO CONCORRENTE
-- ============================================================

CREATE TABLE dw_final.fato_concorrente (
    pk_concorrente BIGSERIAL PRIMARY KEY,

    pk_tempo BIGINT NOT NULL,
    valor_venda NUMERIC(18,2) NOT NULL,

    FOREIGN KEY (pk_tempo)
        REFERENCES dw_final.dim_tempo(pk_tempo)
);


INSERT INTO dw_final.fato_concorrente (
    pk_tempo,
    valor_venda
)
SELECT
    dt_final.pk_tempo,
    SUM(COALESCE(fc.valor_venda, 0))

FROM public.fato_vendas_concorrente fc

JOIN public.dim_tempo dt_origem
    ON fc.sk_tempo = dt_origem.sk_tempo

JOIN dw_final.dim_tempo dt_final
    ON dt_final.ano = dt_origem.ano
   AND dt_final.quadrimestre = dt_origem.quadrimestre

GROUP BY
    dt_final.pk_tempo;


-- ============================================================
-- ACESSO DO PET_USER
-- ============================================================

GRANT USAGE
ON SCHEMA dw_final
TO pet_user;

GRANT SELECT
ON ALL TABLES
IN SCHEMA dw_final
TO pet_user;


COMMIT;
"""


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def executar(comando, check=True, capturar=False):
    print("\n>", " ".join(map(str, comando)))

    resultado = subprocess.run(
        comando,
        cwd=ROOT,
        text=True,
        capture_output=capturar
    )

    if capturar:
        if resultado.stdout:
            print(resultado.stdout)

        if resultado.stderr:
            print(resultado.stderr)

    if check and resultado.returncode != 0:
        raise RuntimeError(
            f"Comando falhou com código {resultado.returncode}"
        )

    return resultado


def preparar_compose_teste():
    """Garante que docker-compose.test.yml existe e publica o PostgreSQL na porta isolada de teste.

    Em vez de tentar reescrever automaticamente docker-compose.yml (fonte de bugs quando o
    formato da porta muda, por exemplo ao usar variáveis de ambiente como
    ${POSTGRES_PORT:-5432}:5432), o repositório já mantém um docker-compose.test.yml versionado
    e revisado manualmente. Esta função apenas valida que ele existe e que a porta publicada do
    PostgreSQL corresponde à porta isolada de teste (PORT), corrigindo-a automaticamente caso o
    arquivo tenha sido editado de forma inconsistente.
    """
    if not COMPOSE_ORIGINAL.exists():
        raise FileNotFoundError(
            f"Não encontrei {COMPOSE_ORIGINAL}"
        )

    if not COMPOSE_TESTE.exists():
        raise FileNotFoundError(
            f"Não encontrei {COMPOSE_TESTE}. "
            "Este arquivo deve existir no repositório e ser mantido manualmente; "
            "ele não é mais gerado automaticamente a partir de docker-compose.yml."
        )

    conteudo = COMPOSE_TESTE.read_text(encoding="utf-8")

    # Regex tolerante: casa qualquer mapeamento externo:5432 do serviço postgres,
    # com ou sem aspas, com ou sem prefixo de host (ex.: 0.0.0.0:), com porta fixa
    # (5432, 5433, 5434...) ou baseada em variável de ambiente (${POSTGRES_PORT:-5432}).
    padrao_porta = re.compile(
        r'(["\']?)(?:0\.0\.0\.0:)?(?:\$\{[^}]+\}|\d+):5432\1'
    )

    porta_esperada = f'"{PORT}:5432"'

    if padrao_porta.search(conteudo):
        novo_conteudo, alteracoes = padrao_porta.subn(porta_esperada, conteudo, count=1)
    else:
        novo_conteudo, alteracoes = conteudo, 0

    if alteracoes == 0:
        # Não encontrar o padrão não é fatal: o arquivo de teste pode já ter sido
        # escrito manualmente em outro formato. Avisamos e seguimos, deixando a
        # validação de esperar_porta() detectar qualquer incompatibilidade real.
        print(
            "AVISO: não encontrei automaticamente o mapeamento de porta do "
            f"PostgreSQL em {COMPOSE_TESTE.name}."
        )
        print(
            f"Confirme manualmente que o serviço postgres publica a porta {PORT} "
            "antes de prosseguir."
        )
    elif novo_conteudo != conteudo:
        COMPOSE_TESTE.write_text(novo_conteudo, encoding="utf-8")
        print(
            f"\nCorrigido {COMPOSE_TESTE.name}: PostgreSQL de teste agora publica a porta {PORT}."
        )
    else:
        print(f"\n{COMPOSE_TESTE.name} já está correto (porta {PORT}).")


def docker_cmd(*args):
    return [
        "docker",
        "compose",
        "-p",
        PROJECT_NAME,
        "-f",
        str(COMPOSE_TESTE),
        *args
    ]


def esperar_postgres():
    print("\nAguardando PostgreSQL ficar saudável...")

    limite = time.time() + 120

    while time.time() < limite:
        resultado = subprocess.run(
            docker_cmd("ps", "-q", "postgres"),
            cwd=ROOT,
            text=True,
            capture_output=True
        )

        container_id = resultado.stdout.strip()

        if container_id:
            inspect = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{if .State.Health}}"
                    "{{.State.Health.Status}}"
                    "{{else}}{{.State.Status}}{{end}}",
                    container_id
                ],
                text=True,
                capture_output=True
            )

            status = inspect.stdout.strip()

            print(f"PostgreSQL: {status}")

            if status in ("healthy", "running"):
                return

        time.sleep(2)

    raise TimeoutError(
        "PostgreSQL não ficou pronto dentro do tempo esperado."
    )


def esperar_etl():
    print("\nAguardando ETL terminar...")

    limite = time.time() + 600

    while time.time() < limite:
        resultado = subprocess.run(
            docker_cmd("ps", "-a", "-q", "etl"),
            cwd=ROOT,
            text=True,
            capture_output=True
        )

        container_id = resultado.stdout.strip()

        if not container_id:
            time.sleep(2)
            continue

        inspect = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Status}} {{.State.ExitCode}}",
                container_id
            ],
            text=True,
            capture_output=True
        )

        estado = inspect.stdout.strip()

        print(f"ETL: {estado}")

        if estado.startswith("exited"):
            partes = estado.split()

            exit_code = int(partes[1])

            executar(
                docker_cmd(
                    "logs",
                    "--tail",
                    "30",
                    "etl"
                ),
                check=False
            )

            if exit_code == 0:
                print("\nETL concluído com sucesso.")
                return

            raise RuntimeError(
                f"ETL terminou com erro. Exit code: {exit_code}"
            )

        time.sleep(3)

    raise TimeoutError(
        "ETL não terminou dentro do tempo esperado."
    )


def instalar_psycopg2():
    try:
        import psycopg2
        return psycopg2

    except ImportError:
        print("\nInstalando psycopg2-binary...")

        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "psycopg2-binary"
        ])

        import psycopg2
        return psycopg2


def esperar_porta():
    print(f"\nAguardando {HOST}:{PORT}...")

    limite = time.time() + 60

    while time.time() < limite:
        try:
            with socket.create_connection(
                (HOST, PORT),
                timeout=2
            ):
                print("Porta PostgreSQL disponível.")
                return

        except OSError:
            time.sleep(1)

    raise TimeoutError(
        f"Não consegui acessar {HOST}:{PORT}."
    )


def criar_dw():
    psycopg2 = instalar_psycopg2()

    print("\nConectando ao petshop_dw...")

    conn = psycopg2.connect(
        host=HOST,
        port=PORT,
        database=DATABASE,
        user=ADMIN_USER,
        password=ADMIN_PASSWORD
    )

    conn.autocommit = True

    try:
        with conn.cursor() as cursor:
            print("\nCriando dw_final...")
            cursor.execute(SQL_DW_FINAL)

    finally:
        conn.close()

    print("dw_final criado com sucesso.")


def validar_dw():
    psycopg2 = instalar_psycopg2()

    conn = psycopg2.connect(
        host=HOST,
        port=PORT,
        database=DATABASE,
        user=ADMIN_USER,
        password=ADMIN_PASSWORD
    )

    consultas = {
        "dim_tempo":
            "SELECT COUNT(*) FROM dw_final.dim_tempo",

        "dim_produto":
            "SELECT COUNT(*) FROM dw_final.dim_produto",

        "dim_estado_civil":
            "SELECT COUNT(*) FROM dw_final.dim_estado_civil",

        "dim_loja":
            "SELECT COUNT(*) FROM dw_final.dim_loja",

        "fato_vendas":
            "SELECT COUNT(*) FROM dw_final.fato_vendas",

        "fato_concorrente":
            "SELECT COUNT(*) FROM dw_final.fato_concorrente",
    }

    print("\n========================================")
    print("VALIDAÇÃO DO DW")
    print("========================================")

    resultados = {}

    with conn.cursor() as cursor:
        for tabela, sql in consultas.items():
            cursor.execute(sql)

            total = cursor.fetchone()[0]

            resultados[tabela] = total

            print(f"{tabela:<22} {total}")

        for tabela, esperado in EXPECTED_COUNTS.items():
            obtido = resultados[tabela]
            if obtido != esperado:
                raise AssertionError(
                    f"{tabela}: esperado {esperado}, obtido {obtido}"
                )

        print("\nOK: contagens esperadas confirmadas.")

        # -----------------------------------------------
        # Combinações máximas
        # -----------------------------------------------

        maximo = (
            resultados["dim_tempo"]
            * resultados["dim_produto"]
            * resultados["dim_estado_civil"]
            * resultados["dim_loja"]
        )

        ausentes = maximo - resultados["fato_vendas"]

        print("\n----------------------------------------")
        print(f"Combinações máximas:   {maximo}")
        print(f"Combinações existentes:{resultados['fato_vendas']}")
        print(f"Combinações ausentes:  {ausentes}")

        # -----------------------------------------------
        # Totais antes e depois
        # -----------------------------------------------

        cursor.execute("""
            SELECT
                SUM(quantidade),
                SUM(valor_venda)
            FROM public.fato_vendas
        """)

        qtd_public, valor_public = cursor.fetchone()

        cursor.execute("""
            SELECT
                SUM(quantidade),
                SUM(valor_total)
            FROM dw_final.fato_vendas
        """)

        qtd_dw, valor_dw = cursor.fetchone()

        print("\n----------------------------------------")
        print("VALIDAÇÃO DOS VALORES")
        print("----------------------------------------")

        print(f"Quantidade PUBLIC:   {qtd_public}")
        print(f"Quantidade DW_FINAL: {qtd_dw}")

        print(f"Valor PUBLIC:        {valor_public}")
        print(f"Valor DW_FINAL:      {valor_dw}")

        if qtd_public == qtd_dw and valor_public == valor_dw:
            print("\nOK: nenhum valor foi perdido.")
        else:
            raise AssertionError(
                "Os totais de quantidade ou valor diferem entre public e dw_final."
            )

    conn.close()


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():
    print("""
===========================================
 PET SHOP - AMBIENTE DE TESTE
===========================================

Projeto:
dw_petshop_teste

Banco:
petshop_dw

Porta:
5434
""")

    preparar_compose_teste()

    # Remove SOMENTE containers do projeto de teste.
    # Não apaga volumes.
    executar(
        docker_cmd("down"),
        check=False
    )

    # Sobe o ambiente novo.
    executar(
        docker_cmd("up", "-d")
    )

    esperar_postgres()

    esperar_etl()

    esperar_porta()

    criar_dw()

    validar_dw()

    print("""
===========================================
 AMBIENTE PRONTO
===========================================

PGADMIN / POWER BI

Host:
127.0.0.1

Port:
5434

Database:
petshop_dw

Username:
pet_user

Password:
123456


ADMINISTRADOR

Username:
postgres

Password:
postgres


Schema:
dw_final
===========================================
""")


if __name__ == "__main__":
    main()
