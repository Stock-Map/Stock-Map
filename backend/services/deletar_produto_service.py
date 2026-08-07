from models.produto_model import Produto


class DeletarProdutoService:
    def executar(self, produto_id):
        produto = Produto.buscar_por_id(produto_id)
        if produto is None:
            return False

        # Remocao logica: o produto pode estar referenciado em pedidos antigos.
        produto.desativar()
        return True
