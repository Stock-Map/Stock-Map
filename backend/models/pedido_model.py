from datetime import datetime

from .database import db


class Pedido(db.Model):
    __tablename__ = "pedidos"

    STATUS_VALIDOS = ("pendente", "confirmado", "despachado", "entregue", "cancelado")

    id = db.Column(db.Integer, primary_key=True)
    lojista_id = db.Column(db.Integer, db.ForeignKey("lojistas.id"), nullable=False)
    fornecedor_id = db.Column(
        db.Integer, db.ForeignKey("fornecedores.id"), nullable=False
    )
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_pedido"),
        nullable=False,
        default="pendente",
    )
    observacoes = db.Column(db.Text)
    valor_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    endereco_entrega = db.Column(db.String(220))
    criado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now,
        server_default=db.func.current_timestamp(),
    )
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now,
        server_default=db.func.current_timestamp(),
    )

    lojista = db.relationship("Lojista", backref="pedidos")
    fornecedor = db.relationship("Fornecedor", backref="pedidos")
    itens = db.relationship(
        "ItemPedido", backref="pedido", cascade="all, delete-orphan"
    )

    def salvar(self):
        """CREATE: salva um novo pedido no banco."""
        db.session.add(self)
        db.session.commit()

    def atualizar(self, **campos):
        """UPDATE: altera apenas os campos informados."""
        permitidos = ("status", "observacoes", "endereco_entrega", "valor_total")
        for nome_campo, valor in campos.items():
            if nome_campo in permitidos and valor is not None:
                setattr(self, nome_campo, valor)
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna todos os pedidos, do mais recente para o mais antigo."""
        return Pedido.query.order_by(Pedido.criado_em.desc()).all()

    @staticmethod
    def buscar_por_id(id):
        """READ: busca um pedido pelo id."""
        return db.session.get(Pedido, id)

    @staticmethod
    def buscar_para_atualizacao(id):
        """READ com trava: usado na troca de status, que devolve estoque."""
        return Pedido.query.filter(Pedido.id == id).with_for_update().first()

    def to_dict(self):
        return {
            "id": self.id,
            "lojista_id": self.lojista_id,
            "lojista_nome": self.lojista.nome if self.lojista else None,
            "fornecedor_id": self.fornecedor_id,
            "fornecedor_nome": self.fornecedor.nome if self.fornecedor else None,
            "status": self.status,
            "observacoes": self.observacoes,
            "valor_total": float(self.valor_total),
            "endereco_entrega": self.endereco_entrega,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class ItemPedido(db.Model):
    __tablename__ = "itens_pedido"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos.id"), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)

    produto = db.relationship("Produto")

    def to_dict(self):
        return {
            "id": self.id,
            "pedido_id": self.pedido_id,
            "produto_id": self.produto_id,
            "produto_nome": self.produto.nome if self.produto else None,
            "sku": self.produto.sku if self.produto else None,
            "quantidade": self.quantidade,
            "preco_unitario": float(self.preco_unitario),
            "subtotal": float(self.subtotal),
        }
