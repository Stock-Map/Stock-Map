# Stock Map

Sistema de gestao de estoque e logistica entre fornecedores e lojistas, com
alertas de reposicao, relatorios por periodo e roteirizacao de entregas.

Backend em Flask com SQLAlchemy, frontend em HTML, CSS e JavaScript puro
consumindo a API REST.

## Estrutura do projeto

```text
stock-map/
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js
│   └── img/
└── backend/
    ├── app.py
    ├── requirements.txt
    ├── controllers/
    ├── services/
    ├── repositories/
    ├── models/
    ├── scripts/smoke_test.sh
    └── database/
        └── create_database.sql
```

## Arquitetura

```text
Frontend
   ↓
Controller
   ↓
Service
   ↓
Model  ou  Repository → CALL sp_... → MySQL
```

- A **Model** representa a entidade do dominio e concentra o CRUD basico.
- O **Repository** encapsula tudo que vai alem do CRUD: filtros, buscas,
  ordenacoes, relatorios e juncoes entre tabelas, sempre por stored procedure.
- O **Service** implementa um caso de uso por classe, com o metodo `executar()`.
- O **Controller** recebe a requisicao HTTP e delega ao Service.

Controller e Service nunca chamam procedure diretamente. Quem conhece o
`CALL sp_...` e o Repository.

## Funcionalidades implementadas

CRUD basico (camada Model):

- cadastrar, listar, buscar, atualizar e remover fornecedores;
- cadastrar, listar, buscar, atualizar e remover lojistas;
- cadastrar, buscar, atualizar e remover produtos;
- registrar pedidos com multiplos itens, com baixa automatica de estoque;
- alterar o status do pedido, devolvendo o estoque no cancelamento;
- ajustar o estoque de um produto, gerando a movimentacao correspondente.

Alem do CRUD (camada Repository, por procedure):

- listar produtos com filtro por fornecedor, busca textual e status de estoque
  calculado;
- listar alertas de estoque baixo ordenados por severidade;
- filtrar pedidos por status, lojista e intervalo de datas;
- consultar o detalhe de um pedido com seus itens;
- gerar relatorio por periodo com resumo, ranking de produtos e desempenho por
  fornecedor;
- selecionar pedidos aptos a roteirizacao e listar rotas com suas paradas;
- consultar o historico de movimentacoes de estoque com filtro por produto,
  fornecedor e periodo.

## Procedures criadas

| Procedure | Parametros | Uso |
|---|---|---|
| `sp_produtos_com_status` | `p_fornecedor_id`, `p_busca` | Produtos ativos com fornecedor e status de estoque |
| `sp_alertas_estoque_baixo` | — | Produtos no limite ou zerados, por severidade |
| `sp_relatorio_resumo` | `p_data_inicio`, `p_data_fim` | Contadores gerais e faturamento do periodo |
| `sp_relatorio_top_produtos` | `p_data_inicio`, `p_data_fim` | Ranking de produtos por demanda |
| `sp_relatorio_desempenho_fornecedores` | `p_data_inicio`, `p_data_fim` | Pedidos e faturamento por fornecedor |
| `sp_pedidos_filtrados` | `p_status`, `p_lojista_id`, `p_data_inicio`, `p_data_fim` | Pedidos com filtros e contagem de itens |
| `sp_pedido_detalhe` | `p_pedido_id` | Cabecalho do pedido com lojista e fornecedor |
| `sp_pedido_itens` | `p_pedido_id` | Itens do pedido com nome e SKU |
| `sp_pedidos_para_roteirizar` | `p_fornecedor_id` | Pedidos confirmados com coordenadas do lojista |
| `sp_rotas_listar` | — | Rotas com fornecedor e numero de paradas |
| `sp_rota_paradas` | `p_rota_id` | Paradas de uma rota, em ordem |
| `sp_historico_movimentacoes` | `p_produto_id`, `p_fornecedor_id`, `p_data_inicio`, `p_data_fim` | Entradas, saidas e ajustes de estoque |

Todas estao em `backend/database/create_database.sql`.

## Models

| Model | Tabela | Responsabilidade |
|---|---|---|
| `Fornecedor` | `fornecedores` | Fornecedor, com localizacao para roteirizacao |
| `Lojista` | `lojistas` | Lojista que faz pedidos |
| `Produto` | `produtos` | Item de estoque de um fornecedor |
| `Pedido` | `pedidos` | Pedido de um lojista a um fornecedor |
| `ItemPedido` | `itens_pedido` | Linha de produto dentro do pedido |
| `MovimentacaoEstoque` | `movimentacoes_estoque` | Entrada, saida ou ajuste de estoque |
| `RotaEntrega` | `rotas_entrega` | Rota planejada para um fornecedor |
| `ParadaRota` | `paradas_rota` | Parada da rota, com ordem e distancia |

## Repositories

| Repository | Metodos | Procedures |
|---|---|---|
| `ProdutoRepository` | `buscar_com_status` | `sp_produtos_com_status` |
| `PedidoRepository` | `buscar_filtrados`, `buscar_detalhe`, `buscar_itens` | `sp_pedidos_filtrados`, `sp_pedido_detalhe`, `sp_pedido_itens` |
| `AlertaRepository` | `listar_estoque_baixo` | `sp_alertas_estoque_baixo` |
| `RelatorioRepository` | `resumo`, `top_produtos`, `desempenho_fornecedores` | as tres `sp_relatorio_*` |
| `RotaRepository` | `pedidos_para_roteirizar`, `listar_com_paradas` | `sp_pedidos_para_roteirizar`, `sp_rotas_listar`, `sp_rota_paradas` |
| `MovimentacaoRepository` | `buscar_historico` | `sp_historico_movimentacoes` |

## Rotas da API

| Metodo | Rota | Descricao |
|---|---|---|
| GET | `/` | Informacoes da API |
| GET | `/fornecedores` | Lista fornecedores |
| POST | `/fornecedores` | Cadastra fornecedor |
| GET | `/fornecedores/<id>` | Busca fornecedor por id |
| PUT | `/fornecedores/<id>` | Atualiza fornecedor |
| DELETE | `/fornecedores/<id>` | Remove fornecedor |
| GET | `/lojistas` | Lista lojistas |
| POST | `/lojistas` | Cadastra lojista |
| GET | `/lojistas/<id>` | Busca lojista por id |
| PUT | `/lojistas/<id>` | Atualiza lojista |
| DELETE | `/lojistas/<id>` | Remove lojista |
| GET | `/produtos?fornecedor_id=&busca=` | Lista produtos com filtro e status (Repository) |
| POST | `/produtos` | Cadastra produto |
| GET | `/produtos/<id>` | Busca produto por id |
| PUT | `/produtos/<id>` | Atualiza produto |
| DELETE | `/produtos/<id>` | Desativa produto |
| PATCH | `/produtos/<id>/estoque` | Ajusta estoque e registra movimentacao |
| GET | `/pedidos?status=&lojista_id=&data_inicio=&data_fim=` | Lista pedidos com filtros (Repository) |
| POST | `/pedidos` | Registra pedido e da baixa no estoque |
| GET | `/pedidos/<id>` | Detalhe do pedido com itens (Repository) |
| PATCH | `/pedidos/<id>/status` | Altera status e devolve estoque no cancelamento |
| GET | `/alertas` | Alertas de estoque baixo (Repository) |
| GET | `/relatorios?data_inicio=&data_fim=` | Relatorio por periodo (Repository) |
| GET | `/rotas` | Rotas com paradas (Repository) |
| POST | `/rotas` | Planeja rota por vizinho mais proximo |
| GET | `/movimentacoes?produto_id=&fornecedor_id=&data_inicio=&data_fim=` | Historico de estoque (Repository) |

Respostas de sucesso retornam o objeto ou array direto. Erros retornam
`{"erro": "mensagem"}`, com status 400 para entrada invalida, 404 para registro
inexistente e 500 para falha de banco.

## Como executar o backend

Entre na pasta do backend:

```bash
cd backend
```

Crie e ative o ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

No Windows, use `.venv\Scripts\activate`.

Instale as dependencias:

```bash
pip install -r requirements.txt
```

Crie o arquivo `.env` a partir do exemplo e ajuste a conexao:

```bash
cp .env.example .env
```

```text
DATABASE_URL=mysql+pymysql://usuario:senha@127.0.0.1:3306/stock_map
```

Crie o banco, o seed e as procedures:

```bash
mysql -u root -p < database/create_database.sql
```

Execute a API:

```bash
python app.py
```

A API fica disponivel em `http://127.0.0.1:5000`.

## Como executar o frontend

Em outro terminal:

```bash
cd frontend
python -m http.server 5500
```

Acesse `http://127.0.0.1:5500`.

O `js/app.js` detecta o ambiente: na porta 5500 ele aponta para
`http://127.0.0.1:5000`; publicado, usa a mesma origem.

## Smoke test

Com a API no ar:

```bash
BASE_URL=http://127.0.0.1:5000 bash backend/scripts/smoke_test.sh
```

## Exemplo de JSON para registrar um pedido

```json
{
  "lojista_id": 1,
  "fornecedor_id": 1,
  "endereco_entrega": "Rua da Bahia, 900",
  "observacoes": "Entregar pela manha",
  "itens": [
    { "produto_id": 1, "quantidade": 5 }
  ]
}
```
