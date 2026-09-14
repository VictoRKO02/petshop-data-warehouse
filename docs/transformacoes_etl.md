# Transformações do ETL

## Extração

- A origem própria lê `clientes`, `produtos`, `categorias`, `vendas` e `itens_venda` de
  `petshop_oracle`.
- A origem concorrente lê `data/08_Vendas_Concorrente.xlsx`.
- As URLs de origem e destino são separadas por `SOURCE_DATABASE_URL` e `DW_DATABASE_URL`.

## Transformação e qualidade

| Regra | Aplicação |
|---|---|
| Oracle → PostgreSQL | `VARCHAR2` vira `VARCHAR`, `SYSDATE` vira `CURRENT_DATE` e `TO_DATE` vira data ISO. |
| Categoria ausente | Substituída por `SEM CATEGORIA`. |
| Marca ausente | Substituída por `NAO INFORMADA`. |
| Estado civil | S/C/D/V/U viram SOLTEIRO/CASADO/DIVORCIADO/VIUVO/UNIAO ESTAVEL. |
| Faixa etária | Calculada com aniversário completo; a fato preserva a faixa na data da venda. |
| Tempo | Deriva dia, mês, trimestre, quadrimestre, semestre e ano. |
| Valor da venda | `quantidade × valor_unitario`. |
| Chaves | IDs naturais são mapeados para surrogate keys das dimensões. |
| Linhagem | `id_origem` e `banco_origem` identificam o registro de origem. |
| Reexecução | A carga completa trunca os fatos/dimensões antes de recarregar, evitando duplicidade. |
| Concorrente | Valida colunas, meses, valores negativos e duplicidade de mês. |

## Carga

O grão próprio é o item da venda, identificado por `(banco_origem, id_item_origem)`. A carga da
concorrente associa cada total mensal às dimensões tempo e empresa. Ela não é artificialmente
detalhada, pois a fonte não contém produto, quantidade, cliente ou cidade.
