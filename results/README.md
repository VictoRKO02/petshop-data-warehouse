# Resultados exportados

Execute `./scripts/export_results.sh` depois do ETL. Esta pasta receberá nove arquivos CSV,
um para cada view gerencial. Os CSVs presentes nesta entrega são referências reproduzíveis da
carga validada; gere-os novamente depois de alterar as fontes antes de usá-los no Excel/Power BI.

As views exportadas pertencem à camada detalhada `public` e servem para auditoria por origem.
Para os cartões consolidados do dashboard, conecte-se ao schema `dw_final` e use
`dw_final.fato_vendas`: `COUNT(*) = 1382` e `SUM(quantidade) = 16482`.
