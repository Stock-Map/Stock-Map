from datetime import date, datetime, timedelta

from repositories.relatorio_repository import RelatorioRepository


class GerarRelatorioService:
    DIAS_PADRAO = 30

    def executar(self, data_inicio=None, data_fim=None):
        fim = self._data(data_fim, "data_fim") or date.today()
        inicio = self._data(data_inicio, "data_inicio") or (
            fim - timedelta(days=self.DIAS_PADRAO)
        )

        if inicio > fim:
            raise ValueError("A data inicial não pode ser maior que a data final.")

        return {
            "periodo": {"data_inicio": inicio.isoformat(), "data_fim": fim.isoformat()},
            "resumo": RelatorioRepository.resumo(inicio, fim),
            "top_produtos": RelatorioRepository.top_produtos(inicio, fim),
            "desempenho_fornecedores": RelatorioRepository.desempenho_fornecedores(inicio, fim),
        }

    @staticmethod
    def _data(valor, nome_campo):
        if valor in (None, ""):
            return None
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date()
        except (TypeError, ValueError) as erro:
            raise ValueError(
                f"O filtro '{nome_campo}' deve estar no formato AAAA-MM-DD."
            ) from erro
