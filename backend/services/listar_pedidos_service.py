from datetime import datetime

from models.pedido_model import Pedido
from repositories.pedido_repository import PedidoRepository


class ListarPedidosService:
    def executar(self, status=None, lojista_id=None, data_inicio=None, data_fim=None):
        if status not in (None, "") and status not in Pedido.STATUS_VALIDOS:
            raise ValueError(
                "Status inválido. Use: " + ", ".join(Pedido.STATUS_VALIDOS) + "."
            )

        return PedidoRepository.buscar_filtrados(
            status=status or None,
            lojista_id=self._inteiro(lojista_id, "lojista_id"),
            data_inicio=self._data(data_inicio, "data_inicio"),
            data_fim=self._data(data_fim, "data_fim"),
        )

    @staticmethod
    def _inteiro(valor, nome_campo):
        if valor in (None, ""):
            return None
        try:
            return int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O filtro '{nome_campo}' deve ser um número inteiro.") from erro

    @staticmethod
    def _data(valor, nome_campo):
        if valor in (None, ""):
            return None
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date()
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O filtro '{nome_campo}' deve estar no formato AAAA-MM-DD.") from erro
