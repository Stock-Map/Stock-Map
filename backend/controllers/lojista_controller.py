from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.criar_lojista_service import CriarLojistaService
from services.listar_lojistas_service import ListarLojistasService
from services.buscar_lojista_por_id_service import BuscarLojistaPorIdService
from services.atualizar_lojista_service import AtualizarLojistaService
from services.deletar_lojista_service import DeletarLojistaService

lojista_controller = Blueprint("lojista_controller", __name__)


@lojista_controller.get("/lojistas")
def listar_lojistas():
    try:
        service = ListarLojistasService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar lojistas."}), 500


@lojista_controller.post("/lojistas")
def criar_lojista():
    try:
        dados = request.get_json() or {}
        service = CriarLojistaService()
        return jsonify(service.executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar lojista no banco de dados."}), 500


@lojista_controller.get("/lojistas/<int:lojista_id>")
def buscar_lojista_por_id(lojista_id):
    try:
        service = BuscarLojistaPorIdService()
        lojista = service.executar(lojista_id)
        if lojista is None:
            return jsonify({"erro": "Lojista não encontrado."}), 404
        return jsonify(lojista), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao buscar lojista."}), 500


@lojista_controller.put("/lojistas/<int:lojista_id>")
def atualizar_lojista(lojista_id):
    try:
        dados = request.get_json() or {}
        service = AtualizarLojistaService()
        lojista = service.executar(lojista_id, dados)
        if lojista is None:
            return jsonify({"erro": "Lojista não encontrado."}), 404
        return jsonify(lojista), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar lojista no banco de dados."}), 500


@lojista_controller.delete("/lojistas/<int:lojista_id>")
def deletar_lojista(lojista_id):
    try:
        service = DeletarLojistaService()
        if service.executar(lojista_id) is False:
            return jsonify({"erro": "Lojista não encontrado."}), 404
        return "", 204
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao remover lojista do banco de dados."}), 500
