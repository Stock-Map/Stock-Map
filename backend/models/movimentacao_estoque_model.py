from datetime import datetime

from .database import db


class MovimentacaoEstoque(db.Model):
    __tablename__ = "movimentacoes_estoque"

    TIPOS_VALIDOS = ("entrada", "saida", "ajuste")

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos.id"), nullable=False)
    fornecedor_id = db.Column(
        db.Integer, db.ForeignKey("fornecedores.id"), nullable=False
    )
    tipo_movimentacao = db.Column(
        db.Enum(*TIPOS_VALIDOS, name="tipo_movimentacao"), nullable=False
    )
    variacao_quantidade = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(180))
    referencia_tipo = db.Column(db.String(40))
    referencia_id = db.Column(db.Integer)
    criado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now,
        server_default=db.func.current_timestamp(),
    )

    produto = db.relationship("Produto")
    fornecedor = db.relationship("Fornecedor")

    def salvar(self):
        """CREATE: registra uma movimentacao de estoque."""
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna as movimentacoes da mais recente para a mais antiga."""
        return (
            MovimentacaoEstoque.query
            .order_by(MovimentacaoEstoque.criado_em.desc())
            .all()
        )

    def to_dict(self):
        return {
            "id": self.id,
            "produto_id": self.produto_id,
            "produto_nome": self.produto.nome if self.produto else None,
            "fornecedor_id": self.fornecedor_id,
            "fornecedor_nome": self.fornecedor.nome if self.fornecedor else None,
            "tipo_movimentacao": self.tipo_movimentacao,
            "variacao_quantidade": self.variacao_quantidade,
            "motivo": self.motivo,
            "referencia_tipo": self.referencia_tipo,
            "referencia_id": self.referencia_id,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
