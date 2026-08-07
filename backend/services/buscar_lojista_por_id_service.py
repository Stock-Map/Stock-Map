from models.lojista_model import Lojista


class BuscarLojistaPorIdService:
    def executar(self, lojista_id):
        lojista = Lojista.buscar_por_id(lojista_id)
        if lojista is None:
            return None
        return lojista.to_dict()
