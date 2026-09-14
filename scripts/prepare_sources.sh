#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose up -d --wait postgres

existe="$(docker compose exec -T postgres psql -U postgres -d postgres -At \
  -c "SELECT 1 FROM pg_database WHERE datname='petshop_postgres'")"
if [[ "$existe" != "1" ]]; then
  docker compose exec -T postgres createdb -U postgres -O pet_user petshop_postgres
  docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U pet_user \
    -d petshop_postgres -f /projeto/data/01_salvador_ddl_postgres.sql
  echo "Origem petshop_postgres criada."
fi

for arquivo in \
  data/05_Feira_Clientes.json \
  data/06_Feira_Produtos.json \
  data/07_Feira_pedidos.json; do
  test -s "$arquivo" || { echo "Fonte JSON ausente ou vazia: $arquivo" >&2; exit 1; }
done

echo "Fontes PostgreSQL e JSON prontas. A fonte Feira é lida diretamente dos arquivos JSON pelo ETL."
