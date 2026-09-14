"""Carga dimensional reutilizável das fontes transacionais do pet shop."""

import os
import re
import unicodedata
from datetime import date

import pandas as pd
from sqlalchemy import create_engine, text


SOURCE_DATABASE_URL = os.getenv(
    "SOURCE_DATABASE_URL",
    "postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_oracle",
)
DW_DATABASE_URL = os.getenv(
    "DW_DATABASE_URL",
    "postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_dw",
)
MESES = {1: "JANEIRO", 2: "FEVEREIRO", 3: "MARCO", 4: "ABRIL", 5: "MAIO",
         6: "JUNHO", 7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO",
         10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"}


def normalizar_texto(valor, padrao="NAO INFORMADO"):
    if pd.isna(valor) or not str(valor).strip():
        return padrao
    return re.sub(
        r"\s+", " ",
        unicodedata.normalize("NFKD", str(valor).strip()).encode("ascii", "ignore").decode(),
    )


def normalizar_sexo(valor):
    return {"M": "M", "MASCULINO": "M", "F": "F", "FEMININO": "F"}.get(
        normalizar_texto(valor, "N").upper(), "N"
    )


def normalizar_estado_civil(valor):
    valor = normalizar_texto(valor).upper()
    return {"S": "SOLTEIRO", "C": "CASADO", "D": "DIVORCIADO", "V": "VIUVO",
            "U": "UNIAO ESTAVEL"}.get(valor, valor if valor in {
                "SOLTEIRO", "CASADO", "DIVORCIADO", "VIUVO", "UNIAO ESTAVEL"
            } else "NAO INFORMADO")


def faixa_etaria(data_nascimento, data_referencia):
    """Calcula a idade completa na data de referência e retorna sua faixa."""
    if pd.isna(data_nascimento) or pd.isna(data_referencia):
        return "NAO INFORMADA"
    nascimento, referencia = pd.Timestamp(data_nascimento), pd.Timestamp(data_referencia)
    idade = referencia.year - nascimento.year - (
        (referencia.month, referencia.day) < (nascimento.month, nascimento.day)
    )
    if idade < 18:
        return "MENOR DE 18"
    if idade <= 30:
        return "18 A 30"
    if idade <= 45:
        return "31 A 45"
    if idade <= 60:
        return "46 A 60"
    return "MAIOR DE 60"


def _validar(tabelas):
    obrigatorias = {"clientes", "produtos", "vendas", "itens_venda"}
    faltantes = obrigatorias - set(tabelas)
    if faltantes:
        raise ValueError(f"Tabelas ausentes: {sorted(faltantes)}")
    for nome in obrigatorias:
        if tabelas[nome].empty:
            raise ValueError(f"A tabela {nome} esta vazia")


def executar_etl(source_url=SOURCE_DATABASE_URL, dw_url=DW_DATABASE_URL, *, tabelas=None,
                  banco_origem="ORACLE", nome_empresa="Pet Shop Nosso Aumigo",
                  nome_unidade="Salvador", cidade="Salvador", estado="Bahia", uf="BA",
                  regiao="Nordeste"):
    """Carrega uma origem no modelo estrela sem apagar as demais origens."""
    if tabelas is None:
        source = create_engine(source_url)
        nomes = ("clientes", "produtos", "categorias", "vendas", "itens_venda")
        tabelas = {nome: pd.read_sql(f"SELECT * FROM {nome}", source) for nome in nomes}
    _validar(tabelas)
    banco_origem = banco_origem.upper()
    dw = create_engine(dw_url)

    # A ordem respeita as FKs e torna cada conector idempotente.
    with dw.begin() as conexao:
        conexao.execute(text("DELETE FROM fato_vendas WHERE banco_origem=:origem"), {"origem": banco_origem})
        for tabela in ("dim_cliente", "dim_produto", "dim_geografia", "dim_empresa"):
            conexao.execute(text(f"DELETE FROM {tabela} WHERE banco_origem=:origem"), {"origem": banco_origem})

    produtos = tabelas["produtos"].copy().rename(columns={"id_produto": "id_origem", "nome": "nome_produto"})
    if "categoria" not in produtos and "categorias" in tabelas:
        categorias = tabelas["categorias"].copy().rename(columns={"nome_categoria": "categoria"})
        produtos = produtos.merge(categorias[["id_categoria", "categoria"]], on="id_categoria", how="left")
    if "categoria" not in produtos:
        produtos["categoria"] = "SEM CATEGORIA"
    produtos["categoria"] = produtos["categoria"].fillna("SEM CATEGORIA").map(normalizar_texto)
    produtos["nome_produto"] = produtos["nome_produto"].map(normalizar_texto)
    produtos["banco_origem"], produtos["marca"] = banco_origem, "NAO INFORMADA"
    produtos[["id_origem", "banco_origem", "nome_produto", "categoria", "marca"]].to_sql(
        "dim_produto", dw, if_exists="append", index=False)

    clientes = tabelas["clientes"].copy().rename(columns={"id_cliente": "id_origem", "nome": "nome_cliente"})
    clientes["nome_cliente"] = clientes["nome_cliente"].map(normalizar_texto)
    clientes["sexo"] = clientes["sexo"].map(normalizar_sexo)
    clientes["estado_civil"] = clientes["estado_civil"].map(normalizar_estado_civil)
    clientes["data_nascimento"] = pd.to_datetime(clientes["data_nascimento"], errors="coerce")
    clientes["faixa_etaria"] = clientes["data_nascimento"].map(lambda valor: faixa_etaria(valor, date.today()))
    clientes["banco_origem"] = banco_origem
    clientes[["id_origem", "banco_origem", "nome_cliente", "sexo", "estado_civil",
              "data_nascimento", "faixa_etaria"]].to_sql("dim_cliente", dw, if_exists="append", index=False)

    pd.DataFrame([{"id_origem": 1, "banco_origem": banco_origem, "cidade": cidade,
                   "estado": estado, "uf": uf, "regiao": regiao}]).to_sql(
        "dim_geografia", dw, if_exists="append", index=False)
    pd.DataFrame([{"id_origem": 1, "banco_origem": banco_origem, "nome_empresa": nome_empresa,
                   "tipo_empresa": "PROPRIA", "nome_unidade": nome_unidade}]).to_sql(
        "dim_empresa", dw, if_exists="append", index=False)

    vendas, itens = tabelas["vendas"].copy(), tabelas["itens_venda"].copy()
    vendas["data_venda"] = pd.to_datetime(vendas["data_venda"], errors="raise").dt.normalize()
    datas = vendas["data_venda"].drop_duplicates().sort_values()
    tempo = pd.DataFrame({"data_completa": datas})
    tempo["dia"], tempo["mes"] = tempo.data_completa.dt.day, tempo.data_completa.dt.month
    tempo["nome_mes"] = tempo.mes.map(MESES)
    tempo["quadrimestre"] = (tempo.mes - 1) // 4 + 1
    tempo["trimestre"] = (tempo.mes - 1) // 3 + 1
    tempo["semestre"] = (tempo.mes - 1) // 6 + 1
    tempo["ano"] = tempo.data_completa.dt.year
    existentes = pd.read_sql("SELECT data_completa FROM dim_tempo", dw)
    if not existentes.empty:
        tempo = tempo[~tempo.data_completa.isin(pd.to_datetime(existentes.data_completa))]
    tempo.to_sql("dim_tempo", dw, if_exists="append", index=False)

    produto_dw = pd.read_sql(text("SELECT sk_produto,id_origem FROM dim_produto WHERE banco_origem=:o"), dw, params={"o": banco_origem})
    cliente_dw = pd.read_sql(text("SELECT sk_cliente,id_origem,data_nascimento FROM dim_cliente WHERE banco_origem=:o"), dw, params={"o": banco_origem})
    tempo_dw = pd.read_sql("SELECT sk_tempo,data_completa FROM dim_tempo", dw)
    constantes = pd.read_sql(text(
        "SELECT (SELECT sk_geografia FROM dim_geografia WHERE banco_origem=:o) sk_geografia, "
        "(SELECT sk_empresa FROM dim_empresa WHERE banco_origem=:o) sk_empresa"), dw, params={"o": banco_origem}).iloc[0]
    total_itens = len(itens)
    fato = itens.merge(vendas, on="id_venda", validate="many_to_one")
    fato = fato.merge(produto_dw, left_on="id_produto", right_on="id_origem", validate="many_to_one")
    fato = fato.merge(cliente_dw, left_on="id_cliente", right_on="id_origem", validate="many_to_one")
    tempo_dw["data_completa"] = pd.to_datetime(tempo_dw.data_completa)
    fato = fato.merge(tempo_dw, left_on="data_venda", right_on="data_completa", validate="many_to_one")
    if len(fato) != total_itens:
        raise ValueError(
            f"A origem {banco_origem} possui itens sem venda, produto, cliente ou data correspondente"
        )
    fato["quantidade"] = pd.to_numeric(fato.quantidade, errors="raise").astype(int)
    fato["valor_unitario"] = pd.to_numeric(fato.valor_unitario, errors="raise")
    if (fato.quantidade <= 0).any() or (fato.valor_unitario < 0).any():
        raise ValueError(f"Quantidade ou valor invalido na origem {banco_origem}")
    fato["valor_venda"] = fato.quantidade * fato.valor_unitario
    fato["faixa_etaria_venda"] = fato.apply(lambda x: faixa_etaria(x.data_nascimento, x.data_venda), axis=1)
    carga = pd.DataFrame({"id_venda_origem": fato.id_venda, "id_item_origem": fato.id_item,
        "banco_origem": banco_origem, "sk_tempo": fato.sk_tempo, "sk_produto": fato.sk_produto,
        "sk_cliente": fato.sk_cliente, "sk_geografia": constantes.sk_geografia,
        "sk_empresa": constantes.sk_empresa, "quantidade": fato.quantidade,
        "valor_unitario": fato.valor_unitario, "valor_venda": fato.valor_venda,
        "faixa_etaria_venda": fato.faixa_etaria_venda})
    carga.to_sql("fato_vendas", dw, if_exists="append", index=False)
    print(f"ETL {banco_origem} concluido: {len(carga)} itens carregados.")
    return len(carga)


if __name__ == "__main__":
    executar_etl()
