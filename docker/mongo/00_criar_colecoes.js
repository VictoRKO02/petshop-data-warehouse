["categorias", "produtos", "clientes", "vendas", "itens_venda"].forEach((nome) => {
  if (!db.getCollectionNames().includes(nome)) {
    db.createCollection(nome);
  }
});

db.categorias.createIndex({ id_categoria: 1 }, { unique: true });
db.produtos.createIndex({ id_produto: 1 }, { unique: true });
db.clientes.createIndex({ id_cliente: 1 }, { unique: true });
db.vendas.createIndex({ id_venda: 1 }, { unique: true });
db.itens_venda.createIndex({ id_item: 1 }, { unique: true });
