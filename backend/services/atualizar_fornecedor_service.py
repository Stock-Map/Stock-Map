from models.fornecedor_model import Fornecedor


class AtualizarFornecedorService:
    def executar(self, fornecedor_id, dados):
        fornecedor = Fornecedor.buscar_por_id(fornecedor_id)
        if fornecedor is None:
            return None

        novo_email = dados.get("email")
        if novo_email:
            existente = Fornecedor.buscar_por_email(novo_email)
            if existente and existente.id != fornecedor.id:
                raise ValueError("Já existe outro fornecedor cadastrado com este e-mail.")

        fornecedor.atualizar(
            nome=dados.get("nome"),
            cnpj=dados.get("cnpj"),
            nome_contato=dados.get("nome_contato"),
            email=dados.get("email"),
            telefone=dados.get("telefone"),
            endereco=dados.get("endereco"),
            cidade=dados.get("cidade"),
            estado=dados.get("estado"),
            latitude=dados.get("latitude"),
            longitude=dados.get("longitude"),
        )
        return fornecedor.to_dict()
