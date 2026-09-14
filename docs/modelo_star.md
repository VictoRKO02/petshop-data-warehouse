# Modelo dimensional final

## Grão

Uma linha de `fato_vendas` representa **um item de produto de uma venda**. A concorrente possui
grão mensal porque sua planilha não oferece transações individuais.

```mermaid
erDiagram
    DIM_TEMPO ||--o{ FATO_VENDAS : periodo
    DIM_PRODUTO ||--o{ FATO_VENDAS : produto
    DIM_CLIENTE ||--o{ FATO_VENDAS : cliente
    DIM_GEOGRAFIA ||--o{ FATO_VENDAS : local
    DIM_EMPRESA ||--o{ FATO_VENDAS : empresa
    DIM_TEMPO ||--o{ FATO_VENDAS_CONCORRENTE : periodo
    DIM_EMPRESA ||--o{ FATO_VENDAS_CONCORRENTE : concorrente

    DIM_TEMPO {
      bigint sk_tempo PK
      date data_completa
      smallint quadrimestre
      smallint ano
    }
    DIM_PRODUTO {
      bigint sk_produto PK
      int id_origem
      varchar banco_origem
      varchar nome_produto
      varchar categoria
    }
    DIM_CLIENTE {
      bigint sk_cliente PK
      int id_origem
      varchar banco_origem
      varchar estado_civil
      varchar faixa_etaria
    }
    DIM_GEOGRAFIA {
      bigint sk_geografia PK
      int id_origem
      varchar banco_origem
      varchar cidade
      char uf
    }
    DIM_EMPRESA {
      bigint sk_empresa PK
      int id_origem
      varchar banco_origem
      varchar nome_empresa
      varchar tipo_empresa
    }
    FATO_VENDAS {
      bigint sk_venda PK
      varchar banco_origem
      bigint sk_tempo FK
      bigint sk_produto FK
      bigint sk_cliente FK
      bigint sk_geografia FK
      bigint sk_empresa FK
      int quantidade
      numeric valor_venda
    }
    FATO_VENDAS_CONCORRENTE {
      bigint sk_concorrente PK
      bigint sk_tempo FK
      bigint sk_empresa FK
      numeric valor_venda
    }
```

## Rastreabilidade da origem

`dim_produto`, `dim_cliente`, `dim_geografia` e `dim_empresa` possuem `id_origem` e
`banco_origem`. `fato_vendas` também registra `banco_origem`. `dim_tempo` é uma dimensão
conformada e compartilhada: datas não pertencem a um banco específico. Na concorrente, a origem
`PLANILHA` fica em `dim_empresa`; na empresa própria, a origem é `ORACLE` (a base Oracle foi
simulada no PostgreSQL `petshop_oracle`).

