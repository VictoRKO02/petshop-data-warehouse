#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p results

views=(
  vw_vendas_produto_categoria vw_vendas_cidade vw_vendas_periodo
  vw_vendas_estado_civil vw_ranking_produtos_quantidade_ano
  vw_ranking_produtos_valor_cidade_ano vw_percentual_produto_periodo
  vw_diferenca_quantidade_anos vw_comparativo_empresa_concorrente
)

for view in "${views[@]}"; do
  docker compose exec -T -e PGPASSWORD=123456 postgres psql \
    -v ON_ERROR_STOP=1 --csv -P footer=off -U pet_user -d petshop_dw \
    -c "SELECT * FROM ${view}" \
    >"results/${view}.csv"
  echo "Exportado: results/${view}.csv"
done
