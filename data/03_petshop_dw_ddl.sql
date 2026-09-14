CREATE TABLE dim_tempo (
    sk_tempo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data_completa DATE NOT NULL UNIQUE, dia SMALLINT NOT NULL, mes SMALLINT NOT NULL,
    nome_mes VARCHAR(15) NOT NULL, quadrimestre SMALLINT NOT NULL,
    trimestre SMALLINT NOT NULL, semestre SMALLINT NOT NULL, ano SMALLINT NOT NULL,
    CHECK (mes BETWEEN 1 AND 12), CHECK (quadrimestre BETWEEN 1 AND 3)
);
CREATE TABLE dim_produto (
    sk_produto BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_origem INT NOT NULL, banco_origem VARCHAR(30) NOT NULL,
    nome_produto VARCHAR(100) NOT NULL, categoria VARCHAR(100) NOT NULL, marca VARCHAR(100),
    UNIQUE (banco_origem, id_origem)
);
CREATE TABLE dim_cliente (
    sk_cliente BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_origem INT NOT NULL, banco_origem VARCHAR(30) NOT NULL,
    nome_cliente VARCHAR(100) NOT NULL, sexo CHAR(1), estado_civil VARCHAR(30) NOT NULL,
    data_nascimento DATE, faixa_etaria VARCHAR(30), UNIQUE (banco_origem, id_origem)
);
CREATE TABLE dim_geografia (
    sk_geografia BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_origem INT NOT NULL, banco_origem VARCHAR(30) NOT NULL, cidade VARCHAR(100) NOT NULL,
    estado VARCHAR(100) NOT NULL, uf CHAR(2) NOT NULL, regiao VARCHAR(30),
    UNIQUE (banco_origem, id_origem)
);
CREATE TABLE dim_empresa (
    sk_empresa BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_origem INT NOT NULL, banco_origem VARCHAR(30) NOT NULL,
    nome_empresa VARCHAR(150) NOT NULL, tipo_empresa VARCHAR(20) NOT NULL,
    nome_unidade VARCHAR(100), UNIQUE (banco_origem, id_origem)
);
CREATE TABLE fato_vendas (
    sk_venda BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_venda_origem INT NOT NULL, id_item_origem INT NOT NULL, banco_origem VARCHAR(30) NOT NULL,
    sk_tempo BIGINT NOT NULL REFERENCES dim_tempo, sk_produto BIGINT NOT NULL REFERENCES dim_produto,
    sk_cliente BIGINT NOT NULL REFERENCES dim_cliente, sk_geografia BIGINT NOT NULL REFERENCES dim_geografia,
    sk_empresa BIGINT NOT NULL REFERENCES dim_empresa, quantidade INT NOT NULL CHECK (quantidade > 0),
    valor_unitario NUMERIC(12,2) NOT NULL CHECK (valor_unitario >= 0),
    valor_venda NUMERIC(14,2) NOT NULL CHECK (valor_venda >= 0), faixa_etaria_venda VARCHAR(30),
    UNIQUE (banco_origem, id_item_origem)
);
CREATE TABLE fato_vendas_concorrente (
    sk_concorrente BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sk_tempo BIGINT NOT NULL REFERENCES dim_tempo, sk_empresa BIGINT NOT NULL REFERENCES dim_empresa,
    valor_venda NUMERIC(14,2) NOT NULL CHECK (valor_venda >= 0), UNIQUE (sk_tempo, sk_empresa)
);
CREATE INDEX ix_fato_vendas_tempo ON fato_vendas(sk_tempo);
CREATE INDEX ix_fato_vendas_produto ON fato_vendas(sk_produto);
CREATE INDEX ix_fato_vendas_geografia ON fato_vendas(sk_geografia);
