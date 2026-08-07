#!/usr/bin/env bash
# Smoke test das rotas da API Stock Map.
# Uso: BASE_URL=http://127.0.0.1:5001 bash backend/scripts/smoke_test.sh

set -u

BASE_URL="${BASE_URL:-http://127.0.0.1:5001}"
FALHAS=0

verificar() {
    local descricao="$1"
    local esperado="$2"
    local obtido="$3"

    if [ "$esperado" = "$obtido" ]; then
        printf 'ok    %-52s %s\n' "$descricao" "$obtido"
    else
        printf 'FALHA %-52s esperado %s, obtido %s\n' "$descricao" "$esperado" "$obtido"
        FALHAS=$((FALHAS + 1))
    fi
}

codigo() {
    curl -s -o /dev/null -w '%{http_code}' "$@"
}

echo "Smoke test em $BASE_URL"
echo

verificar "GET /"                    200 "$(codigo "$BASE_URL/")"
verificar "GET /fornecedores"        200 "$(codigo "$BASE_URL/fornecedores")"
verificar "GET /lojistas"            200 "$(codigo "$BASE_URL/lojistas")"
verificar "GET /produtos"            200 "$(codigo "$BASE_URL/produtos")"
verificar "GET /pedidos"             200 "$(codigo "$BASE_URL/pedidos")"
verificar "GET /alertas"             200 "$(codigo "$BASE_URL/alertas")"
verificar "GET /relatorios"          200 "$(codigo "$BASE_URL/relatorios")"
verificar "GET /rotas"               200 "$(codigo "$BASE_URL/rotas")"
verificar "GET /movimentacoes"       200 "$(codigo "$BASE_URL/movimentacoes")"

verificar "GET /fornecedores/999999 (inexistente)" 404 \
    "$(codigo "$BASE_URL/fornecedores/999999")"
verificar "GET /pedidos?status=invalido"           400 \
    "$(codigo "$BASE_URL/pedidos?status=invalido")"
verificar "GET /relatorios?data_inicio=01-01-2020" 400 \
    "$(codigo "$BASE_URL/relatorios?data_inicio=01-01-2020")"

# Filtros das procedures devolvem subconjuntos coerentes.
TOTAL_PRODUTOS=$(curl -s "$BASE_URL/produtos" | grep -o '"id"' | wc -l)
BUSCA_PRODUTOS=$(curl -s "$BASE_URL/produtos?busca=Arroz" | grep -o '"id"' | wc -l)
if [ "$BUSCA_PRODUTOS" -lt "$TOTAL_PRODUTOS" ] && [ "$BUSCA_PRODUTOS" -ge 1 ]; then
    printf 'ok    %-52s %s de %s\n' "GET /produtos?busca=Arroz filtra" \
        "$BUSCA_PRODUTOS" "$TOTAL_PRODUTOS"
else
    printf 'FALHA %-52s %s de %s\n' "GET /produtos?busca=Arroz filtra" \
        "$BUSCA_PRODUTOS" "$TOTAL_PRODUTOS"
    FALHAS=$((FALHAS + 1))
fi

# Ciclo de escrita: cria fornecedor, rejeita incompleto, remove.
CRIACAO=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_URL/fornecedores" \
    -H 'Content-Type: application/json' \
    -d '{"nome":"Smoke Test Ltda","nome_contato":"Robo","email":"smoke@teste.local"}')
verificar "POST /fornecedores" 201 "$CRIACAO"

verificar "POST /fornecedores sem campo obrigatorio" 400 \
    "$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_URL/fornecedores" \
        -H 'Content-Type: application/json' -d '{"nome":"Incompleto"}')"

ID_SMOKE=$(curl -s "$BASE_URL/fornecedores" | \
    python3 -c "import sys,json; ids=[f['id'] for f in json.load(sys.stdin) if f['email']=='smoke@teste.local']; print(ids[0] if ids else '')")

if [ -n "$ID_SMOKE" ]; then
    verificar "DELETE /fornecedores/<id>" 204 \
        "$(codigo -X DELETE "$BASE_URL/fornecedores/$ID_SMOKE")"
else
    printf 'FALHA %-52s fornecedor de teste nao encontrado\n' "DELETE /fornecedores/<id>"
    FALHAS=$((FALHAS + 1))
fi

echo
if [ "$FALHAS" -eq 0 ]; then
    echo "Todos os testes passaram."
    exit 0
fi
echo "$FALHAS teste(s) falharam."
exit 1
