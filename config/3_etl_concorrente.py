"""Carrega os totais mensais disponíveis na planilha da concorrente."""

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


DW_DATABASE_URL = os.getenv(
    "DW_DATABASE_URL",
    "postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_dw",
)
ARQUIVO = Path(__file__).resolve().parent.parent / "data" / "08_Vendas_Concorrente.xlsx"
MESES = {"Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5, "Jun": 6,
         "Jul": 7, "Ago": 8, "Set": 9, "Out": 10, "Nov": 11, "Dez": 12}
NOMES_MESES = {numero: nome.upper() for nome, numero in MESES.items()}


def executar_etl(dw_url=DW_DATABASE_URL, arquivo=ARQUIVO):
    df = pd.read_excel(arquivo)
    colunas = {"Ano", "Mês", "Vendas (R$)"}
    if not colunas.issubset(df.columns):
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(colunas - set(df.columns))}")
    df["mes"] = df["Mês"].map(MESES)
    if df["mes"].isna().any():
        raise ValueError("A planilha contém um mês desconhecido")
    df["data_completa"] = pd.to_datetime(dict(year=df["Ano"], month=df["mes"], day=1))
    df["valor_venda"] = pd.to_numeric(df["Vendas (R$)"], errors="raise")
    if (df["valor_venda"] < 0).any() or df.duplicated(["Ano", "mes"]).any():
        raise ValueError("A planilha contém valor negativo ou mês duplicado")

    dw = create_engine(dw_url)
    with dw.begin() as conexao:
        conexao.execute(text("DELETE FROM fato_vendas_concorrente"))
        conexao.execute(text("DELETE FROM dim_empresa WHERE banco_origem='PLANILHA'"))
        conexao.execute(text("INSERT INTO dim_empresa (id_origem,banco_origem,nome_empresa,tipo_empresa,nome_unidade) VALUES (1,'PLANILHA','Concorrente','CONCORRENTE','NAO INFORMADA')"))
        # Inclui os primeiros dias dos meses caso não existam na venda própria.
        for data in df["data_completa"]:
            conexao.execute(text("INSERT INTO dim_tempo (data_completa,dia,mes,nome_mes,quadrimestre,trimestre,semestre,ano) VALUES (:data,1,:mes,:nome,:quad,:tri,:sem,:ano) ON CONFLICT (data_completa) DO NOTHING"), {
                "data": data.date(), "mes": data.month, "nome": NOMES_MESES[data.month],
                "quad": (data.month-1)//4+1, "tri": (data.month-1)//3+1,
                "sem": (data.month-1)//6+1, "ano": data.year,
            })
    tempo = pd.read_sql("SELECT sk_tempo,data_completa FROM dim_tempo", dw)
    tempo["data_completa"] = pd.to_datetime(tempo["data_completa"])
    empresa = pd.read_sql("SELECT sk_empresa FROM dim_empresa WHERE banco_origem='PLANILHA'", dw).iloc[0, 0]
    carga = df.merge(tempo, on="data_completa", validate="many_to_one")
    carga["sk_empresa"] = empresa
    carga[["sk_tempo", "sk_empresa", "valor_venda"]].to_sql("fato_vendas_concorrente", dw, if_exists="append", index=False)
    print(f"ETL concorrente concluído: {len(carga)} meses carregados. Quantidade/produto não existem na fonte.")


if __name__ == "__main__":
    executar_etl()
