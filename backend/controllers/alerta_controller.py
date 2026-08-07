from flask import Blueprint, jsonify
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.listar_alertas_estoque_baixo_service import ListarAlertasEstoqueBaixoService

alerta_controller = Blueprint("alerta_controller", __name__)


@alerta_controller.get("/alertas")
def listar_alertas():
    try:
        service = ListarAlertasEstoqueBaixoService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar alertas de estoque."}), 500
