from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.gerar_relatorio_service import GerarRelatorioService

relatorio_controller = Blueprint("relatorio_controller", __name__)


@relatorio_controller.get("/relatorios")
def gerar_relatorio():
    try:
        service = GerarRelatorioService()
        relatorio = service.executar(
            data_inicio=request.args.get("data_inicio"),
            data_fim=request.args.get("data_fim"),
        )
        return jsonify(relatorio), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao gerar o relatório."}), 500
