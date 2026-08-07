from datetime import datetime

from .database import db


class Lojista(db.Model):
    __tablename__ = "lojistas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(140), nullable=False)
    cnpj = db.Column(db.String(24))
    nome_contato = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True)
    telefone = db.Column(db.String(40))
    endereco = db.Column(db.String(220))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(40))
    latitude = db.Column(db.Numeric(10, 7))
    longitude = db.Column(db.Numeric(10, 7))
    criado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now,
        server_default=db.func.current_timestamp(),
    )
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now,
        server_default=db.func.current_timestamp(),
    )

    def salvar(self):
        """CREATE: salva um novo lojista no banco."""
        db.session.add(self)
        db.session.commit()

    def atualizar(self, **campos):
        """UPDATE: altera apenas os campos informados."""
        permitidos = (
            "nome", "cnpj", "nome_contato", "email", "telefone",
            "endereco", "cidade", "estado", "latitude", "longitude",
        )
        for nome_campo, valor in campos.items():
            if nome_campo in permitidos and valor is not None:
                setattr(self, nome_campo, valor)
        db.session.commit()

    def deletar(self):
        """DELETE: remove o lojista do banco."""
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna todos os lojistas ordenados por nome."""
        return Lojista.query.order_by(Lojista.nome.asc()).all()

    @staticmethod
    def buscar_por_id(id):
        """READ: busca um lojista pelo id."""
        return db.session.get(Lojista, id)

    @staticmethod
    def buscar_por_email(email):
        """READ auxiliar: busca um lojista pelo e-mail."""
        return Lojista.query.filter_by(email=email).first()

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "cnpj": self.cnpj,
            "nome_contato": self.nome_contato,
            "email": self.email,
            "telefone": self.telefone,
            "endereco": self.endereco,
            "cidade": self.cidade,
            "estado": self.estado,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }
