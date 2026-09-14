"""ETL principal: recria e preenche o OLAP com todas as fontes disponíveis."""
import importlib.util
import os
from pathlib import Path

from sqlalchemy import create_engine, text

DW_URL = os.getenv("DW_DATABASE_URL", "postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_dw")


def _carregar(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, Path(__file__).with_name(arquivo))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def executar_etl(dw_url=DW_URL):
    """Limpa o destino uma vez e executa Salvador, Itabuna, Feira e concorrente."""
    dw = create_engine(dw_url)
    with dw.begin() as conexao:
        conexao.execute(text("TRUNCATE fato_vendas, fato_vendas_concorrente, dim_cliente, dim_produto, dim_geografia, dim_empresa, dim_tempo RESTART IDENTITY CASCADE"))
    cargas = {}
    cargas["ORACLE"] = _carregar("etl_oracle", "2_etl_oracle.py").executar_etl(dw_url=dw_url)
    cargas["POSTGRES"] = _carregar("etl_postgres", "4_etl_postgres.py").executar_etl(dw_url=dw_url)
    cargas["MONGODB"] = _carregar("etl_mongodb", "5_etl_mongodb.py").executar_etl(dw_url=dw_url)
    _carregar("etl_concorrente", "3_etl_concorrente.py").executar_etl(dw_url=dw_url)
    total = sum(cargas.values())
    print(f"ETL principal concluido: {total} itens de vendas proprias; concorrente carregada.")
    return cargas


if __name__ == "__main__":
    executar_etl()
