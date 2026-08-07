from models.produto_model import Produto


class BuscarProdutoPorIdService:
    def executar(self, produto_id):
        produto = Produto.buscar_por_id(produto_id)
        if produto is None:
            return None
        return produto.to_dict()
