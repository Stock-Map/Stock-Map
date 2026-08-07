from models.fornecedor_model import Fornecedor


class ListarFornecedoresService:
    def executar(self):
        fornecedores = Fornecedor.listar_todos()
        return [fornecedor.to_dict() for fornecedor in fornecedores]
