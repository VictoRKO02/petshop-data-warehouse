import importlib.util
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


RAIZ = Path(__file__).resolve().parent.parent


class TestFontes(unittest.TestCase):
    def test_contrato_do_dw_final(self):
        caminho = RAIZ / "scripts" / "setup_data_warehouse.py"
        spec = importlib.util.spec_from_file_location("setup_dw", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)

        for tabela in (
            "dw_final.dim_tempo",
            "dw_final.dim_produto",
            "dw_final.dim_estado_civil",
            "dw_final.dim_loja",
            "dw_final.fato_vendas",
            "dw_final.fato_concorrente",
        ):
            self.assertIn(tabela, modulo.SQL_DW_FINAL)

        self.assertIn("UPPER(TRIM(nome_produto))", modulo.SQL_DW_FINAL)
        self.assertIn("<> 'SEM CATEGORIA'", modulo.SQL_DW_FINAL)
        self.assertNotIn("sk_empresa", modulo.SQL_DW_FINAL)
        self.assertEqual(
            {
                "dim_tempo": 6,
                "dim_produto": 17,
                "dim_estado_civil": 6,
                "dim_loja": 3,
                "fato_vendas": 1382,
                "fato_concorrente": 6,
            },
            modulo.EXPECTED_COUNTS,
        )

    def test_compose_de_teste_usa_porta_isolada(self):
        compose = (RAIZ / "docker-compose.test.yml").read_text(encoding="utf-8")
        self.assertIn('"5434:5432"', compose)
        self.assertIn("python config/etl_multifonte.py", compose)

    def test_inicializacao_habilita_validacao_entre_bancos(self):
        init = (RAIZ / "docker" / "init" / "00_criar_bancos.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("CREATE EXTENSION IF NOT EXISTS dblink", init)

    def test_validacao_multifonte_usa_total_oracle_correspondente(self):
        validacao = (RAIZ / "scripts" / "validate_environment.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("IF itens <> 6621", validacao)
        self.assertIn("WHERE banco_origem = 'ORACLE'", validacao)

    def test_quantidades_da_origem(self):
        sql = (RAIZ / "data" / "02_salvador_dml_postgres.sql").read_text()
        esperado = {"categorias": 8, "produtos": 17, "clientes": 200,
                    "vendas": 900, "itens_venda": 3166}
        obtido = {tabela: len(re.findall(rf"INSERT INTO {tabela}\b", sql, re.I))
                  for tabela in esperado}
        self.assertEqual(esperado, obtido)

    def test_conversor_oracle_postgres(self):
        caminho = RAIZ / "config" / "1_converter_oracle_p_postgre.py"
        spec = importlib.util.spec_from_file_location("conversor", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        convertido = modulo.converter_oracle_para_postgres(
            "VARCHAR2(10) DEFAULT SYSDATE; TO_DATE('22/08/2026','DD/MM/YYYY')"
        )
        self.assertEqual(
            "VARCHAR(10) DEFAULT CURRENT_DATE; '2026-08-22'", convertido
        )

    def test_planilha_tem_24_meses(self):
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        with ZipFile(RAIZ / "data" / "08_Vendas_Concorrente.xlsx") as arquivo:
            planilha = ElementTree.fromstring(arquivo.read("xl/worksheets/sheet1.xml"))
        linhas = planilha.findall(".//m:row", ns)
        self.assertEqual(25, len(linhas))  # cabeçalho + 24 meses

    def test_exportacao_feira_e_transformada_em_tabelas(self):
        caminho = RAIZ / "config" / "5_etl_mongodb.py"
        spec = importlib.util.spec_from_file_location("etl_feira", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        tabelas = modulo.extrair_json()
        self.assertEqual(130, len(tabelas["clientes"]))
        self.assertEqual(15, len(tabelas["produtos"]))
        self.assertEqual(500, len(tabelas["vendas"]))
        self.assertGreater(len(tabelas["itens_venda"]), 500)
        self.assertFalse(tabelas["itens_venda"]["id_item"].duplicated().any())

    def test_normalizacao_das_fontes(self):
        caminho = RAIZ / "config" / "2_etl_oracle.py"
        spec = importlib.util.spec_from_file_location("etl_dimensional", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        self.assertEqual("F", modulo.normalizar_sexo("Feminino"))
        self.assertEqual("UNIAO ESTAVEL", modulo.normalizar_estado_civil("União Estável"))


if __name__ == "__main__":
    unittest.main()
