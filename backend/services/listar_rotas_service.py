from repositories.rota_repository import RotaRepository


class ListarRotasService:
    def executar(self):
        return RotaRepository.listar_com_paradas()
