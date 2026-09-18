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

A unidade de Feira de Santana não usa um serviço MongoDB em execução: `config/5_etl_mongodb.py` lê diretamente os arquivos JSON exportados em `data/05_Feira_Clientes.json`, `data/06_Feira_Produtos.json` e `data/07_Feira_pedidos.json`. O arquivo `docker/mongo/00_criar_colecoes.js` é mantido apenas como referência histórica de como as coleções foram originalmente estruturadas no MongoDB e não é executado pelo `docker-compose.yml`.

## Pré-requisitos

- Git;
- Docker Desktop iniciado, com Docker Compose v2;
- Python 3.12 e pip no `PATH`, caso seja usado o script de validação;
- Power BI Desktop, apenas para abrir ou atualizar o dashboard opcional. Disponível somente para Windows (ver seção [Power BI e Docker](#power-bi-e-docker)).

Não é necessário instalar PostgreSQL, MongoDB ou outro servidor de banco localmente. Os serviços e arquivos necessários são fornecidos pelo projeto.

### Observação para usuários de Windows

O repositório inclui um arquivo `.gitattributes` que força o uso de quebras de linha `LF` para scripts (`.sh`, `.py`, `.sql`, `.js`, `.yml`, `.json`). Isso é necessário porque os scripts de inicialização em `docker/init` são executados dentro de containers Linux; se o Git clonar esses arquivos com `CRLF` (comportamento padrão do Git for Windows quando a opção `core.autocrlf` está definida como `true`), o PostgreSQL falha silenciosamente ao processá-los na primeira inicialização.

Caso o ambiente já tenha sido clonado antes dessa correção, ou caso o Git local esteja configurado com `core.autocrlf=true` e o `.gitattributes` não seja respeitado por algum motivo, normalize manualmente o repositório após atualizar:

```powershell
git rm --cached -r .
git reset --hard
```

Recomenda-se também Docker Desktop configurado com o backend WSL2, que é o padrão em instalações recentes e evita problemas de desempenho de I/O em bind mounts no Windows.

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

O script usa o projeto Compose isolado `dw_petshop_teste`, definido em `docker-compose.test.yml` (versionado no repositório, publicando o PostgreSQL em `127.0.0.1:5434`), recria o schema `dw_final` e encerra com as contagens e totais validados. Ele falha com uma mensagem e código de erro se Docker, ETL, PostgreSQL ou alguma validação falhar.

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

Esse mesmo comando executa, em sequência, `config/etl_multifonte.py` (carga
das camadas `public.*`) e `scripts/aplicar_dw_final.py` (recriação do schema
`dw_final` a partir de `data/06_dw_final_ddl_dml.sql`). Portanto, ao final da
execução, tanto `public.fato_vendas` quanto `dw_final.fato_vendas` já estarão
disponíveis no mesmo banco `petshop_dw`, na porta `5432`.

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
-- Camada detalhada: uma linha por item de venda (6621 linhas esperadas).
SELECT COUNT(*) FROM public.fato_vendas;
SELECT SUM(quantidade) AS itens_vendidos FROM public.fato_vendas;
SELECT banco_origem, COUNT(*)
FROM public.fato_vendas
GROUP BY banco_origem
ORDER BY banco_origem;
SELECT COUNT(*) FROM public.fato_vendas_concorrente;

-- Camada semântica do dashboard (1382 linhas e 16482 unidades esperadas).
SELECT COUNT(*) FROM dw_final.fato_vendas;
SELECT SUM(quantidade) AS itens_vendidos FROM dw_final.fato_vendas;
```

`public.fato_vendas` preserva cada item das três fontes e, por isso, tem 6621 linhas. Para o
dashboard, use `dw_final.fato_vendas`, agregada por Tempo x Produto x Estado Civil x Loja: ela
possui 1382 combinações e deve somar 16482 unidades. Contar linhas detalhadas ou aplicar filtros
de uma única fonte não representa o total analítico consolidado.

O schema `dw_final` já é criado automaticamente pelo `docker compose run --rm etl` (ver seção
anterior). Caso ele precise ser recriado manualmente sem rodar o ETL completo novamente — por
exemplo, após alterar apenas `data/06_dw_final_ddl_dml.sql` —, execute dentro do container `etl`:

```bash
docker compose run --rm etl python scripts/aplicar_dw_final.py
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

O servidor `Petshop PostgreSQL (Docker)` já vem pré-cadastrado automaticamente a partir de `docker/pgadmin/servers.json`, montado no container. Ao expandir o servidor pela primeira vez, o pgAdmin solicitará apenas a senha (por segurança, a senha nunca é armazenada nesse arquivo):

- Password: `123456`

Caso seja necessário cadastrar o servidor manualmente (por exemplo, após limpar o volume `pgadmin_data`), use:

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

#### Power BI e Docker

O Power BI Desktop não é suportado oficialmente pela Microsoft em containers Docker ou em Linux; é um aplicativo nativo do Windows. Por isso, ele não faz parte dos serviços do `docker-compose.yml` e continua sendo executado diretamente na máquina host, apenas se conectando ao PostgreSQL que roda em container pela porta publicada em `127.0.0.1`. Essa arquitetura já é a forma correta e suportada de integrar as duas ferramentas, e não há necessidade (nem possibilidade prática) de rodar o Power BI Desktop dentro de um container.

Se o ambiente de desenvolvimento for Linux (por exemplo, Ubuntu) e não houver acesso a uma máquina Windows, os únicos caminhos possíveis são:

- Usar o [Power BI Service](https://app.powerbi.com) (a versão web/nuvem), que roda no navegador e é compatível com Linux, publicando o `.pbix` a partir de uma máquina Windows e depois configurando um gateway de dados; ou
- Rodar o Power BI Desktop dentro de uma máquina virtual Windows.

Em ambos os casos, o Data Warehouse em si (PostgreSQL, ETL e pgAdmin) continua funcionando normalmente em Docker no Ubuntu, independentemente de onde o Power BI seja aberto.

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
python scripts/aplicar_dw_final.py
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

### No Windows, o PostgreSQL falha na inicialização ou os bancos `pet_user` não são criados

Esse sintoma costuma indicar que os scripts de `docker/init` foram clonados com quebras de linha `CRLF` em vez de `LF`. Confirme se o `.gitattributes` do repositório foi respeitado:

```powershell
git config core.autocrlf
```

Se o valor retornado for `true`, ajuste para não converter automaticamente e reclone o repositório (ou normalize os arquivos existentes conforme a seção [Observação para usuários de Windows](#observação-para-usuários-de-windows)):

```powershell
git config --global core.autocrlf input
```

Depois, recrie os volumes para que os scripts de inicialização sejam executados novamente:

```powershell
docker compose down -v
docker compose up -d postgres pgadmin
```

## Limitação conhecida da fonte concorrente

`08_Vendas_Concorrente.xlsx` possui apenas Ano, Mês e Vendas (R$). Não é tecnicamente possível calcular quantidade ou detalhar por produto e cidade sem receber esses campos da fonte. O projeto não inventa esses dados. O indicador 9 compara apenas os valores por quadrimestre e ano.