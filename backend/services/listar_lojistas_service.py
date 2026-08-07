from models.lojista_model import Lojista


class ListarLojistasService:
    def executar(self):
        lojistas = Lojista.listar_todos()
        return [lojista.to_dict() for lojista in lojistas]
