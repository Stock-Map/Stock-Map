from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linhas


class MovimentacaoRepository:
    """Historico de entradas, saidas e ajustes de estoque."""

    @staticmethod
    def buscar_historico(produto_id=None, fornecedor_id=None,
                         data_inicio=None, data_fim=None):
        sql = text(
            "CALL sp_historico_movimentacoes("
            ":produto_id, :fornecedor_id, :data_inicio, :data_fim)"
        )
        resultado = db.session.execute(
            sql,
            {
                "produto_id": produto_id,
                "fornecedor_id": fornecedor_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
            },
        )
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)
