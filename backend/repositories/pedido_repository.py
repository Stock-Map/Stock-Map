from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linha, converter_linhas


class PedidoRepository:
    """Consultas de pedido que envolvem filtros e juncao com outras tabelas."""

    @staticmethod
    def buscar_filtrados(status=None, lojista_id=None, data_inicio=None, data_fim=None):
        sql = text(
            "CALL sp_pedidos_filtrados(:status, :lojista_id, :data_inicio, :data_fim)"
        )
        resultado = db.session.execute(
            sql,
            {
                "status": status,
                "lojista_id": lojista_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
            },
        )
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)

    @staticmethod
    def buscar_detalhe(pedido_id):
        sql = text("CALL sp_pedido_detalhe(:pedido_id)")
        resultado = db.session.execute(sql, {"pedido_id": pedido_id})
        linhas = resultado.mappings().all()
        resultado.close()
        if not linhas:
            return None
        return converter_linha(linhas[0])

    @staticmethod
    def buscar_itens(pedido_id):
        sql = text("CALL sp_pedido_itens(:pedido_id)")
        resultado = db.session.execute(sql, {"pedido_id": pedido_id})
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)
