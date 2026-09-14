#!/bin/bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<SQL
CREATE USER pet_user WITH PASSWORD '123456';
CREATE DATABASE petshop_oracle OWNER pet_user;
CREATE DATABASE petshop_postgres OWNER pet_user;
CREATE DATABASE petshop_dw OWNER pet_user;
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname petshop_dw \
  -c "CREATE EXTENSION IF NOT EXISTS dblink;"

psql -v ON_ERROR_STOP=1 --username pet_user --dbname petshop_oracle -f /projeto/data/01_salvador_ddl_postgres.sql
psql -v ON_ERROR_STOP=1 --username pet_user --dbname petshop_oracle -f /projeto/data/02_salvador_dml_postgres.sql

psql -v ON_ERROR_STOP=1 --username pet_user --dbname petshop_postgres -f /projeto/data/03_Itabuna_ddl.sql
psql -v ON_ERROR_STOP=1 --username pet_user --dbname petshop_postgres -f /projeto/data/04_itabuna_dml.sql

psql -v ON_ERROR_STOP=1 --username pet_user --dbname petshop_dw -f /projeto/data/03_petshop_dw_ddl.sql
