from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linhas


class ProdutoRepository:
    """Consultas de produto que vao alem do CRUD basico da Model."""

    @staticmethod
    def buscar_com_status(fornecedor_id=None, busca=None):
        sql = text("CALL sp_produtos_com_status(:fornecedor_id, :busca)")
        resultado = db.session.execute(
            sql, {"fornecedor_id": fornecedor_id, "busca": busca}
        )
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)
