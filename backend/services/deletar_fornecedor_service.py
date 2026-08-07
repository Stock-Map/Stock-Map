from models.fornecedor_model import Fornecedor
from models.produto_model import Produto


class DeletarFornecedorService:
    def executar(self, fornecedor_id):
        fornecedor = Fornecedor.buscar_por_id(fornecedor_id)
        if fornecedor is None:
            return False

        produtos = Produto.query.filter_by(fornecedor_id=fornecedor_id).count()
        if produtos > 0:
            raise ValueError(
                "Não é possível remover um fornecedor que possui produtos cadastrados."
            )

        fornecedor.deletar()
        return True
