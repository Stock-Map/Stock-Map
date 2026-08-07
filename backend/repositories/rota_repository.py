from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linhas


class RotaRepository:
    """Consultas de roteirizacao e listagem de rotas com suas paradas."""

    @staticmethod
    def pedidos_para_roteirizar(fornecedor_id):
        sql = text("CALL sp_pedidos_para_roteirizar(:fornecedor_id)")
        resultado = db.session.execute(sql, {"fornecedor_id": fornecedor_id})
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)

    @staticmethod
    def listar_com_paradas():
        sql_rotas = text("CALL sp_rotas_listar()")
        resultado = db.session.execute(sql_rotas)
        rotas = converter_linhas(resultado.mappings().all())
        resultado.close()

        for rota in rotas:
            sql_paradas = text("CALL sp_rota_paradas(:rota_id)")
            resultado_paradas = db.session.execute(sql_paradas, {"rota_id": rota["id"]})
            rota["paradas"] = converter_linhas(resultado_paradas.mappings().all())
            resultado_paradas.close()

        return rotas
