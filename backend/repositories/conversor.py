from datetime import date, datetime
from decimal import Decimal


def converter_linha(linha):
    """Normaliza uma linha de procedure para tipos serializaveis em JSON."""
    if linha is None:
        return None

    resultado = {}
    for chave, valor in dict(linha).items():
        if isinstance(valor, Decimal):
            resultado[chave] = float(valor)
        elif isinstance(valor, (datetime, date)):
            resultado[chave] = valor.isoformat()
        else:
            resultado[chave] = valor
    return resultado


def converter_linhas(linhas):
    return [converter_linha(linha) for linha in linhas]
