from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.listar_historico_movimentacoes_service import (
    ListarHistoricoMovimentacoesService,
)

movimentacao_controller = Blueprint("movimentacao_controller", __name__)


@movimentacao_controller.get("/movimentacoes")
def listar_movimentacoes():
    try:
        service = ListarHistoricoMovimentacoesService()
        movimentacoes = service.executar(
            produto_id=request.args.get("produto_id"),
            fornecedor_id=request.args.get("fornecedor_id"),
            data_inicio=request.args.get("data_inicio"),
            data_fim=request.args.get("data_fim"),
        )
        return jsonify(movimentacoes), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar o histórico de movimentações."}), 500
