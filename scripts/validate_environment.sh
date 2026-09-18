#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Iniciando PostgreSQL"
docker compose up -d --wait postgres

echo "==> Executando cargas ETL"
docker compose run --rm etl

echo "==> Validando contagens e integridade financeira"
docker compose exec -T -e PGPASSWORD=123456 postgres psql \
  -v ON_ERROR_STOP=1 -U pet_user -d petshop_dw <<'SQL'
DO $$
DECLARE
    itens BIGINT;
    unidades BIGINT;
    meses BIGINT;
    total_oracle_origem NUMERIC;
    total_oracle_dw NUMERIC;
    total_dw NUMERIC;
BEGIN
    SELECT COUNT(*) INTO itens FROM fato_vendas;
    SELECT COALESCE(SUM(quantidade), 0) INTO unidades FROM fato_vendas;
    SELECT COUNT(*) INTO meses FROM fato_vendas_concorrente;
    IF itens <> 6621 THEN
        RAISE EXCEPTION 'Esperados 6621 itens no DW multifonte, encontrados %', itens;
    END IF;
    IF unidades <> 16482 THEN
        RAISE EXCEPTION 'Esperadas 16482 unidades vendidas no DW multifonte, encontradas %', unidades;
    END IF;
    IF meses <> 24 THEN
        RAISE EXCEPTION 'Esperados 24 meses da concorrente, encontrados %', meses;
    END IF;

    SELECT COALESCE(SUM(valor_venda), 0) INTO total_dw FROM fato_vendas;
    SELECT COALESCE(SUM(valor_venda), 0) INTO total_oracle_dw
    FROM fato_vendas WHERE banco_origem = 'ORACLE';
    SELECT total INTO total_oracle_origem
    FROM dblink(
        'dbname=petshop_oracle user=pet_user password=123456',
        'SELECT SUM(quantidade * valor_unitario) FROM itens_venda'
    ) AS origem(total NUMERIC);
    IF total_oracle_origem <> total_oracle_dw THEN
        RAISE EXCEPTION 'Total Oracle de origem (%) difere do DW (%)', total_oracle_origem, total_oracle_dw;
    END IF;
    RAISE NOTICE 'OK: % linhas detalhadas, % unidades vendidas, % meses concorrente, total consolidado R$ %', itens, unidades, meses, total_dw;
END $$;
SQL

echo "==> Executando consultas OLAP"
docker compose exec -T -e PGPASSWORD=123456 postgres psql \
  -v ON_ERROR_STOP=1 -U pet_user -d petshop_dw \
  -f /projeto/data/04_indicadores.sql >/tmp/indicadores_petshop.log

echo "VALIDAÇÃO CONCLUÍDA. Indicadores: /tmp/indicadores_petshop.log"
