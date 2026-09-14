"""Conector da unidade Itabuna (PostgreSQL) para o DW consolidado."""
import importlib.util
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, inspect

SOURCE_URL = os.getenv("POSTGRES_SOURCE_DATABASE_URL", "postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_postgres")
DW_URL = os.getenv("DW_DATABASE_URL", "postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_dw")
TABELAS = ("clientes", "produtos", "vendas", "itens_venda")


def _executor():
    caminho = Path(__file__).with_name("2_etl_oracle.py")
    spec = importlib.util.spec_from_file_location("etl_dimensional", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.executar_etl


def executar_etl(source_url=SOURCE_URL, dw_url=DW_URL):
    source = create_engine(source_url)
    existentes = set(inspect(source).get_table_names())
    faltantes = set(TABELAS) - existentes
    if faltantes:
        raise RuntimeError(f"Tabelas ausentes na origem PostgreSQL: {sorted(faltantes)}")
    tabelas = {nome: pd.read_sql(f"SELECT * FROM {nome}", source) for nome in TABELAS}
    if all(frame.empty for frame in tabelas.values()):
        print("ETL POSTGRES ignorado: origem vazia.")
        return 0
    return _executor()(dw_url=dw_url, tabelas=tabelas, banco_origem="POSTGRES",
        nome_empresa=os.getenv("POSTGRES_NOME_EMPRESA", "Pet Shop Nosso Aumigo"),
        nome_unidade=os.getenv("POSTGRES_NOME_UNIDADE", "Itabuna"),
        cidade=os.getenv("POSTGRES_CIDADE", "Itabuna"), estado=os.getenv("POSTGRES_ESTADO", "Bahia"),
        uf=os.getenv("POSTGRES_UF", "BA"), regiao=os.getenv("POSTGRES_REGIAO", "Nordeste"))


if __name__ == "__main__":
    executar_etl()
