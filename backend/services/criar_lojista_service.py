from models.lojista_model import Lojista


class CriarLojistaService:
    CAMPOS_OBRIGATORIOS = ("nome", "nome_contato", "email")

    def executar(self, dados):
        for campo in self.CAMPOS_OBRIGATORIOS:
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        if Lojista.buscar_por_email(dados["email"]):
            raise ValueError("Já existe um lojista cadastrado com este e-mail.")

        lojista = Lojista(
            nome=dados["nome"],
            cnpj=dados.get("cnpj"),
            nome_contato=dados["nome_contato"],
            email=dados["email"],
            telefone=dados.get("telefone"),
            endereco=dados.get("endereco"),
            cidade=dados.get("cidade"),
            estado=dados.get("estado"),
            latitude=dados.get("latitude"),
            longitude=dados.get("longitude"),
        )
        lojista.salvar()
        return lojista.to_dict()
