from models.fornecedor_model import Fornecedor
from models.produto_model import Produto


class AtualizarProdutoService:
    def executar(self, produto_id, dados):
        produto = Produto.buscar_por_id(produto_id)
        if produto is None:
            return None

        fornecedor_id = produto.fornecedor_id
        if dados.get("fornecedor_id") not in (None, ""):
            fornecedor_id = int(dados["fornecedor_id"])
            if Fornecedor.buscar_por_id(fornecedor_id) is None:
                raise ValueError("Fornecedor não encontrado.")

        novo_sku = dados.get("sku") or produto.sku
        existente = Produto.buscar_por_sku(fornecedor_id, novo_sku)
        if existente and existente.id != produto.id:
            raise ValueError("Já existe um produto com este SKU para o fornecedor.")

        produto.atualizar(
            fornecedor_id=fornecedor_id,
            sku=dados.get("sku"),
            nome=dados.get("nome"),
            categoria=dados.get("categoria"),
            preco_unitario=dados.get("preco_unitario"),
            estoque_minimo=dados.get("estoque_minimo"),
            prazo_entrega_dias=dados.get("prazo_entrega_dias"),
            ativo=dados.get("ativo"),
        )
        return produto.to_dict()
