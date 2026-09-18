-- ============================================================
-- Camada semantica dw_final
--
-- Este script agrega public.fato_vendas (grao de item de venda,
-- unindo Salvador/Oracle, Itabuna/Postgres e Feira/MongoDB) para
-- o grao Tempo x Produto x Estado Civil x Loja, usado pelo
-- dashboard do Power BI.
--
-- Mesmo conteudo usado em scripts/setup_data_warehouse.py
-- (variavel SQL_DW_FINAL), extraido para arquivo proprio e
-- reaplicado tambem no fluxo principal via docker-compose.yml.
-- Mantido consistente entre os dois ambientes de proposito.
-- ============================================================

BEGIN;

DROP SCHEMA IF EXISTS dw_final CASCADE;

CREATE SCHEMA dw_final;


-- ============================================================
-- 1. DIMENSAO TEMPO
-- ============================================================

CREATE TABLE dw_final.dim_tempo (
    pk_tempo BIGSERIAL PRIMARY KEY,
    quadrimestre SMALLINT NOT NULL,
    ano SMALLINT NOT NULL,
    UNIQUE (ano, quadrimestre)
);

INSERT INTO dw_final.dim_tempo (
    quadrimestre,
    ano
)
SELECT DISTINCT
    quadrimestre,
    ano
FROM public.dim_tempo
WHERE quadrimestre IS NOT NULL
  AND ano IS NOT NULL
ORDER BY
    ano,
    quadrimestre;


-- ============================================================
-- 2. DIMENSAO PRODUTO
-- Unifica produtos repetidos entre as fontes
-- ============================================================

CREATE TABLE dw_final.dim_produto (
    pk_produto BIGSERIAL PRIMARY KEY,
    nome_produto VARCHAR(255) NOT NULL,
    categoria VARCHAR(255) NOT NULL
);

INSERT INTO dw_final.dim_produto (
    nome_produto,
    categoria
)
SELECT
    MIN(TRIM(nome_produto)) AS nome_produto,

    COALESCE(
        MIN(TRIM(categoria))
        FILTER (
            WHERE NULLIF(TRIM(categoria), '') IS NOT NULL
              AND UPPER(TRIM(categoria)) <> 'SEM CATEGORIA'
        ),
        'SEM CATEGORIA'
    ) AS categoria

FROM public.dim_produto

WHERE NULLIF(TRIM(nome_produto), '') IS NOT NULL

GROUP BY
    UPPER(TRIM(nome_produto))

ORDER BY
    MIN(TRIM(nome_produto));


-- ============================================================
-- 3. DIMENSAO ESTADO CIVIL
-- ============================================================

CREATE TABLE dw_final.dim_estado_civil (
    pk_estado_civil BIGSERIAL PRIMARY KEY,
    estado_civil VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO dw_final.dim_estado_civil (
    estado_civil
)
SELECT DISTINCT
    COALESCE(
        NULLIF(UPPER(TRIM(estado_civil)), ''),
        'NAO INFORMADO'
    )
FROM public.dim_cliente
ORDER BY 1;


-- ============================================================
-- 4. DIMENSAO LOJA
-- Uma unidade por cidade
-- ============================================================

CREATE TABLE dw_final.dim_loja (
    pk_loja BIGSERIAL PRIMARY KEY,
    nome_loja VARCHAR(150) NOT NULL,
    cidade VARCHAR(100) NOT NULL UNIQUE
);

INSERT INTO dw_final.dim_loja (
    nome_loja,
    cidade
)
SELECT
    MIN(TRIM(g.cidade)) AS nome_loja,
    MIN(TRIM(g.cidade)) AS cidade

FROM public.fato_vendas f

JOIN public.dim_geografia g
    ON f.sk_geografia = g.sk_geografia

WHERE NULLIF(TRIM(g.cidade), '') IS NOT NULL

GROUP BY
    UPPER(TRIM(g.cidade))

ORDER BY
    MIN(TRIM(g.cidade));


-- ============================================================
-- 5. FATO VENDAS
--
-- Granularidade:
-- Tempo x Produto x Estado Civil x Loja
-- ============================================================

CREATE TABLE dw_final.fato_vendas (
    id_vendas BIGSERIAL PRIMARY KEY,

    pk_tempo BIGINT NOT NULL,
    pk_estado_civil BIGINT NOT NULL,
    pk_produto BIGINT NOT NULL,
    pk_loja BIGINT NOT NULL,

    quantidade BIGINT NOT NULL,
    valor_total NUMERIC(18,2) NOT NULL,

    FOREIGN KEY (pk_tempo)
        REFERENCES dw_final.dim_tempo(pk_tempo),

    FOREIGN KEY (pk_estado_civil)
        REFERENCES dw_final.dim_estado_civil(pk_estado_civil),

    FOREIGN KEY (pk_produto)
        REFERENCES dw_final.dim_produto(pk_produto),

    FOREIGN KEY (pk_loja)
        REFERENCES dw_final.dim_loja(pk_loja)
);


INSERT INTO dw_final.fato_vendas (
    pk_tempo,
    pk_estado_civil,
    pk_produto,
    pk_loja,
    quantidade,
    valor_total
)
SELECT
    dt_final.pk_tempo,
    dec.pk_estado_civil,
    dp_final.pk_produto,
    dl.pk_loja,

    SUM(COALESCE(f.quantidade, 0)),
    SUM(COALESCE(f.valor_venda, 0))

FROM public.fato_vendas f


JOIN public.dim_tempo dt_origem
    ON f.sk_tempo = dt_origem.sk_tempo

JOIN dw_final.dim_tempo dt_final
    ON dt_final.ano = dt_origem.ano
   AND dt_final.quadrimestre = dt_origem.quadrimestre


JOIN public.dim_cliente c
    ON f.sk_cliente = c.sk_cliente

JOIN dw_final.dim_estado_civil dec
    ON dec.estado_civil =
       COALESCE(
           NULLIF(UPPER(TRIM(c.estado_civil)), ''),
           'NAO INFORMADO'
       )


JOIN public.dim_produto dp_origem
    ON f.sk_produto = dp_origem.sk_produto

JOIN dw_final.dim_produto dp_final
    ON UPPER(TRIM(dp_origem.nome_produto))
       = UPPER(TRIM(dp_final.nome_produto))


JOIN public.dim_geografia g
    ON f.sk_geografia = g.sk_geografia

JOIN dw_final.dim_loja dl
    ON UPPER(TRIM(g.cidade))
       = UPPER(TRIM(dl.cidade))


GROUP BY
    dt_final.pk_tempo,
    dec.pk_estado_civil,
    dp_final.pk_produto,
    dl.pk_loja;


-- ============================================================
-- 6. FATO CONCORRENTE
-- ============================================================

CREATE TABLE dw_final.fato_concorrente (
    pk_concorrente BIGSERIAL PRIMARY KEY,

    pk_tempo BIGINT NOT NULL,
    valor_venda NUMERIC(18,2) NOT NULL,

    FOREIGN KEY (pk_tempo)
        REFERENCES dw_final.dim_tempo(pk_tempo)
);


INSERT INTO dw_final.fato_concorrente (
    pk_tempo,
    valor_venda
)
SELECT
    dt_final.pk_tempo,
    SUM(COALESCE(fc.valor_venda, 0))

FROM public.fato_vendas_concorrente fc

JOIN public.dim_tempo dt_origem
    ON fc.sk_tempo = dt_origem.sk_tempo

JOIN dw_final.dim_tempo dt_final
    ON dt_final.ano = dt_origem.ano
   AND dt_final.quadrimestre = dt_origem.quadrimestre

GROUP BY
    dt_final.pk_tempo;


-- ============================================================
-- ACESSO DO PET_USER
-- ============================================================

GRANT USAGE
ON SCHEMA dw_final
TO pet_user;

GRANT SELECT
ON ALL TABLES
IN SCHEMA dw_final
TO pet_user;


COMMIT;
