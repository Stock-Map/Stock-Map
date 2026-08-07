from models.fornecedor_model import Fornecedor
from models.produto_model import Produto


class CriarProdutoService:
    CAMPOS_OBRIGATORIOS = ("fornecedor_id", "sku", "nome", "preco_unitario")

    def executar(self, dados):
        for campo in self.CAMPOS_OBRIGATORIOS:
            if dados.get(campo) in (None, ""):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        fornecedor_id = self._inteiro(dados["fornecedor_id"], "fornecedor_id", minimo=1)
        if Fornecedor.buscar_por_id(fornecedor_id) is None:
            raise ValueError("Fornecedor não encontrado.")

        if Produto.buscar_por_sku(fornecedor_id, dados["sku"]):
            raise ValueError("Já existe um produto com este SKU para o fornecedor.")

        produto = Produto(
            fornecedor_id=fornecedor_id,
            sku=dados["sku"],
            nome=dados["nome"],
            categoria=dados.get("categoria"),
            preco_unitario=self._decimal(dados["preco_unitario"], "preco_unitario"),
            quantidade=self._inteiro(dados.get("quantidade", 0), "quantidade", minimo=0),
            estoque_minimo=self._inteiro(dados.get("estoque_minimo", 5), "estoque_minimo", minimo=0),
            prazo_entrega_dias=self._inteiro(
                dados.get("prazo_entrega_dias", 2), "prazo_entrega_dias", minimo=0
            ),
            ativo=True,
        )
        produto.salvar()
        return produto.to_dict()

    @staticmethod
    def _inteiro(valor, nome_campo, minimo=None):
        try:
            numero = int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O campo '{nome_campo}' deve ser um número inteiro.") from erro
        if minimo is not None and numero < minimo:
            raise ValueError(f"O campo '{nome_campo}' deve ser maior ou igual a {minimo}.")
        return numero

    @staticmethod
    def _decimal(valor, nome_campo):
        try:
            numero = float(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O campo '{nome_campo}' deve ser um número.") from erro
        if numero < 0:
            raise ValueError(f"O campo '{nome_campo}' não pode ser negativo.")
        return numero
