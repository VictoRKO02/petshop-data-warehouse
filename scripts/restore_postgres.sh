#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
origem="${1:?Uso: ./scripts/restore_postgres.sh backups/AAAAmmdd_HHMMSS}"

for arquivo in "$origem/petshop_oracle.dump" "$origem/petshop_dw.dump"; do
  test -s "$arquivo" || { echo "Backup ausente ou vazio: $arquivo" >&2; exit 1; }
done

docker compose up -d --wait postgres
for banco in petshop_oracle petshop_dw; do
  docker compose exec -T -e PGPASSWORD=postgres postgres psql \
    -v ON_ERROR_STOP=1 -U postgres -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${banco}' AND pid <> pg_backend_pid();" \
    -c "DROP DATABASE IF EXISTS ${banco};" \
    -c "CREATE DATABASE ${banco} OWNER pet_user;"
  docker compose exec -T -e PGPASSWORD=123456 postgres pg_restore \
    -v --exit-on-error -U pet_user -d "$banco" <"$origem/${banco}.dump"
  echo "Restaurado: $banco"
done
