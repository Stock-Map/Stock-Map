from models.lojista_model import Lojista


class AtualizarLojistaService:
    def executar(self, lojista_id, dados):
        lojista = Lojista.buscar_por_id(lojista_id)
        if lojista is None:
            return None

        novo_email = dados.get("email")
        if novo_email:
            existente = Lojista.buscar_por_email(novo_email)
            if existente and existente.id != lojista.id:
                raise ValueError("Já existe outro lojista cadastrado com este e-mail.")

        lojista.atualizar(
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
        return lojista.to_dict()
