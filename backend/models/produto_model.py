from datetime import datetime

from .database import db


class Produto(db.Model):
    __tablename__ = "produtos"
    __table_args__ = (
        db.UniqueConstraint("fornecedor_id", "sku", name="uq_produtos_fornecedor_sku"),
    )

    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(
        db.Integer, db.ForeignKey("fornecedores.id"), nullable=False
    )
    sku = db.Column(db.String(60), nullable=False)
    nome = db.Column(db.String(160), nullable=False)
    categoria = db.Column(db.String(100))
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    estoque_minimo = db.Column(db.Integer, nullable=False, default=5)
    prazo_entrega_dias = db.Column(db.Integer, nullable=False, default=2)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now,
        server_default=db.func.current_timestamp(),
    )
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now,
        server_default=db.func.current_timestamp(),
    )

    fornecedor = db.relationship("Fornecedor", backref="produtos")

    def salvar(self):
        """CREATE: salva um novo produto no banco."""
        db.session.add(self)
        db.session.commit()

    def atualizar(self, **campos):
        """UPDATE: altera apenas os campos informados."""
        permitidos = (
            "fornecedor_id", "sku", "nome", "categoria", "preco_unitario",
            "quantidade", "estoque_minimo", "prazo_entrega_dias", "ativo",
        )
        for nome_campo, valor in campos.items():
            if nome_campo in permitidos and valor is not None:
                setattr(self, nome_campo, valor)
        db.session.commit()

    def deletar(self):
        """DELETE: remove o produto do banco."""
        db.session.delete(self)
        db.session.commit()

    def desativar(self):
        """DELETE logico: mantem o historico de pedidos que referenciam o produto."""
        self.ativo = False
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna todos os produtos ativos ordenados por nome."""
        return (
            Produto.query
            .filter(Produto.ativo.is_(True))
            .order_by(Produto.nome.asc())
            .all()
        )

    @staticmethod
    def buscar_por_id(id):
        """READ: busca um produto pelo id."""
        return db.session.get(Produto, id)

    @staticmethod
    def buscar_por_sku(fornecedor_id, sku):
        """READ auxiliar: garante SKU unico por fornecedor."""
        return Produto.query.filter_by(fornecedor_id=fornecedor_id, sku=sku).first()

    @staticmethod
    def buscar_para_atualizacao(id):
        """READ com trava: usado pelos casos de uso que movimentam estoque."""
        return (
            Produto.query
            .filter(Produto.id == id)
            .with_for_update()
            .first()
        )

    def status_estoque(self):
        if self.quantidade <= 0:
            return "indisponivel"
        if self.quantidade <= self.estoque_minimo:
            return "baixo"
        return "disponivel"

    def to_dict(self):
        return {
            "id": self.id,
            "fornecedor_id": self.fornecedor_id,
            "fornecedor_nome": self.fornecedor.nome if self.fornecedor else None,
            "sku": self.sku,
            "nome": self.nome,
            "categoria": self.categoria,
            "preco_unitario": float(self.preco_unitario),
            "quantidade": self.quantidade,
            "estoque_minimo": self.estoque_minimo,
            "prazo_entrega_dias": self.prazo_entrega_dias,
            "ativo": self.ativo,
            "status_estoque": self.status_estoque(),
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }
