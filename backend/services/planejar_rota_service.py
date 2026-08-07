from datetime import date
from math import asin, cos, radians, sin, sqrt

from models.database import db
from models.fornecedor_model import Fornecedor
from models.rota_model import ParadaRota, RotaEntrega
from repositories.rota_repository import RotaRepository


class PlanejarRotaService:
    """Monta a rota de entrega ordenando as paradas por vizinho mais proximo."""

    RAIO_TERRA_KM = 6371

    def executar(self, dados):
        fornecedor_id = self._inteiro(dados.get("fornecedor_id"), "fornecedor_id", minimo=1)

        fornecedor = Fornecedor.buscar_por_id(fornecedor_id)
        if fornecedor is None:
            raise ValueError("Fornecedor não encontrado.")

        paradas = RotaRepository.pedidos_para_roteirizar(fornecedor_id)

        pedidos_escolhidos = dados.get("pedidos_ids") or []
        if pedidos_escolhidos:
            escolhidos = {
                self._inteiro(pedido_id, "pedidos_ids", minimo=1)
                for pedido_id in pedidos_escolhidos
            }
            paradas = [p for p in paradas if p["pedido_id"] in escolhidos]

        if not paradas:
            raise ValueError("Não existem pedidos confirmados para roteirizar.")

        origem = (fornecedor.latitude, fornecedor.longitude)
        ordenadas = self._ordenar(origem, paradas)
        distancia_total = sum(
            (parada.get("distancia_anterior_km") or 0) for parada in ordenadas
        )

        try:
            rota = RotaEntrega(
                fornecedor_id=fornecedor_id,
                data_rota=date.today(),
                status="planejada",
                distancia_total_km=distancia_total,
                observacoes=dados.get("observacoes"),
            )
            db.session.add(rota)
            db.session.flush()

            for indice, parada in enumerate(ordenadas, start=1):
                db.session.add(
                    ParadaRota(
                        rota_id=rota.id,
                        pedido_id=parada["pedido_id"],
                        lojista_id=parada["lojista_id"],
                        ordem_parada=indice,
                        distancia_anterior_km=parada.get("distancia_anterior_km"),
                        status="planejada",
                    )
                )

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return rota.to_dict()

    def _ordenar(self, origem, paradas):
        sem_coordenada = any(
            parada["latitude"] is None or parada["longitude"] is None
            for parada in paradas
        )
        if origem[0] is None or origem[1] is None or sem_coordenada:
            return sorted(
                paradas, key=lambda p: ((p["cidade"] or ""), p["lojista_nome"])
            )

        ordenadas = []
        atual = origem
        restantes = list(paradas)
        while restantes:
            proxima = min(
                restantes,
                key=lambda p: self._haversine(atual, (p["latitude"], p["longitude"])),
            )
            proxima["distancia_anterior_km"] = self._haversine(
                atual, (proxima["latitude"], proxima["longitude"])
            )
            ordenadas.append(proxima)
            atual = (proxima["latitude"], proxima["longitude"])
            restantes.remove(proxima)
        return ordenadas

    def _haversine(self, origem, destino):
        lat1, lon1 = float(origem[0]), float(origem[1])
        lat2, lon2 = float(destino[0]), float(destino[1])
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        )
        return round(self.RAIO_TERRA_KM * 2 * asin(sqrt(a)), 2)

    @staticmethod
    def _inteiro(valor, nome_campo, minimo=None):
        try:
            numero = int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O campo '{nome_campo}' deve ser um número inteiro.") from erro
        if minimo is not None and numero < minimo:
            raise ValueError(f"O campo '{nome_campo}' deve ser maior ou igual a {minimo}.")
        return numero
