"""
Aplica o schema dw_final (camada semantica agregada) sobre o
Data Warehouse principal.

Este script executa data/06_dw_final_ddl_dml.sql, que recria o
schema dw_final a partir dos dados ja carregados em public pelo
ETL principal (config/etl_multifonte.py). Deve ser executado
sempre depois do ETL, nunca antes, pois depende das tabelas
public.fato_vendas, public.dim_tempo, public.dim_produto,
public.dim_cliente e public.dim_geografia ja populadas.

Uso tipico (dentro do container etl do docker-compose.yml):
    python config/etl_multifonte.py
    python scripts/aplicar_dw_final.py
"""
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine

# Raiz do projeto, independente de onde o script for chamado.
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

CAMINHO_SQL_DW_FINAL = RAIZ_PROJETO / "data" / "06_dw_final_ddl_dml.sql"

DW_URL = os.getenv(
    "DW_DATABASE_URL",
    "postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_dw",
)


def aplicar_dw_final(dw_url=DW_URL, caminho_sql=CAMINHO_SQL_DW_FINAL):
    """Le o arquivo SQL do dw_final e o executa por completo no Data Warehouse.

    O arquivo .sql controla sua propria transacao com BEGIN/COMMIT.
    Por isso, usamos a conexao DBAPI (psycopg2) crua em modo
    autocommit, em vez do gerenciador de transacao do SQLAlchemy:
    assim o BEGIN/COMMIT do arquivo e o unico controle transacional
    enviado ao Postgres, evitando conflito com uma transacao que o
    proprio SQLAlchemy tentaria abrir implicitamente.
    """
    if not caminho_sql.exists():
        raise FileNotFoundError(
            f"Arquivo SQL do dw_final nao encontrado em: {caminho_sql}"
        )

    sql_dw_final = caminho_sql.read_text(encoding="utf-8")

    engine = create_engine(dw_url)

    conexao_bruta = engine.raw_connection()
    try:
        # psycopg2 nao possui autocommit nativo aqui; deixamos o
        # proprio BEGIN/COMMIT do arquivo controlar a transacao e
        # apenas garantimos que a conexao nao aborte silenciosamente
        # um bloco ja concluido.
        cursor = conexao_bruta.cursor()
        cursor.execute(sql_dw_final)
        cursor.close()
        conexao_bruta.commit()
    except Exception:
        conexao_bruta.rollback()
        raise
    finally:
        conexao_bruta.close()

    print("Schema dw_final aplicado com sucesso.")


if __name__ == "__main__":
    try:
        aplicar_dw_final()
    except Exception as erro:
        print(f"Falha ao aplicar o schema dw_final: {erro}", file=sys.stderr)
        sys.exit(1)
