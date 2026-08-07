from decimal import Decimal

from models.database import db
from models.fornecedor_model import Fornecedor
from models.lojista_model import Lojista
from models.movimentacao_estoque_model import MovimentacaoEstoque
from models.pedido_model import ItemPedido, Pedido
from models.produto_model import Produto


class CriarPedidoService:
    """Grava pedido, itens, baixa de estoque e movimentacoes em uma transacao."""

    def executar(self, dados):
        lojista_id = self._inteiro(dados.get("lojista_id"), "lojista_id", minimo=1)
        fornecedor_id = self._inteiro(dados.get("fornecedor_id"), "fornecedor_id", minimo=1)

        itens = dados.get("itens") or []
        if not itens:
            raise ValueError("Inclua ao menos um item no pedido.")

        lojista = Lojista.buscar_por_id(lojista_id)
        if lojista is None:
            raise ValueError("Lojista não encontrado.")
        if Fornecedor.buscar_por_id(fornecedor_id) is None:
            raise ValueError("Fornecedor não encontrado.")

        try:
            pedido = Pedido(
                lojista_id=lojista_id,
                fornecedor_id=fornecedor_id,
                status="confirmado",
                observacoes=dados.get("observacoes"),
                valor_total=Decimal("0"),
                endereco_entrega=dados.get("endereco_entrega") or lojista.endereco,
            )
            db.session.add(pedido)
            db.session.flush()  # atribui pedido.id sem encerrar a transacao

            total = Decimal("0")
            for item in itens:
                produto_id = self._inteiro(item.get("produto_id"), "produto_id", minimo=1)
                quantidade = self._inteiro(item.get("quantidade"), "quantidade", minimo=1)

                produto = Produto.buscar_para_atualizacao(produto_id)
                if produto is None or not produto.ativo:
                    raise ValueError("Produto não encontrado.")
                if produto.fornecedor_id != fornecedor_id:
                    raise ValueError(
                        f"O produto {produto.nome} não pertence ao fornecedor selecionado."
                    )
                if produto.quantidade < quantidade:
                    raise ValueError(
                        f"Estoque insuficiente para {produto.nome}. "
                        f"Disponível: {produto.quantidade}."
                    )

                subtotal = produto.preco_unitario * quantidade
                total += subtotal

                db.session.add(
                    ItemPedido(
                        pedido_id=pedido.id,
                        produto_id=produto.id,
                        quantidade=quantidade,
                        preco_unitario=produto.preco_unitario,
                        subtotal=subtotal,
                    )
                )
                produto.quantidade = produto.quantidade - quantidade
                db.session.add(
                    MovimentacaoEstoque(
                        produto_id=produto.id,
                        fornecedor_id=fornecedor_id,
                        tipo_movimentacao="saida",
                        variacao_quantidade=-quantidade,
                        motivo="Pedido confirmado",
                        referencia_tipo="pedido",
                        referencia_id=pedido.id,
                    )
                )

            pedido.valor_total = total
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return pedido.to_dict()

    @staticmethod
    def _inteiro(valor, nome_campo, minimo=None):
        try:
            numero = int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O campo '{nome_campo}' deve ser um número inteiro.") from erro
        if minimo is not None and numero < minimo:
            raise ValueError(f"O campo '{nome_campo}' deve ser maior ou igual a {minimo}.")
        return numero
