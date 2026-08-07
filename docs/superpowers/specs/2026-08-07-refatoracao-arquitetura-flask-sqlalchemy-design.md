# Refatoração do Stock Map para a arquitetura Flask + SQLAlchemy

Data: 2026-08-07
Status: aprovado para implementação

## Contexto

O projeto Stock Map (fornecedores, lojistas, produtos, pedidos, rotas de entrega)
está hoje escrito com SQL cru em todas as camadas: os "models" são módulos de
funções que montam `INSERT`/`UPDATE` em string, os repositories concentram
`SELECT` com `JOIN`/`GROUP BY` também em string, e os services são funções soltas
em módulo. O acesso ao banco usa `mysql-connector` diretamente, sem ORM.

O professor apontou três problemas: models precisam ser classes SQLAlchemy, a
camada de service não é orientada a objeto, e o frontend não pode usar Jinja.
O enunciado da atividade acrescenta que toda consulta além do CRUD básico deve
ficar na camada Repository, implementada por procedures no banco, com Controller
e Service próprios por caso de uso.

O repositório de referência é
<https://github.com/gleisonbt/projeto-flask-sqlalchemy>, e a decisão do grupo é
que o projeto fique igual a esse padrão.

## Objetivo

Reescrever o backend e o frontend do Stock Map seguindo exatamente o padrão do
repositório de referência, preservando o domínio e as funcionalidades atuais e
acrescentando três funcionalidades não-CRUD novas.

## Decisões tomadas

1. Refatorar o projeto inteiro de uma vez, não incrementalmente.
2. Tabelas criadas por `db.create_all()` a partir dos models. O script SQL
   espelha as tabelas com `CREATE TABLE IF NOT EXISTS`, além de criar o
   database, carregar o seed e instalar as procedures — mesma redundância da
   referência, necessária para o script rodar sozinho pelo cliente `mysql`.
3. Frontend totalmente separado do Flask, consumindo a API por `fetch`, com CORS
   habilitado no backend.
4. Identificadores em português, iguais à referência (classes, arquivos, tabelas,
   colunas e campos JSON).
5. Três funcionalidades novas: histórico de movimentação de estoque, filtro de
   pedidos e relatório por período.
6. Em produção, o nginx passa a servir o frontend estático e faz proxy apenas das
   rotas de recurso para o gunicorn.

O banco atual contém apenas dados de exemplo (2 fornecedores, 2 lojistas,
3 produtos, 1 pedido, 4 movimentações), então a renomeação para português não
exige migração de dados: o banco é recriado a partir do script e do seed.

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

Regras de fronteira:

- Controller nunca fala com Model ou Repository, apenas com Service.
- Service nunca escreve `CALL` nem SQL; ou usa a Model, ou usa o Repository.
- Apenas o Repository conhece o nome das procedures.
- CRUD básico vive nos métodos da Model.

## Estrutura de diretórios

```text
stock-map/
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js
│   └── img/stockmap-logo.svg
└── backend/
    ├── app.py
    ├── requirements.txt
    ├── .env.example
    ├── database/
    │   └── create_database.sql
    ├── models/
    │   ├── database.py
    │   ├── fornecedor_model.py
    │   ├── lojista_model.py
    │   ├── produto_model.py
    │   ├── pedido_model.py
    │   ├── movimentacao_estoque_model.py
    │   └── rota_model.py
    ├── repositories/
    │   ├── produto_repository.py
    │   ├── pedido_repository.py
    │   ├── alerta_repository.py
    │   ├── relatorio_repository.py
    │   ├── rota_repository.py
    │   └── movimentacao_repository.py
    ├── services/
    └── controllers/
```

`models/__init__.py`, `repositories/__init__.py`, `services/__init__.py` e
`controllers/__init__.py` ficam vazios, como na referência. O registro dos
blueprints acontece no `app.py`.

## Modelo de dados

O nome do banco continua `stock_map`. Tabelas e classes renomeadas:

| Tabela atual | Tabela nova | Classe |
|---|---|---|
| suppliers | fornecedores | `Fornecedor` |
| retailers | lojistas | `Lojista` |
| products | produtos | `Produto` |
| orders | pedidos | `Pedido` |
| order_items | itens_pedido | `ItemPedido` |
| stock_movements | movimentacoes_estoque | `MovimentacaoEstoque` |
| delivery_routes | rotas_entrega | `RotaEntrega` |
| route_stops | paradas_rota | `ParadaRota` |

### Colunas

`Fornecedor` e `Lojista`: `id`, `nome`, `cnpj`, `nome_contato`, `email`,
`telefone`, `endereco`, `cidade`, `estado`, `latitude`, `longitude`,
`criado_em`, `atualizado_em`. `email` é único.

`Produto`: `id`, `fornecedor_id`, `sku`, `nome`, `categoria`, `preco_unitario`,
`quantidade`, `estoque_minimo`, `prazo_entrega_dias`, `ativo`, `criado_em`,
`atualizado_em`. Único composto em (`fornecedor_id`, `sku`).

`Pedido`: `id`, `lojista_id`, `fornecedor_id`, `status`, `observacoes`,
`valor_total`, `endereco_entrega`, `criado_em`, `atualizado_em`. Status possíveis:
`pendente`, `confirmado`, `despachado`, `entregue`, `cancelado`.

`ItemPedido`: `id`, `pedido_id`, `produto_id`, `quantidade`, `preco_unitario`,
`subtotal`.

`MovimentacaoEstoque`: `id`, `produto_id`, `fornecedor_id`, `tipo_movimentacao`
(`entrada`, `saida`, `ajuste`), `variacao_quantidade`, `motivo`,
`referencia_tipo`, `referencia_id`, `criado_em`.

`RotaEntrega`: `id`, `fornecedor_id`, `data_rota`, `status` (`planejada`,
`em_andamento`, `concluida`, `cancelada`), `distancia_total_km`, `observacoes`,
`criado_em`, `atualizado_em`.

`ParadaRota`: `id`, `rota_id`, `pedido_id`, `lojista_id`, `ordem_parada`,
`distancia_anterior_km`, `status` (`planejada`, `concluida`, `ignorada`),
`criado_em`.

### Métodos das Models

Cada model expõe o CRUD básico no padrão da referência:

- `salvar()` — `db.session.add(self)` e `commit()`
- `atualizar(**campos)` — altera apenas os campos informados e faz `commit()`
- `deletar()` — `db.session.delete(self)` e `commit()`
- `@staticmethod listar_todos()`
- `@staticmethod buscar_por_id(id)`
- buscas auxiliares por chave única (`buscar_por_email`, `buscar_por_sku`)
- `to_dict()` — serialização para JSON

## Procedures

Todas em `backend/database/create_database.sql`, criadas com `DELIMITER //`
e precedidas de `DROP PROCEDURE IF EXISTS`. Como `DELIMITER` é uma diretiva do
cliente `mysql` e não SQL de servidor, o script é executado por
`mysql -u root -p < backend/database/create_database.sql`. Os comandos CLI
`init-db` e `seed-db` do `app.py` atual deixam de existir.

| Procedure | Parâmetros | Uso |
|---|---|---|
| `sp_produtos_com_status` | `p_fornecedor_id`, `p_busca` | Lista produtos ativos com nome do fornecedor e status de estoque calculado |
| `sp_alertas_estoque_baixo` | — | Produtos com quantidade <= estoque mínimo, ordenados por severidade |
| `sp_relatorio_resumo` | `p_data_inicio`, `p_data_fim` | Contadores gerais e faturamento do período |
| `sp_relatorio_top_produtos` | `p_data_inicio`, `p_data_fim` | Ranking de produtos por demanda |
| `sp_relatorio_desempenho_fornecedores` | `p_data_inicio`, `p_data_fim` | Pedidos e faturamento por fornecedor |
| `sp_pedidos_filtrados` | `p_status`, `p_lojista_id`, `p_data_inicio`, `p_data_fim` | Lista pedidos com filtros e contagem de itens |
| `sp_pedido_detalhe` | `p_pedido_id` | Cabeçalho do pedido com nomes de lojista e fornecedor |
| `sp_pedido_itens` | `p_pedido_id` | Itens do pedido com nome e SKU do produto |
| `sp_pedidos_para_roteirizar` | `p_fornecedor_id` | Pedidos confirmados ou despachados com coordenadas do lojista |
| `sp_rotas_listar` | — | Rotas com nome do fornecedor e número de paradas |
| `sp_rota_paradas` | `p_rota_id` | Paradas de uma rota com dados do lojista |
| `sp_historico_movimentacoes` | `p_produto_id`, `p_fornecedor_id`, `p_data_inicio`, `p_data_fim` | Histórico de entradas, saídas e ajustes |

Parâmetros opcionais são tratados dentro da procedure com `IS NULL OR` para não
exigir SQL dinâmico.

## Repositories

Classes com métodos estáticos. Padrão de chamada:

```python
sql = text("CALL sp_produtos_com_status(:fornecedor_id, :busca)")
resultado = db.session.execute(sql, {"fornecedor_id": ..., "busca": ...})
linhas = resultado.mappings().all()
resultado.close()
return [dict(linha) for linha in linhas]
```

| Repository | Métodos |
|---|---|
| `ProdutoRepository` | `buscar_com_status(fornecedor_id, busca)` |
| `PedidoRepository` | `buscar_filtrados(status, lojista_id, data_inicio, data_fim)`, `buscar_detalhe(pedido_id)`, `buscar_itens(pedido_id)` |
| `AlertaRepository` | `listar_estoque_baixo()` |
| `RelatorioRepository` | `resumo(data_inicio, data_fim)`, `top_produtos(data_inicio, data_fim)`, `desempenho_fornecedores(data_inicio, data_fim)` |
| `RotaRepository` | `pedidos_para_roteirizar(fornecedor_id)`, `listar_com_paradas()` |
| `MovimentacaoRepository` | `buscar_historico(produto_id, fornecedor_id, data_inicio, data_fim)` |

Como as procedures retornam linhas agregadas de várias tabelas, os repositories
devolvem dicionários, não instâncias de model.

## Services

Uma classe por caso de uso, um arquivo por classe, método público `executar()`.

| Arquivo | Classe | Acessa |
|---|---|---|
| `criar_fornecedor_service.py` | `CriarFornecedorService` | Model |
| `listar_fornecedores_service.py` | `ListarFornecedoresService` | Model |
| `buscar_fornecedor_por_id_service.py` | `BuscarFornecedorPorIdService` | Model |
| `atualizar_fornecedor_service.py` | `AtualizarFornecedorService` | Model |
| `deletar_fornecedor_service.py` | `DeletarFornecedorService` | Model |
| `criar_lojista_service.py` | `CriarLojistaService` | Model |
| `listar_lojistas_service.py` | `ListarLojistasService` | Model |
| `buscar_lojista_por_id_service.py` | `BuscarLojistaPorIdService` | Model |
| `atualizar_lojista_service.py` | `AtualizarLojistaService` | Model |
| `deletar_lojista_service.py` | `DeletarLojistaService` | Model |
| `criar_produto_service.py` | `CriarProdutoService` | Model |
| `listar_produtos_service.py` | `ListarProdutosService` | Repository |
| `buscar_produto_por_id_service.py` | `BuscarProdutoPorIdService` | Model |
| `atualizar_produto_service.py` | `AtualizarProdutoService` | Model |
| `deletar_produto_service.py` | `DeletarProdutoService` | Model |
| `atualizar_estoque_produto_service.py` | `AtualizarEstoqueProdutoService` | Model |
| `criar_pedido_service.py` | `CriarPedidoService` | Model |
| `listar_pedidos_service.py` | `ListarPedidosService` | Repository |
| `buscar_pedido_por_id_service.py` | `BuscarPedidoPorIdService` | Repository |
| `atualizar_status_pedido_service.py` | `AtualizarStatusPedidoService` | Model |
| `listar_alertas_estoque_baixo_service.py` | `ListarAlertasEstoqueBaixoService` | Repository |
| `gerar_relatorio_service.py` | `GerarRelatorioService` | Repository |
| `planejar_rota_service.py` | `PlanejarRotaService` | Model + Repository |
| `listar_rotas_service.py` | `ListarRotasService` | Repository |
| `listar_historico_movimentacoes_service.py` | `ListarHistoricoMovimentacoesService` | Repository |

Validação de entrada acontece no service, levantando `ValueError` com mensagem
em português, como na referência. O módulo `services/validation.py` atual deixa
de existir; a validação vira responsabilidade de cada service.

### Regras de negócio preservadas

`CriarPedidoService`: valida lojista e fornecedor, exige ao menos um item, checa
que cada produto pertence ao fornecedor selecionado e que há estoque suficiente,
calcula subtotal e total, dá baixa no estoque e grava uma movimentação de saída
por item.

`AtualizarStatusPedidoService`: bloqueia mudança de status de pedido cancelado e,
ao cancelar, devolve o estoque de cada item gerando movimentação de entrada.

`AtualizarEstoqueProdutoService`: grava movimentação de ajuste com a diferença
entre a quantidade nova e a anterior.

`PlanejarRotaService`: calcula a ordem das paradas por vizinho mais próximo
usando distância de haversine a partir das coordenadas do fornecedor, com
fallback para ordenação por cidade quando faltam coordenadas.

### Transações

Os services que gravam em mais de uma tabela — `CriarPedidoService`,
`AtualizarStatusPedidoService` e `PlanejarRotaService` — não usam `salvar()` por
objeto, porque um commit por model deixaria o banco inconsistente se uma etapa
intermediária falhasse. Nesses três casos o service usa `db.session.add()` nos
objetos e um único `db.session.commit()` no fim, com `with_for_update()` na
leitura do produto para evitar venda concorrente do mesmo estoque. O restante do
projeto usa os métodos de CRUD da model normalmente.

Este é o único desvio consciente do padrão da referência, e existe porque a
referência só tem casos de uso de uma tabela.

## Controllers

Um blueprint por domínio, sem `url_prefix`. Cada rota trata `ValueError` como
400, `SQLAlchemyError` como 500 com `db.session.rollback()`, e ausência de
registro como 404. Respostas de sucesso retornam o objeto ou array direto, sem
envelope; erros retornam `{"erro": "mensagem"}`.

| Método | Rota | Service |
|---|---|---|
| GET | `/` | — (informativa) |
| GET | `/fornecedores` | `ListarFornecedoresService` |
| POST | `/fornecedores` | `CriarFornecedorService` |
| GET | `/fornecedores/<id>` | `BuscarFornecedorPorIdService` |
| PUT | `/fornecedores/<id>` | `AtualizarFornecedorService` |
| DELETE | `/fornecedores/<id>` | `DeletarFornecedorService` |
| GET | `/lojistas` | `ListarLojistasService` |
| POST | `/lojistas` | `CriarLojistaService` |
| GET | `/lojistas/<id>` | `BuscarLojistaPorIdService` |
| PUT | `/lojistas/<id>` | `AtualizarLojistaService` |
| DELETE | `/lojistas/<id>` | `DeletarLojistaService` |
| GET | `/produtos?fornecedor_id=&busca=` | `ListarProdutosService` |
| POST | `/produtos` | `CriarProdutoService` |
| GET | `/produtos/<id>` | `BuscarProdutoPorIdService` |
| PUT | `/produtos/<id>` | `AtualizarProdutoService` |
| DELETE | `/produtos/<id>` | `DeletarProdutoService` |
| PATCH | `/produtos/<id>/estoque` | `AtualizarEstoqueProdutoService` |
| GET | `/pedidos?status=&lojista_id=&data_inicio=&data_fim=` | `ListarPedidosService` |
| POST | `/pedidos` | `CriarPedidoService` |
| GET | `/pedidos/<id>` | `BuscarPedidoPorIdService` |
| PATCH | `/pedidos/<id>/status` | `AtualizarStatusPedidoService` |
| GET | `/alertas` | `ListarAlertasEstoqueBaixoService` |
| GET | `/relatorios?data_inicio=&data_fim=` | `GerarRelatorioService` |
| GET | `/rotas` | `ListarRotasService` |
| POST | `/rotas` | `PlanejarRotaService` |
| GET | `/movimentacoes?produto_id=&fornecedor_id=&data_inicio=&data_fim=` | `ListarHistoricoMovimentacoesService` |

`DELETE /produtos/<id>` é remoção lógica: marca `ativo = 0`, preservando o
histórico de pedidos que referenciam o produto.

## app.py

```python
def create_app():
    load_dotenv()
    app = Flask(__name__)
    CORS(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", ...)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    # registro dos 8 blueprints
    # rota GET / informativa
    with app.app_context():
        db.create_all()
    return app
```

`app = create_app()` no nível do módulo, para o gunicorn continuar servindo
`app:app` sem mudança no systemd.

### Dependências

`requirements.txt` passa a ser Flask, Flask-SQLAlchemy, Flask-Cors,
python-dotenv, PyMySQL e gunicorn. O `mysql-connector-python` sai. O gunicorn não
existe na referência, mas é mantido porque o serviço em produção depende dele.

### Configuração

`.env` passa a usar uma única variável de conexão:

```text
DATABASE_URL=mysql+pymysql://stock_map_app:senha@127.0.0.1:3306/stock_map
```

As variáveis `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` e `DB_NAME` saem.
O `EnvironmentFile` do systemd continua apontando para o mesmo arquivo.

## Frontend

Vira aplicação estática independente, sem nenhuma tag Jinja. Os caminhos de CSS,
JS e imagem passam a ser relativos (`css/style.css`, `js/app.js`,
`img/stockmap-logo.svg`).

A base da API é resolvida em tempo de execução:

```javascript
const API_URL =
  location.port === "5500" || location.protocol === "file:"
    ? "http://127.0.0.1:5000"
    : "";
```

Assim o mesmo arquivo funciona em desenvolvimento (front na 5500, API na 5000,
via CORS) e em produção (mesma origem, sem CORS).

O `app.js` é reescrito para o novo contrato: sem envelope `{ok, data}` — sucesso
é o próprio corpo, e erro é lido de `{"erro": ...}` com base no status HTTP. Os
nomes de campo passam a ser os do JSON em português.

### Telas

Mantidas: Painel, Fornecedores, Lojistas, Produtos, Alertas, Rotas.

Alteradas:

- **Pedidos** ganha barra de filtros com status, lojista e intervalo de datas,
  chamando `GET /pedidos` com os parâmetros.
- **Relatórios** ganha seletor de data inicial e final, com padrão de 30 dias,
  chamando `GET /relatorios`.

Nova:

- **Movimentações** lista o histórico de entradas, saídas e ajustes, com filtros
  por produto, fornecedor e período, chamando `GET /movimentacoes`.

## Deploy

`stockmap.service` não muda. O nginx de `stockmap.easytechnl.com.br` passa a ter:

- `root /home/stock-map/frontend;` com `location /` servindo os arquivos
  estáticos;
- `location` de proxy para o gunicorn em `/fornecedores`, `/lojistas`,
  `/produtos`, `/pedidos`, `/alertas`, `/relatorios`, `/rotas` e
  `/movimentacoes`.

Como o front usa origem relativa em produção, não há CORS envolvido no domínio
publicado.

### Convivência durante a refatoração

As tabelas novas têm nomes diferentes das antigas, então as duas gerações
convivem no mesmo banco `stock_map`. O serviço em produção continua rodando o
código antigo sobre as tabelas em inglês enquanto a refatoração acontece. O
`.env` ganha `DATABASE_URL` sem perder as variáveis `DB_*` até o cutover, e o
servidor de desenvolvimento roda na porta 5001 para não colidir com o gunicorn
na 5000.

O cutover é a última tarefa: reiniciar o `stockmap.service`, aplicar o novo
`server` block do nginx, remover as variáveis `DB_*` do `.env` e só então
derrubar as tabelas antigas.

## Verificação

Não existe suíte de testes no projeto e a atividade não exige uma. A verificação
é feita por um script de smoke test em `backend/scripts/smoke_test.sh`, que sobe
a API e exercita cada rota com `curl`, conferindo os códigos de status e o
formato do corpo. O roteiro mínimo:

1. Recriar o banco com `create_database.sql` e subir a API.
2. `GET /fornecedores`, `/lojistas`, `/produtos`, `/alertas`, `/relatorios`,
   `/rotas`, `/movimentacoes` respondem 200 com array ou objeto.
3. `POST /fornecedores` e `POST /produtos` respondem 201.
4. `POST /pedidos` com estoque insuficiente responde 400 com `{"erro": ...}`.
5. `POST /pedidos` válido responde 201, e o estoque do produto cai na mesma
   proporção, com movimentação de saída registrada.
6. `PATCH /pedidos/<id>/status` para `cancelado` devolve o estoque.
7. `GET /produtos?busca=` e `GET /pedidos?status=` retornam subconjuntos
   coerentes, provando que as procedures recebem os parâmetros.
8. Abrir o frontend na 5500 e percorrer as nove telas.

## README

O README da raiz é reescrito com: descrição do projeto, estrutura de pastas,
diagrama de camadas, lista de funcionalidades implementadas, tabela de
procedures, tabela de rotas, tabela de models e repositories, e instruções de
execução de backend e frontend.

## Fora de escopo

- Migrations com Alembic.
- Autenticação e autorização.
- Testes automatizados.
- Mudanças no `stockmap.service`.
