from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.criar_pedido_service import CriarPedidoService
from services.listar_pedidos_service import ListarPedidosService
from services.buscar_pedido_por_id_service import BuscarPedidoPorIdService
from services.atualizar_status_pedido_service import AtualizarStatusPedidoService

pedido_controller = Blueprint("pedido_controller", __name__)


@pedido_controller.get("/pedidos")
def listar_pedidos():
    try:
        service = ListarPedidosService()
        pedidos = service.executar(
            status=request.args.get("status"),
            lojista_id=request.args.get("lojista_id"),
            data_inicio=request.args.get("data_inicio"),
            data_fim=request.args.get("data_fim"),
        )
        return jsonify(pedidos), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar pedidos."}), 500


@pedido_controller.post("/pedidos")
def criar_pedido():
    try:
        dados = request.get_json() or {}
        service = CriarPedidoService()
        return jsonify(service.executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar pedido no banco de dados."}), 500


@pedido_controller.get("/pedidos/<int:pedido_id>")
def buscar_pedido_por_id(pedido_id):
    try:
        service = BuscarPedidoPorIdService()
        pedido = service.executar(pedido_id)
        if pedido is None:
            return jsonify({"erro": "Pedido não encontrado."}), 404
        return jsonify(pedido), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao buscar pedido."}), 500


@pedido_controller.patch("/pedidos/<int:pedido_id>/status")
def atualizar_status_pedido(pedido_id):
    try:
        dados = request.get_json() or {}
        service = AtualizarStatusPedidoService()
        pedido = service.executar(pedido_id, dados)
        if pedido is None:
            return jsonify({"erro": "Pedido não encontrado."}), 404
        return jsonify(pedido), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar o status do pedido."}), 500
