# Fontes PostgreSQL e MongoDB

O ambiente consolida `petshop_oracle` (Salvador), `petshop_postgres` (Itabuna), os arquivos JSON
exportados por Feira de Santana e a planilha da concorrente. Execute apenas
`python config/etl_multifonte.py` para fazer a carga completa e idempotente no OLAP.

## Contrato da origem PostgreSQL

As tabelas devem seguir o DDL `data/01_salvador_ddl_postgres.sql`. Importe o DML real da unidade
em `petshop_postgres` e execute `python config/4_etl_postgres.py` no serviço ETL. Configure cidade,
UF e unidade pelas variáveis `POSTGRES_CIDADE`, `POSTGRES_UF` e `POSTGRES_NOME_UNIDADE`.

## Contrato da origem MongoDB

Os arquivos `05_Feira_Clientes.json`, `06_Feira_Produtos.json` e `07_Feira_pedidos.json` são a
exportação corrigida da origem MongoDB. O conector transforma os pedidos aninhados em vendas e
itens antes de chamar a mesma carga dimensional utilizada pelas fontes relacionais.

Os scripts numerados ainda podem ser executados isoladamente para recarregar somente uma origem,
sem remover os dados das demais. A execução oficial, porém, é sempre o orquestrador multifonte.
