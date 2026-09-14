-- Camada semântica persistida no PostgreSQL. As views podem ser consultadas pelo
-- Power BI, Metabase, pgAdmin, SQLTools ou psql sem repetir as regras OLAP.

CREATE OR REPLACE VIEW vw_vendas_produto_categoria AS
SELECT f.banco_origem, p.categoria, p.nome_produto,
       SUM(f.quantidade) quantidade, SUM(f.valor_venda) valor
FROM fato_vendas f JOIN dim_produto p USING (sk_produto)
GROUP BY f.banco_origem, p.categoria, p.nome_produto;

CREATE OR REPLACE VIEW vw_vendas_cidade AS
SELECT f.banco_origem, g.cidade, g.estado, g.uf,
       SUM(f.quantidade) quantidade, SUM(f.valor_venda) valor
FROM fato_vendas f JOIN dim_geografia g USING (sk_geografia)
GROUP BY f.banco_origem, g.cidade, g.estado, g.uf;

CREATE OR REPLACE VIEW vw_vendas_periodo AS
SELECT f.banco_origem, t.ano, t.quadrimestre,
       SUM(f.quantidade) quantidade, SUM(f.valor_venda) valor
FROM fato_vendas f JOIN dim_tempo t USING (sk_tempo)
GROUP BY f.banco_origem, t.ano, t.quadrimestre;

CREATE OR REPLACE VIEW vw_vendas_estado_civil AS
SELECT f.banco_origem, c.estado_civil,
       SUM(f.quantidade) quantidade, SUM(f.valor_venda) valor
FROM fato_vendas f JOIN dim_cliente c USING (sk_cliente)
GROUP BY f.banco_origem, c.estado_civil;

CREATE OR REPLACE VIEW vw_ranking_produtos_quantidade_ano AS
SELECT t.ano, f.banco_origem, p.nome_produto, SUM(f.quantidade) quantidade,
       RANK() OVER (PARTITION BY t.ano, f.banco_origem ORDER BY SUM(f.quantidade) DESC) ranking
FROM fato_vendas f JOIN dim_tempo t USING (sk_tempo) JOIN dim_produto p USING (sk_produto)
GROUP BY t.ano, f.banco_origem, p.nome_produto;

CREATE OR REPLACE VIEW vw_ranking_produtos_valor_cidade_ano AS
SELECT t.ano, f.banco_origem, g.cidade, p.nome_produto, SUM(f.valor_venda) valor,
       RANK() OVER (PARTITION BY t.ano, f.banco_origem, g.cidade ORDER BY SUM(f.valor_venda) DESC) ranking
FROM fato_vendas f JOIN dim_tempo t USING (sk_tempo) JOIN dim_produto p USING (sk_produto)
JOIN dim_geografia g USING (sk_geografia)
GROUP BY t.ano, f.banco_origem, g.cidade, p.nome_produto;

CREATE OR REPLACE VIEW vw_percentual_produto_periodo AS
SELECT t.ano, t.quadrimestre, f.banco_origem, p.nome_produto,
       SUM(f.valor_venda) valor,
       ROUND(100 * SUM(f.valor_venda) / SUM(SUM(f.valor_venda)) OVER
             (PARTITION BY t.ano, t.quadrimestre, f.banco_origem), 2) percentual
FROM fato_vendas f JOIN dim_tempo t USING (sk_tempo) JOIN dim_produto p USING (sk_produto)
GROUP BY t.ano, t.quadrimestre, f.banco_origem, p.nome_produto;

CREATE OR REPLACE VIEW vw_diferenca_quantidade_anos AS
WITH anual AS (
    SELECT t.ano, f.banco_origem, p.nome_produto, SUM(f.quantidade) quantidade
    FROM fato_vendas f JOIN dim_tempo t USING (sk_tempo) JOIN dim_produto p USING (sk_produto)
    GROUP BY t.ano, f.banco_origem, p.nome_produto
)
SELECT *, quantidade - LAG(quantidade) OVER
       (PARTITION BY banco_origem, nome_produto ORDER BY ano) diferenca
FROM anual;

CREATE OR REPLACE VIEW vw_comparativo_empresa_concorrente AS
WITH propria AS (
    SELECT t.ano, t.quadrimestre, SUM(f.quantidade) quantidade, SUM(f.valor_venda) valor
    FROM fato_vendas f JOIN dim_tempo t USING (sk_tempo)
    GROUP BY t.ano, t.quadrimestre
), concorrente AS (
    SELECT t.ano, t.quadrimestre, SUM(f.valor_venda) valor
    FROM fato_vendas_concorrente f JOIN dim_tempo t USING (sk_tempo)
    GROUP BY t.ano, t.quadrimestre
)
SELECT COALESCE(p.ano, c.ano) ano,
       COALESCE(p.quadrimestre, c.quadrimestre) quadrimestre,
       p.quantidade quantidade_propria,
       NULL::BIGINT quantidade_concorrente,
       p.valor valor_propria, c.valor valor_concorrente,
       p.valor - c.valor diferenca_valor
FROM propria p FULL JOIN concorrente c USING (ano, quadrimestre);

COMMENT ON COLUMN vw_comparativo_empresa_concorrente.quantidade_concorrente IS
'Indisponível: a planilha concorrente não fornece quantidade, produto ou cidade.';
