from models.fornecedor_model import Fornecedor


class BuscarFornecedorPorIdService:
    def executar(self, fornecedor_id):
        fornecedor = Fornecedor.buscar_por_id(fornecedor_id)
        if fornecedor is None:
            return None
        return fornecedor.to_dict()
