# Data Warehouse do Pet Shop

Projeto acadêmico de BI que converte uma base transacional originalmente escrita para Oracle,
carrega-a em PostgreSQL e consolida as unidades de Salvador (Oracle convertido), Itabuna
(PostgreSQL), Feira de Santana (JSON exportado do MongoDB) e os totais mensais de uma concorrente
em um único Data Warehouse dimensional.

## Arquitetura

```text
Salvador/Oracle convertido --\
Itabuna/PostgreSQL -----------+-> ETL principal -> petshop_dw -> consultas OLAP
Feira/JSON MongoDB -----------+
planilha concorrente ---------/
```

O grão de `fato_vendas` é um item de uma venda. As dimensões são tempo, produto, cliente,
geografia e empresa. A planilha da concorrente contém somente ano, mês e valor total; por isso sua
fato mensal permite comparar valores, mas não quantidades ou produtos.

## Pré-requisitos

- Git (para clonar o repositório);
- Docker Desktop iniciado, com Docker Compose v2 disponível;
- Python **3.12** e `pip` no PATH (o script de validação usa o cliente Python para acessar o
  PostgreSQL de teste);
- Power BI Desktop, apenas para abrir ou atualizar o dashboard opcional.

Não é necessário instalar PostgreSQL, MongoDB ou qualquer servidor de banco localmente: eles são
fornecidos pelos containers e pelos arquivos de fonte versionados no projeto.

## Preparação e execução recomendada

Copie o arquivo de exemplo. Os valores fornecidos são credenciais acadêmicas de desenvolvimento,
necessárias para que o ambiente reproduzível funcione; não use credenciais reais neste arquivo.

```bash
copy .env.example .env
python -m pip install -r requirements.txt
python scripts/setup_data_warehouse.py
```

No macOS/Linux, use `cp .env.example .env`. O script usa exclusivamente o projeto Compose
`dw_petshop_teste`, publica PostgreSQL em `127.0.0.1:5434`, recria o schema `dw_final` e encerra
com as contagens e totais validados. Ele falha com uma mensagem e código de erro se Docker, ETL,
PostgreSQL ou uma validação falhar.

## Execução direta com Docker (opcional)

Este fluxo carrega apenas o modelo OLAP público e expõe PostgreSQL em `127.0.0.1:5432`. Para a
entrega e o dashboard, prefira sempre o script isolado da seção anterior.

```bash
docker compose up --abort-on-container-exit --exit-code-from etl
```

Na primeira execução, o Compose cria e popula as origens relacionais, cria o esquema de
`petshop_dw` e executa `config/etl_multifonte.py`. Esse orquestrador limpa o OLAP uma única vez,
carrega todas as lojas no mesmo modelo estrela e, por último, carrega a concorrente. Para recriar
tudo do zero:

```bash
docker compose down -v
docker compose up --abort-on-container-exit --exit-code-from etl
```

Para abrir o PostgreSQL depois da carga:

```bash
docker compose run --rm postgres psql -h postgres -U pet_user -d petshop_dw
```

A senha de desenvolvimento é `123456`. Ela existe apenas para tornar o exercício reproduzível e
deve ser substituída por secrets fora do ambiente acadêmico.

## Validação completa em ambiente isolado

Para preparar o compose de teste, executar o ETL, criar o schema `dw_final` e validar as
contagens e os totais financeiros, execute:

```bash
python scripts/setup_data_warehouse.py
```

O comando usa exclusivamente `docker-compose.test.yml`, o projeto Compose
`dw_petshop_teste` e a porta local `5434`. Portanto, não reutiliza nem remove containers,
volumes ou bancos do ambiente principal.

Copie `.env.example` para `.env` se precisar substituir as conexões e metadados padrão. O
arquivo `.env` é ignorado pelo Git.

## Conexão e Power BI

O arquivo do dashboard está em `powerbi/Petshop_Nosso_Aumigo_Dashboard.pbix` e é rastreável pelo
Git. Abra-o no Power BI Desktop. A conexão do ambiente de teste é:

| Campo | Valor |
|---|---|
| Host | `127.0.0.1` |
| Porta | `5434` |
| Banco | `petshop_dw` |
| Usuário | `pet_user` |
| Senha | `123456` |
| Schema | `dw_final` |

O `.pbix` usa modo **Importar**: ele pode abrir com dados já carregados, mas atualizar os dados
exige que `python scripts/setup_data_warehouse.py` tenha concluído e que o banco de teste esteja
ativo.

## Execução sem Docker

Crie os bancos `petshop_oracle` e `petshop_dw`, aplique na ordem:

1. `data/01_salvador_ddl_postgres.sql` no banco de origem;
2. `data/02_salvador_dml_postgres.sql` no banco de origem;
3. `data/03_petshop_dw_ddl.sql` no DW.

Depois execute:

```bash
python -m pip install -r requirements.txt
export SOURCE_DATABASE_URL='postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_oracle'
export DW_DATABASE_URL='postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_dw'
export POSTGRES_SOURCE_DATABASE_URL='postgresql+psycopg2://pet_user:123456@localhost:5432/petshop_postgres'
python config/etl_multifonte.py
```

## Validação adicional

Após a carga, valide os totais por origem e os 24 meses da concorrente:

```sql
SELECT banco_origem, COUNT(*) FROM fato_vendas GROUP BY banco_origem ORDER BY banco_origem;
SELECT COUNT(*) FROM fato_vendas_concorrente;
```

As consultas para os indicadores do enunciado estão em `data/04_indicadores.sql`.

Para executar os testes de fonte isoladamente após instalar as dependências:

```bash
python -m pytest -q
```

Os utilitários opcionais em `scripts/*.sh` (backup, restauração, exportação e validação
complementar) exigem Bash. No Windows, execute-os pelo **Git Bash**, instalado junto com Git for
Windows; eles não são necessários para o fluxo principal em Python.

## Limitação conhecida da fonte concorrente

`08_Vendas_Concorrente.xlsx` possui apenas `Ano`, `Mês` e `Vendas (R$)`. Não é tecnicamente
possível calcular quantidade ou detalhar por produto/cidade sem receber esses campos da fonte. O
projeto não inventa esses dados: o indicador 9 compara apenas os valores por quadrimestre e ano.
