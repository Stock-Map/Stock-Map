from repositories.produto_repository import ProdutoRepository


class ListarProdutosService:
    def executar(self, fornecedor_id=None, busca=None):
        if fornecedor_id in (None, ""):
            fornecedor_id_convertido = None
        else:
            try:
                fornecedor_id_convertido = int(fornecedor_id)
            except (TypeError, ValueError) as erro:
                raise ValueError("O filtro 'fornecedor_id' deve ser um número inteiro.") from erro

        termo = busca.strip() if isinstance(busca, str) and busca.strip() else None

        return ProdutoRepository.buscar_com_status(fornecedor_id_convertido, termo)
