from models.database import db
from models.movimentacao_estoque_model import MovimentacaoEstoque
from models.produto_model import Produto


class AtualizarEstoqueProdutoService:
    def executar(self, produto_id, dados):
        if dados.get("quantidade") in (None, ""):
            raise ValueError("O campo 'quantidade' é obrigatório.")

        try:
            quantidade = int(dados["quantidade"])
        except (TypeError, ValueError) as erro:
            raise ValueError("O campo 'quantidade' deve ser um número inteiro.") from erro

        if quantidade < 0:
            raise ValueError("O campo 'quantidade' não pode ser negativo.")

        motivo = dados.get("motivo") or "Atualização manual"

        try:
            produto = Produto.buscar_para_atualizacao(produto_id)
            if produto is None:
                db.session.rollback()
                return None

            variacao = quantidade - produto.quantidade
            produto.quantidade = quantidade

            db.session.add(
                MovimentacaoEstoque(
                    produto_id=produto.id,
                    fornecedor_id=produto.fornecedor_id,
                    tipo_movimentacao="ajuste",
                    variacao_quantidade=variacao,
                    motivo=motivo,
                    referencia_tipo="manual",
                    referencia_id=None,
                )
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return produto.to_dict()
