from models.database import db
from models.movimentacao_estoque_model import MovimentacaoEstoque
from models.pedido_model import ItemPedido, Pedido
from models.produto_model import Produto


class AtualizarStatusPedidoService:
    """Troca o status do pedido e devolve o estoque quando ele e cancelado."""

    def executar(self, pedido_id, dados):
        status = dados.get("status")
        if status not in Pedido.STATUS_VALIDOS:
            raise ValueError(
                "Status inválido. Use: " + ", ".join(Pedido.STATUS_VALIDOS) + "."
            )

        try:
            pedido = Pedido.buscar_para_atualizacao(pedido_id)
            if pedido is None:
                db.session.rollback()
                return None

            anterior = pedido.status
            if anterior == status:
                db.session.rollback()
                return pedido.to_dict()

            if anterior == "cancelado":
                raise ValueError("Pedido cancelado não pode mudar de status.")

            if status == "cancelado":
                itens = ItemPedido.query.filter_by(pedido_id=pedido.id).all()
                for item in itens:
                    produto = Produto.buscar_para_atualizacao(item.produto_id)
                    if produto is None:
                        continue
                    produto.quantidade = produto.quantidade + item.quantidade
                    db.session.add(
                        MovimentacaoEstoque(
                            produto_id=produto.id,
                            fornecedor_id=pedido.fornecedor_id,
                            tipo_movimentacao="entrada",
                            variacao_quantidade=item.quantidade,
                            motivo="Pedido cancelado",
                            referencia_tipo="cancelamento_pedido",
                            referencia_id=pedido.id,
                        )
                    )

            pedido.status = status
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return pedido.to_dict()
