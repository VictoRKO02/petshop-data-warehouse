# Data Warehouse do Pet Shop

Projeto acadêmico de BI que converte uma base transacional originalmente escrita para Oracle, carrega-a em PostgreSQL e consolida as unidades de Salvador (Oracle convertido), Itabuna (PostgreSQL), Feira de Santana (JSON exportado do MongoDB) e os totais mensais de uma concorrente em um único Data Warehouse dimensional.

## Arquitetura

```text
Salvador/Oracle convertido --\
Itabuna/PostgreSQL -----------+-> ETL principal -> petshop_dw -> consultas OLAP / Power BI
Feira/JSON MongoDB -----------+
planilha concorrente ---------/
```

O grão de `fato_vendas` é um item de uma venda. As dimensões são tempo, produto, cliente, geografia e empresa. A planilha da concorrente contém somente ano, mês e valor total. Por isso, sua fato mensal permite comparar valores, mas não quantidades ou produtos.

## Serviços Docker

O ambiente principal usa uma rede Docker dedicada chamada `petshop-data-warehouse-network`.

- `postgres`: hospeda as bases relacionais e o Data Warehouse.
- `etl`: executa `config/etl_multifonte.py` e acessa o PostgreSQL pelo hostname interno `postgres`.
- `pgadmin`: fornece uma interface web e acessa o PostgreSQL pelo mesmo hostname interno.
- Power BI Desktop: roda na máquina host, portanto não entra diretamente na rede Docker. Ele acessa o banco pela porta publicada em `127.0.0.1`.

### Bancos utilizados

- `petshop_oracle`: origem de Salvador, convertida do modelo Oracle para PostgreSQL.
- `petshop_postgres`: origem PostgreSQL da unidade de Itabuna.
- `petshop_dw`: Data Warehouse dimensional consolidado.

## Pré-requisitos

- Git;
- Docker Desktop iniciado, com Docker Compose v2;
- Python 3.12 e pip no `PATH`, caso seja usado o script de validação;
- Power BI Desktop, apenas para abrir ou atualizar o dashboard opcional.

Não é necessário instalar PostgreSQL, MongoDB ou outro servidor de banco localmente. Os serviços e arquivos necessários são fornecidos pelo projeto.

## Preparação recomendada

Copie o arquivo de exemplo de variáveis de ambiente. As credenciais fornecidas são apenas para desenvolvimento acadêmico e não devem ser reutilizadas em produção.

No macOS ou Linux:

```bash
cp .env.example .env
python -m pip install -r requirements.txt
python scripts/setup_data_warehouse.py
```

No Windows PowerShell:

```powershell
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python scripts/setup_data_warehouse.py
```

O script usa o projeto Compose isolado `dw_petshop_teste`, publica o PostgreSQL em `127.0.0.1:5434`, recria o schema `dw_final` e encerra com as contagens e totais validados. Ele falha com uma mensagem e código de erro se Docker, ETL, PostgreSQL ou alguma validação falhar.

## Execução direta com Docker Compose

Este fluxo carrega o modelo OLAP público e publica o PostgreSQL em `127.0.0.1:5432` por padrão.

### 1. Criar e iniciar PostgreSQL e pgAdmin

```bash
docker compose up -d postgres pgadmin
```

### 2. Conferir o estado dos serviços

```bash
docker compose ps
```

O serviço `postgres` deve aparecer como `healthy`. O `pgadmin` deve aparecer como `running`.

### 3. Executar o ETL

```bash
docker compose run --rm etl
```

Como alternativa, para acompanhar a execução do ETL no processo principal:

```bash
docker compose up --abort-on-container-exit --exit-code-from etl
```

### 4. Consultar o Data Warehouse pelo terminal

A opção recomendada é executar o `psql` dentro do container PostgreSQL já iniciado:

```bash
docker compose exec postgres psql -U pet_user -d petshop_dw
```

A senha acadêmica padrão é `123456`, caso seja solicitada.

Comandos úteis no `psql`:

```sql
\conninfo
\dt
SELECT COUNT(*) FROM fato_vendas;
SELECT banco_origem, COUNT(*)
FROM fato_vendas
GROUP BY banco_origem
ORDER BY banco_origem;
SELECT COUNT(*) FROM fato_vendas_concorrente;
```

Para sair:

```text
\q
```

### 5. Acessar o pgAdmin 4

Abra no navegador:

```text
http://localhost:5050
```

Credenciais padrão da interface:

- E-mail: `admin@petshop.local`
- Senha: `admin`

Depois, cadastre um servidor no pgAdmin com:

- Name: `Petshop DW`
- Host name/address: `postgres`
- Port: `5432`
- Maintenance database: `petshop_dw`
- Username: `pet_user`
- Password: `123456`

O hostname deve ser `postgres`, e não `localhost`, porque o pgAdmin está dentro da mesma rede Docker do banco.

### 6. Acessar pelo Power BI Desktop

O Power BI Desktop roda na máquina host. Use:

- Servidor: `127.0.0.1:5432`
- Banco: `petshop_dw`
- Usuário: `pet_user`
- Senha: `123456`
- Modo: `Importar`

O arquivo do dashboard está em `powerbi/Petshop_Nosso_Aumigo_Dashboard.pbix`.

### 7. Ver logs

```bash
docker compose logs postgres --tail=100
docker compose logs pgadmin --tail=100
docker compose logs etl --tail=100
```

Para acompanhar continuamente:

```bash
docker compose logs -f postgres pgadmin
```

### 8. Parar o ambiente

Preservando os dados:

```bash
docker compose down
```

Removendo containers, rede e volumes persistentes:

```bash
docker compose down -v
```

Use `down -v` quando quiser recriar toda a inicialização do banco a partir de `docker/init`.

## Configuração opcional no `.env`

As portas e credenciais da interface podem ser alteradas sem editar o Compose:

```dotenv
POSTGRES_PORT=5432
PGADMIN_PORT=5050
PGADMIN_DEFAULT_EMAIL=admin@petshop.local
PGADMIN_DEFAULT_PASSWORD=admin
```

Se a porta 5432 já estiver ocupada, use, por exemplo:

```dotenv
POSTGRES_PORT=5433
```

Nesse caso, o Power BI e clientes executados na máquina devem usar `127.0.0.1:5433`. Os containers `etl` e `pgadmin` continuam usando `postgres:5432` dentro da rede Docker.

## Validação completa em ambiente isolado

Para preparar o Compose de teste, executar o ETL, criar o schema `dw_final` e validar contagens e totais financeiros:

```bash
python scripts/setup_data_warehouse.py
```

O comando usa exclusivamente `docker-compose.test.yml`, o projeto Compose `dw_petshop_teste` e a porta local `5434`. Portanto, não reutiliza nem remove containers, volumes ou bancos do ambiente principal.

A conexão do ambiente de teste para o Power BI é:

- Host: `127.0.0.1`
- Porta: `5434`
- Banco: `petshop_dw`
- Usuário: `pet_user`
- Senha: `123456`
- Schema: `dw_final`

## Execução sem Docker

Crie os bancos `petshop_oracle`, `petshop_postgres` e `petshop_dw`. Aplique, na ordem:

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

```sql
SELECT banco_origem, COUNT(*)
FROM fato_vendas
GROUP BY banco_origem
ORDER BY banco_origem;

SELECT COUNT(*) FROM fato_vendas_concorrente;
```

As consultas dos indicadores estão em `data/04_indicadores.sql`.

Para executar os testes de fonte:

```bash
python -m pytest -q
```

Os utilitários opcionais em `scripts/*.sh` exigem Bash. No Windows, execute-os pelo Git Bash. Eles não são necessários para o fluxo principal em Python.

## Solução de problemas

### O hostname `postgres` não é resolvido

Confirme que o banco está ativo:

```bash
docker compose ps
docker compose up -d postgres
```

Para acessar o banco, prefira:

```bash
docker compose exec postgres psql -U pet_user -d petshop_dw
```

O hostname `postgres` só é resolvido entre containers conectados à rede do Compose. Na máquina host, use `127.0.0.1` e a porta publicada.

### O PostgreSQL não fica `healthy`

```bash
docker compose logs postgres --tail=100
```

Se houver dados antigos incompatíveis e eles puderem ser descartados:

```bash
docker compose down -v
docker compose up -d postgres pgadmin
```

### O banco ou usuário não existe

Os scripts em `docker/init` são executados apenas na primeira inicialização de um volume vazio. Recrie os volumes se os arquivos de inicialização foram alterados:

```bash
docker compose down -v
docker compose up -d postgres pgadmin
docker compose run --rm etl
```

### O ETL falhou

```bash
docker compose run --rm etl
```

O comando mantém a saída do ETL visível. Também verifique se o PostgreSQL está saudável com `docker compose ps`.

### A porta já está em uso

Altere `POSTGRES_PORT` ou `PGADMIN_PORT` no `.env` e recrie os serviços:

```bash
docker compose up -d --force-recreate postgres pgadmin
```

### O pgAdmin não conecta usando `localhost`

Dentro do pgAdmin, use `postgres` como host. `localhost` apontaria para o próprio container do pgAdmin.

## Limitação conhecida da fonte concorrente

`08_Vendas_Concorrente.xlsx` possui apenas Ano, Mês e Vendas (R$). Não é tecnicamente possível calcular quantidade ou detalhar por produto e cidade sem receber esses campos da fonte. O projeto não inventa esses dados. O indicador 9 compara apenas os valores por quadrimestre e ano.
