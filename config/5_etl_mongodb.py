"""Conector dos JSON exportados pela unidade Feira de Santana para o DW."""
import importlib.util
import json
import os
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DW_URL = os.getenv("DW_DATABASE_URL", "postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_dw")
ARQUIVOS = {"clientes": RAIZ / "data/05_Feira_Clientes.json", "produtos": RAIZ / "data/06_Feira_Produtos.json", "pedidos": RAIZ / "data/07_Feira_pedidos.json"}


def _executor():
    caminho = Path(__file__).with_name("2_etl_oracle.py")
    spec = importlib.util.spec_from_file_location("etl_dimensional", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.executar_etl


def extrair_json(arquivos=ARQUIVOS):
    dados = {nome: json.loads(Path(caminho).read_text(encoding="utf-8")) for nome, caminho in arquivos.items()}
    clientes, produtos, vendas, itens = pd.DataFrame(dados["clientes"]), pd.DataFrame(dados["produtos"]), [], []
    for pedido in dados["pedidos"]:
        vendas.append({"id_venda": pedido["id_pedido"], "id_cliente": pedido["id_cliente"], "data_venda": pedido["data_pedido"]})
        for numero, item in enumerate(pedido.get("itens", []), 1):
            itens.append({"id_item": pedido["id_pedido"] * 1000 + numero, "id_venda": pedido["id_pedido"],
                          "id_produto": item["id_produto"], "quantidade": item["quantidade"],
                          "valor_unitario": item["preco_unitario"]})
    return {"clientes": clientes, "produtos": produtos, "vendas": pd.DataFrame(vendas), "itens_venda": pd.DataFrame(itens)}


def executar_etl(dw_url=DW_URL, arquivos=ARQUIVOS):
    tabelas = extrair_json(arquivos)
    return _executor()(dw_url=dw_url, tabelas=tabelas, banco_origem="MONGODB",
        nome_empresa="Pet Shop Nosso Aumigo", nome_unidade="Feira de Santana",
        cidade="Feira de Santana", estado="Bahia", uf="BA", regiao="Nordeste")


if __name__ == "__main__":
    executar_etl()
