from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.criar_fornecedor_service import CriarFornecedorService
from services.listar_fornecedores_service import ListarFornecedoresService
from services.buscar_fornecedor_por_id_service import BuscarFornecedorPorIdService
from services.atualizar_fornecedor_service import AtualizarFornecedorService
from services.deletar_fornecedor_service import DeletarFornecedorService

fornecedor_controller = Blueprint("fornecedor_controller", __name__)


@fornecedor_controller.get("/fornecedores")
def listar_fornecedores():
    try:
        service = ListarFornecedoresService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar fornecedores."}), 500


@fornecedor_controller.post("/fornecedores")
def criar_fornecedor():
    try:
        dados = request.get_json() or {}
        service = CriarFornecedorService()
        return jsonify(service.executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar fornecedor no banco de dados."}), 500


@fornecedor_controller.get("/fornecedores/<int:fornecedor_id>")
def buscar_fornecedor_por_id(fornecedor_id):
    try:
        service = BuscarFornecedorPorIdService()
        fornecedor = service.executar(fornecedor_id)
        if fornecedor is None:
            return jsonify({"erro": "Fornecedor não encontrado."}), 404
        return jsonify(fornecedor), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao buscar fornecedor."}), 500


@fornecedor_controller.put("/fornecedores/<int:fornecedor_id>")
def atualizar_fornecedor(fornecedor_id):
    try:
        dados = request.get_json() or {}
        service = AtualizarFornecedorService()
        fornecedor = service.executar(fornecedor_id, dados)
        if fornecedor is None:
            return jsonify({"erro": "Fornecedor não encontrado."}), 404
        return jsonify(fornecedor), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar fornecedor no banco de dados."}), 500


@fornecedor_controller.delete("/fornecedores/<int:fornecedor_id>")
def deletar_fornecedor(fornecedor_id):
    try:
        service = DeletarFornecedorService()
        if service.executar(fornecedor_id) is False:
            return jsonify({"erro": "Fornecedor não encontrado."}), 404
        return "", 204
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao remover fornecedor do banco de dados."}), 500
