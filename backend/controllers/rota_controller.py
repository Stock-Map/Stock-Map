from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.planejar_rota_service import PlanejarRotaService
from services.listar_rotas_service import ListarRotasService

rota_controller = Blueprint("rota_controller", __name__)


@rota_controller.get("/rotas")
def listar_rotas():
    try:
        service = ListarRotasService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar rotas."}), 500


@rota_controller.post("/rotas")
def planejar_rota():
    try:
        dados = request.get_json() or {}
        service = PlanejarRotaService()
        return jsonify(service.executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao planejar a rota de entrega."}), 500
