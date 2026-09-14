-- 1/2/3/4: produto, categoria, cidade, período e estado civil.
SELECT t.ano, t.quadrimestre, p.categoria, p.nome_produto, g.cidade, c.estado_civil,
       SUM(f.quantidade) quantidade, SUM(f.valor_venda) valor
FROM fato_vendas f JOIN dim_tempo t USING(sk_tempo) JOIN dim_produto p USING(sk_produto)
JOIN dim_geografia g USING(sk_geografia) JOIN dim_cliente c USING(sk_cliente)
GROUP BY t.ano,t.quadrimestre,p.categoria,p.nome_produto,g.cidade,c.estado_civil;

-- 5: ranking anual por quantidade.
SELECT t.ano,p.nome_produto,SUM(f.quantidade) quantidade,
       RANK() OVER(PARTITION BY t.ano ORDER BY SUM(f.quantidade) DESC) ranking
FROM fato_vendas f JOIN dim_tempo t USING(sk_tempo) JOIN dim_produto p USING(sk_produto)
GROUP BY t.ano,p.nome_produto;

-- 6: ranking por valor, cidade e ano.
SELECT t.ano,g.cidade,p.nome_produto,SUM(f.valor_venda) valor,
       RANK() OVER(PARTITION BY t.ano,g.cidade ORDER BY SUM(f.valor_venda) DESC) ranking
FROM fato_vendas f JOIN dim_tempo t USING(sk_tempo) JOIN dim_produto p USING(sk_produto)
JOIN dim_geografia g USING(sk_geografia) GROUP BY t.ano,g.cidade,p.nome_produto;

-- 7: percentual do valor de cada produto no quadrimestre.
SELECT t.ano,t.quadrimestre,p.nome_produto,SUM(f.valor_venda) valor,
       ROUND(100*SUM(f.valor_venda)/SUM(SUM(f.valor_venda)) OVER(PARTITION BY t.ano,t.quadrimestre),2) percentual
FROM fato_vendas f JOIN dim_tempo t USING(sk_tempo) JOIN dim_produto p USING(sk_produto)
GROUP BY t.ano,t.quadrimestre,p.nome_produto;

-- 8: diferença de quantidade contra o ano anterior.
WITH anual AS (SELECT t.ano,p.nome_produto,SUM(f.quantidade) quantidade
 FROM fato_vendas f JOIN dim_tempo t USING(sk_tempo) JOIN dim_produto p USING(sk_produto)
 GROUP BY t.ano,p.nome_produto)
SELECT *,quantidade-LAG(quantidade) OVER(PARTITION BY nome_produto ORDER BY ano) diferenca
FROM anual ORDER BY nome_produto,ano;

-- 9: comparação de valor. A planilha não fornece quantidade nem produto.
WITH propria AS (SELECT t.ano,t.quadrimestre,SUM(f.valor_venda) valor FROM fato_vendas f
 JOIN dim_tempo t USING(sk_tempo) GROUP BY t.ano,t.quadrimestre),
concorrente AS (SELECT t.ano,t.quadrimestre,SUM(f.valor_venda) valor FROM fato_vendas_concorrente f
 JOIN dim_tempo t USING(sk_tempo) GROUP BY t.ano,t.quadrimestre)
SELECT COALESCE(p.ano,c.ano) ano,COALESCE(p.quadrimestre,c.quadrimestre) quadrimestre,
 p.valor valor_propria,c.valor valor_concorrente,p.valor-c.valor diferenca
FROM propria p FULL JOIN concorrente c USING(ano,quadrimestre) ORDER BY ano,quadrimestre;
