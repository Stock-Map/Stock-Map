from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linha, converter_linhas


class RelatorioRepository:
    """Agregacoes e rankings usados nos relatorios."""

    @staticmethod
    def resumo(data_inicio, data_fim):
        sql = text("CALL sp_relatorio_resumo(:data_inicio, :data_fim)")
        resultado = db.session.execute(
            sql, {"data_inicio": data_inicio, "data_fim": data_fim}
        )
        linhas = resultado.mappings().all()
        resultado.close()
        if not linhas:
            return {}
        return converter_linha(linhas[0])

    @staticmethod
    def top_produtos(data_inicio, data_fim):
        sql = text("CALL sp_relatorio_top_produtos(:data_inicio, :data_fim)")
        resultado = db.session.execute(
            sql, {"data_inicio": data_inicio, "data_fim": data_fim}
        )
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)

    @staticmethod
    def desempenho_fornecedores(data_inicio, data_fim):
        sql = text("CALL sp_relatorio_desempenho_fornecedores(:data_inicio, :data_fim)")
        resultado = db.session.execute(
            sql, {"data_inicio": data_inicio, "data_fim": data_fim}
        )
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)
