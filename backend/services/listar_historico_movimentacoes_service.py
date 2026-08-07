from datetime import datetime

from repositories.movimentacao_repository import MovimentacaoRepository


class ListarHistoricoMovimentacoesService:
    def executar(self, produto_id=None, fornecedor_id=None,
                 data_inicio=None, data_fim=None):
        inicio = self._data(data_inicio, "data_inicio")
        fim = self._data(data_fim, "data_fim")

        if inicio and fim and inicio > fim:
            raise ValueError("A data inicial não pode ser maior que a data final.")

        return MovimentacaoRepository.buscar_historico(
            produto_id=self._inteiro(produto_id, "produto_id"),
            fornecedor_id=self._inteiro(fornecedor_id, "fornecedor_id"),
            data_inicio=inicio,
            data_fim=fim,
        )

    @staticmethod
    def _inteiro(valor, nome_campo):
        if valor in (None, ""):
            return None
        try:
            return int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O filtro '{nome_campo}' deve ser um número inteiro.") from erro

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
