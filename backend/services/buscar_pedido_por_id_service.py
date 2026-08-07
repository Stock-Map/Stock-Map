from repositories.pedido_repository import PedidoRepository


class BuscarPedidoPorIdService:
    def executar(self, pedido_id):
        pedido = PedidoRepository.buscar_detalhe(pedido_id)
        if pedido is None:
            return None
        pedido["itens"] = PedidoRepository.buscar_itens(pedido_id)
        return pedido
