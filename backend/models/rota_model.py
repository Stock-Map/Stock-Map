from datetime import datetime

from .database import db


class RotaEntrega(db.Model):
    __tablename__ = "rotas_entrega"

    STATUS_VALIDOS = ("planejada", "em_andamento", "concluida", "cancelada")

    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(
        db.Integer, db.ForeignKey("fornecedores.id"), nullable=False
    )
    data_rota = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_rota"), nullable=False, default="planejada"
    )
    distancia_total_km = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    observacoes = db.Column(db.Text)
    criado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now,
        server_default=db.func.current_timestamp(),
    )
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now,
        server_default=db.func.current_timestamp(),
    )

    fornecedor = db.relationship("Fornecedor")
    paradas = db.relationship(
        "ParadaRota", backref="rota", cascade="all, delete-orphan"
    )

    def salvar(self):
        """CREATE: salva uma nova rota de entrega."""
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna as rotas da mais recente para a mais antiga."""
        return RotaEntrega.query.order_by(RotaEntrega.criado_em.desc()).all()

    @staticmethod
    def buscar_por_id(id):
        """READ: busca uma rota pelo id."""
        return db.session.get(RotaEntrega, id)

    def to_dict(self):
        return {
            "id": self.id,
            "fornecedor_id": self.fornecedor_id,
            "fornecedor_nome": self.fornecedor.nome if self.fornecedor else None,
            "data_rota": self.data_rota.isoformat() if self.data_rota else None,
            "status": self.status,
            "distancia_total_km": float(self.distancia_total_km),
            "observacoes": self.observacoes,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class ParadaRota(db.Model):
    __tablename__ = "paradas_rota"
    __table_args__ = (
        db.UniqueConstraint("rota_id", "ordem_parada", name="uq_paradas_rota_ordem"),
    )

    STATUS_VALIDOS = ("planejada", "concluida", "ignorada")

    id = db.Column(db.Integer, primary_key=True)
    rota_id = db.Column(db.Integer, db.ForeignKey("rotas_entrega.id"), nullable=False)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False)
    lojista_id = db.Column(db.Integer, db.ForeignKey("lojistas.id"), nullable=False)
    ordem_parada = db.Column(db.Integer, nullable=False)
    distancia_anterior_km = db.Column(db.Numeric(10, 2))
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_parada"),
        nullable=False,
        default="planejada",
    )
    criado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now,
        server_default=db.func.current_timestamp(),
    )

    lojista = db.relationship("Lojista")

    def to_dict(self):
        return {
            "id": self.id,
            "rota_id": self.rota_id,
            "pedido_id": self.pedido_id,
            "lojista_id": self.lojista_id,
            "lojista_nome": self.lojista.nome if self.lojista else None,
            "ordem_parada": self.ordem_parada,
            "distancia_anterior_km": (
                float(self.distancia_anterior_km)
                if self.distancia_anterior_km is not None
                else None
            ),
            "status": self.status,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
