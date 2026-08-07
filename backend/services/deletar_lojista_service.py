from models.lojista_model import Lojista
from models.pedido_model import Pedido


class DeletarLojistaService:
    def executar(self, lojista_id):
        lojista = Lojista.buscar_por_id(lojista_id)
        if lojista is None:
            return False

        pedidos = Pedido.query.filter_by(lojista_id=lojista_id).count()
        if pedidos > 0:
            raise ValueError(
                "Não é possível remover um lojista que possui pedidos registrados."
            )

        lojista.deletar()
        return True
