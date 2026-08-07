from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linhas


class AlertaRepository:
    """Alertas de estoque, calculados por procedure."""

    @staticmethod
    def listar_estoque_baixo():
        sql = text("CALL sp_alertas_estoque_baixo()")
        resultado = db.session.execute(sql)
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)
