from repositories.alerta_repository import AlertaRepository


class ListarAlertasEstoqueBaixoService:
    def executar(self):
        return AlertaRepository.listar_estoque_baixo()
