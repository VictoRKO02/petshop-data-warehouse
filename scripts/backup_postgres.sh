#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
destino="${1:-backups/$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$destino"
docker compose up -d --wait postgres

for banco in petshop_oracle petshop_dw; do
  docker compose exec -T -e PGPASSWORD=123456 postgres pg_dump \
    -U pet_user -d "$banco" --format=custom --no-owner --no-acl \
    >"$destino/${banco}.dump"
  test -s "$destino/${banco}.dump"
  echo "Backup criado: $destino/${banco}.dump"
done

echo "Copie a pasta '$destino' para restaurar os dois bancos em outro computador."
