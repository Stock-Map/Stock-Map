# Refatoração do Stock Map para Flask + SQLAlchemy — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reescrever o backend e o frontend do Stock Map na arquitetura do repositório de referência `gleisonbt/projeto-flask-sqlalchemy` — models como classes `db.Model`, repositories chamando stored procedures, services orientados a objeto por caso de uso, frontend estático sem Jinja.

**Architecture:** `Frontend → Controller → Service → Model` para CRUD básico, e `Frontend → Controller → Service → Repository → CALL sp_... → MySQL` para tudo que envolve filtro, JOIN, agregação, ordenação ou relatório. Somente o Repository conhece o nome das procedures; o Controller nunca fala com Model nem com Repository.

**Tech Stack:** Python 3.10, Flask 3, Flask-SQLAlchemy 3.1, Flask-Cors, PyMySQL, MariaDB, HTML/CSS/JavaScript puro, gunicorn + nginx em produção.

**Spec:** `docs/superpowers/specs/2026-08-07-refatoracao-arquitetura-flask-sqlalchemy-design.md`

## Global Constraints

- Identificadores em português: classes, arquivos, tabelas, colunas e campos JSON.
- Nome do banco continua `stock_map`. Não renomear o banco.
- Respostas de sucesso são o objeto ou array direto, **sem envelope** `{ok, data}`. Erros são `{"erro": "mensagem"}`.
- Mensagens de erro em português, com acento.
- Blueprints **sem** `url_prefix`. As rotas são `/fornecedores`, `/produtos`, etc — sem `/api`.
- `models/__init__.py`, `repositories/__init__.py`, `services/__init__.py` e `controllers/__init__.py` ficam **vazios**. O registro dos blueprints acontece no `app.py`.
- Um arquivo por service, uma classe por service, método público sempre chamado `executar()`.
- Controller trata `ValueError` como 400, `SQLAlchemyError` como 500 com `db.session.rollback()`, e `None` do service como 404.
- Nenhum `CALL` ou SQL cru fora da pasta `repositories/`.
- O serviço em produção (`stockmap.service`, gunicorn na 5000) continua rodando o código antigo até a Task 18. Durante todo o resto do plano, o servidor de desenvolvimento roda na **porta 5001**.
- As tabelas novas (português) convivem com as antigas (inglês) no mesmo banco. **Não derrubar as tabelas antigas antes da Task 18.**
- Não remover `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` do `.env` antes da Task 18 — o código antigo em produção depende delas.
- Commits em português, sem acento na primeira linha, prefixo `feat:`, `refactor:`, `docs:` ou `chore:`.
- **Toda coluna `criado_em` e `atualizado_em` precisa de `server_default=db.func.current_timestamp()`** além do `default=datetime.now` do Python. Como o `db.create_all()` roda antes do script SQL, o `CREATE TABLE IF NOT EXISTS` do script vira no-op e o `DEFAULT CURRENT_TIMESTAMP` dele nunca é aplicado. Sem o `server_default` no model, o seed em SQL grava data-zero (`0000-00-00 00:00:00`), que o PyMySQL devolve como `str` e quebra o `.isoformat()` do `to_dict()`.

## Estrutura de arquivos

```text
stock-map/
├── frontend/
│   ├── index.html                          movido e reescrito (Task 14)
│   ├── css/style.css                       movido de static/css/styles.css
│   ├── js/app.js                           movido (Task 14), reescrito (Task 15)
│   └── img/stockmap-logo.svg               movido de static/img/
└── backend/
    ├── app.py                              nasce como app_novo.py (Task 1), promovido (Task 16)
    ├── requirements.txt                    reescrito (Task 1)
    ├── .env.example                         reescrito (Task 1)
    ├── database/create_database.sql        reescrito (Task 6)
    ├── scripts/smoke_test.sh               novo (Task 16)
    ├── models/
    │   ├── database.py                     db = SQLAlchemy()
    │   ├── fornecedor_model.py             Fornecedor
    │   ├── lojista_model.py                Lojista
    │   ├── produto_model.py                Produto
    │   ├── pedido_model.py                 Pedido, ItemPedido
    │   ├── movimentacao_estoque_model.py   MovimentacaoEstoque
    │   └── rota_model.py                   RotaEntrega, ParadaRota
    ├── repositories/
    │   ├── conversor.py                    normaliza Decimal/datetime das procedures
    │   ├── produto_repository.py
    │   ├── pedido_repository.py
    │   ├── alerta_repository.py
    │   ├── relatorio_repository.py
    │   ├── rota_repository.py
    │   └── movimentacao_repository.py
    ├── services/                            25 arquivos, um por caso de uso
    └── controllers/                         8 blueprints
```

Arquivos removidos na Task 16: `database/connection.py`, `database/seed.sql`, os 6 models antigos, os 5 repositories antigos, os 7 services antigos, `services/validation.py`, os 8 controllers antigos, `controllers/helpers.py`. As pastas `frontend/templates/` e `frontend/static/` são desmontadas na Task 14.

## Ambiente de verificação

Todas as tarefas usam o venv existente e um servidor de desenvolvimento na porta 5001:

```bash
cd /home/stock-map/backend
/home/stock-map/.venv/bin/python -m flask --app app run --port 5001
```

Credenciais do banco saem do `.env` já existente.

---

### Task 1: Base do projeto — dependências, configuração e app.py

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`
- Modify: `backend/.env`
- Create: `backend/models/database.py`
- Create: `backend/app_novo.py`

**Interfaces:**
- Consumes: nada.
- Produces: `models.database.db` — instância `SQLAlchemy()` compartilhada por models e repositories. `app_novo.create_app()` — fábrica do Flask; vira `app.py` na Task 15.

O `app.py` antigo continua intocado nesta tarefa porque o gunicorn em produção o está executando. O novo nasce como `app_novo.py` e assume o nome definitivo só na Task 16.

- [ ] **Step 1: Reescrever `backend/requirements.txt`**

```text
Flask>=3.0,<4
Flask-SQLAlchemy>=3.1,<4
Flask-Cors>=4.0,<7
PyMySQL>=1.1,<2
python-dotenv>=1.0,<2
gunicorn>=22,<24
```

O `mysql-connector-python` sai da lista. Não desinstalar do venv ainda — o código antigo em produção usa.

- [ ] **Step 2: Instalar as dependências novas**

Run:
```bash
/home/stock-map/.venv/bin/pip install -r /home/stock-map/backend/requirements.txt
```
Expected: instala `Flask-SQLAlchemy`, `Flask-Cors`, `PyMySQL`; os demais já satisfeitos.

- [ ] **Step 3: Reescrever `backend/.env.example`**

```text
# Conexao unica usada pelo SQLAlchemy.
DATABASE_URL=mysql+pymysql://usuario:senha@127.0.0.1:3306/stock_map

SECRET_KEY=troque-esta-chave
FLASK_DEBUG=True
```

- [ ] **Step 4: Acrescentar `DATABASE_URL` ao `backend/.env`**

Ler o `.env` atual, montar a URL com os valores de `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` e `DB_NAME` que já estão lá, e acrescentar a linha ao final. **Manter as variáveis `DB_*` existentes** — o código antigo em produção depende delas até a Task 18.

Linha a acrescentar (com a senha real do arquivo):
```text
DATABASE_URL=mysql+pymysql://stock_map_app:SENHA_ATUAL@127.0.0.1:3306/stock_map
```

Se a senha tiver caractere especial (`@`, `:`, `/`, `#`), aplicar percent-encoding.

- [ ] **Step 5: Criar `backend/models/database.py`**

```python
from flask_sqlalchemy import SQLAlchemy

# Objeto compartilhado por toda a aplicacao. Inicializado no app.py.
db = SQLAlchemy()
```

- [ ] **Step 6: Criar `backend/app_novo.py`**

Os blueprints ainda não existem; entram nas Tasks 8 a 13. Esta versão sobe com a rota informativa e o `create_all`.

```python
import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

from models.database import db
from models import (  # noqa: F401  (registra os mapeamentos no SQLAlchemy)
    fornecedor_model,
    lojista_model,
    produto_model,
    pedido_model,
    movimentacao_estoque_model,
    rota_model,
)


def create_app():
    load_dotenv(override=True)

    app = Flask(__name__)
    CORS(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

    db.init_app(app)

    @app.get("/")
    def home():
        return jsonify({
            "mensagem": "API Stock Map - Flask + SQLAlchemy",
            "rotas": {
                "fornecedores": "GET|POST /fornecedores",
                "lojistas": "GET|POST /lojistas",
                "produtos": "GET /produtos?fornecedor_id=&busca=",
                "pedidos": "GET /pedidos?status=&lojista_id=&data_inicio=&data_fim=",
                "alertas": "GET /alertas",
                "relatorios": "GET /relatorios?data_inicio=&data_fim=",
                "rotas": "GET|POST /rotas",
                "movimentacoes": "GET /movimentacoes?produto_id=&fornecedor_id=&data_inicio=&data_fim=",
            },
        })

    with app.app_context():
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "True") == "True"
    app.run(debug=debug, host="0.0.0.0", port=5000)
```

O import de `models` vai falhar até a Task 5 criar os seis arquivos. Isso é esperado; a verificação desta tarefa é só do `database.py`.

- [ ] **Step 7: Verificar que o SQLAlchemy carrega**

Run:
```bash
cd /home/stock-map/backend && /home/stock-map/.venv/bin/python -c "
from models.database import db
print('ok', type(db).__name__)
"
```
Expected: `ok SQLAlchemy`

- [ ] **Step 8: Verificar que a URL de conexão funciona**

Run:
```bash
cd /home/stock-map/backend && /home/stock-map/.venv/bin/python -c "
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
load_dotenv(override=True)
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conexao:
    print(conexao.execute(text('SELECT DATABASE()')).scalar())
"
```
Expected: `stock_map`

- [ ] **Step 9: Confirmar que produção continua no ar**

Run: `curl -s -o /dev/null -w "%{http_code}\n" https://stockmap.easytechnl.com.br/api/health`
Expected: `200`

- [ ] **Step 10: Commit**

```bash
cd /home/stock-map
git add backend/requirements.txt backend/.env.example backend/models/database.py backend/app_novo.py
git commit -m "feat: adiciona base do SQLAlchemy e fabrica do app"
```

O `.env` não entra no commit (está no `.gitignore`).

---

### Task 2: Models Fornecedor e Lojista

**Files:**
- Create: `backend/models/fornecedor_model.py`
- Create: `backend/models/lojista_model.py`

**Interfaces:**
- Consumes: `models.database.db`.
- Produces:
  - `Fornecedor(db.Model)` — `salvar()`, `atualizar(**campos)`, `deletar()`, `Fornecedor.listar_todos()`, `Fornecedor.buscar_por_id(id)`, `Fornecedor.buscar_por_email(email)`, `to_dict()`.
  - `Lojista(db.Model)` — mesma superfície.

- [ ] **Step 1: Criar `backend/models/fornecedor_model.py`**

```python
from datetime import datetime

from .database import db


class Fornecedor(db.Model):
    __tablename__ = "fornecedores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(140), nullable=False)
    cnpj = db.Column(db.String(24))
    nome_contato = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True)
    telefone = db.Column(db.String(40))
    endereco = db.Column(db.String(220))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(40))
    latitude = db.Column(db.Numeric(10, 7))
    longitude = db.Column(db.Numeric(10, 7))
    criado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now,
        server_default=db.func.current_timestamp(),
    )
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now,
        server_default=db.func.current_timestamp(),
    )

    def salvar(self):
        """CREATE: salva um novo fornecedor no banco."""
        db.session.add(self)
        db.session.commit()

    def atualizar(self, **campos):
        """UPDATE: altera apenas os campos informados."""
        permitidos = (
            "nome", "cnpj", "nome_contato", "email", "telefone",
            "endereco", "cidade", "estado", "latitude", "longitude",
        )
        for nome_campo, valor in campos.items():
            if nome_campo in permitidos and valor is not None:
                setattr(self, nome_campo, valor)
        db.session.commit()

    def deletar(self):
        """DELETE: remove o fornecedor do banco."""
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna todos os fornecedores ordenados por nome."""
        return Fornecedor.query.order_by(Fornecedor.nome.asc()).all()

    @staticmethod
    def buscar_por_id(id):
        """READ: busca um fornecedor pelo id."""
        return db.session.get(Fornecedor, id)

    @staticmethod
    def buscar_por_email(email):
        """READ auxiliar: busca um fornecedor pelo e-mail."""
        return Fornecedor.query.filter_by(email=email).first()

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "cnpj": self.cnpj,
            "nome_contato": self.nome_contato,
            "email": self.email,
            "telefone": self.telefone,
            "endereco": self.endereco,
            "cidade": self.cidade,
            "estado": self.estado,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }
```

- [ ] **Step 2: Criar `backend/models/lojista_model.py`**

```python
from datetime import datetime

from .database import db


class Lojista(db.Model):
    __tablename__ = "lojistas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(140), nullable=False)
    cnpj = db.Column(db.String(24))
    nome_contato = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True)
    telefone = db.Column(db.String(40))
    endereco = db.Column(db.String(220))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(40))
    latitude = db.Column(db.Numeric(10, 7))
    longitude = db.Column(db.Numeric(10, 7))
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    def salvar(self):
        """CREATE: salva um novo lojista no banco."""
        db.session.add(self)
        db.session.commit()

    def atualizar(self, **campos):
        """UPDATE: altera apenas os campos informados."""
        permitidos = (
            "nome", "cnpj", "nome_contato", "email", "telefone",
            "endereco", "cidade", "estado", "latitude", "longitude",
        )
        for nome_campo, valor in campos.items():
            if nome_campo in permitidos and valor is not None:
                setattr(self, nome_campo, valor)
        db.session.commit()

    def deletar(self):
        """DELETE: remove o lojista do banco."""
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna todos os lojistas ordenados por nome."""
        return Lojista.query.order_by(Lojista.nome.asc()).all()

    @staticmethod
    def buscar_por_id(id):
        """READ: busca um lojista pelo id."""
        return db.session.get(Lojista, id)

    @staticmethod
    def buscar_por_email(email):
        """READ auxiliar: busca um lojista pelo e-mail."""
        return Lojista.query.filter_by(email=email).first()

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "cnpj": self.cnpj,
            "nome_contato": self.nome_contato,
            "email": self.email,
            "telefone": self.telefone,
            "endereco": self.endereco,
            "cidade": self.cidade,
            "estado": self.estado,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }
```

- [ ] **Step 3: Verificar que as classes carregam**

Run:
```bash
cd /home/stock-map/backend && /home/stock-map/.venv/bin/python -c "
from models.fornecedor_model import Fornecedor
from models.lojista_model import Lojista
print(Fornecedor.__tablename__, Lojista.__tablename__)
print([c.name for c in Fornecedor.__table__.columns])
"
```
Expected: `fornecedores lojistas` seguido da lista de 13 colunas em português.

- [ ] **Step 4: Commit**

```bash
cd /home/stock-map
git add backend/models/fornecedor_model.py backend/models/lojista_model.py
git commit -m "feat: adiciona models Fornecedor e Lojista com SQLAlchemy"
```

---

### Task 3: Model Produto

**Files:**
- Create: `backend/models/produto_model.py`

**Interfaces:**
- Consumes: `models.database.db`, `Fornecedor` (por nome, via `db.ForeignKey("fornecedores.id")`).
- Produces: `Produto(db.Model)` — `salvar()`, `atualizar(**campos)`, `deletar()`, `desativar()`, `Produto.listar_todos()`, `Produto.buscar_por_id(id)`, `Produto.buscar_por_sku(fornecedor_id, sku)`, `Produto.buscar_para_atualizacao(id)`, `to_dict()`.

`buscar_para_atualizacao` faz `SELECT ... FOR UPDATE` e é usada pelos services transacionais das Tasks 10, 11 e 13.

- [ ] **Step 1: Criar `backend/models/produto_model.py`**

```python
from datetime import datetime

from .database import db


class Produto(db.Model):
    __tablename__ = "produtos"
    __table_args__ = (
        db.UniqueConstraint("fornecedor_id", "sku", name="uq_produtos_fornecedor_sku"),
    )

    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(
        db.Integer, db.ForeignKey("fornecedores.id"), nullable=False
    )
    sku = db.Column(db.String(60), nullable=False)
    nome = db.Column(db.String(160), nullable=False)
    categoria = db.Column(db.String(100))
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    estoque_minimo = db.Column(db.Integer, nullable=False, default=5)
    prazo_entrega_dias = db.Column(db.Integer, nullable=False, default=2)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    fornecedor = db.relationship("Fornecedor", backref="produtos")

    def salvar(self):
        """CREATE: salva um novo produto no banco."""
        db.session.add(self)
        db.session.commit()

    def atualizar(self, **campos):
        """UPDATE: altera apenas os campos informados."""
        permitidos = (
            "fornecedor_id", "sku", "nome", "categoria", "preco_unitario",
            "quantidade", "estoque_minimo", "prazo_entrega_dias", "ativo",
        )
        for nome_campo, valor in campos.items():
            if nome_campo in permitidos and valor is not None:
                setattr(self, nome_campo, valor)
        db.session.commit()

    def deletar(self):
        """DELETE: remove o produto do banco."""
        db.session.delete(self)
        db.session.commit()

    def desativar(self):
        """DELETE logico: mantem o historico de pedidos que referenciam o produto."""
        self.ativo = False
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna todos os produtos ativos ordenados por nome."""
        return (
            Produto.query
            .filter(Produto.ativo.is_(True))
            .order_by(Produto.nome.asc())
            .all()
        )

    @staticmethod
    def buscar_por_id(id):
        """READ: busca um produto pelo id."""
        return db.session.get(Produto, id)

    @staticmethod
    def buscar_por_sku(fornecedor_id, sku):
        """READ auxiliar: garante SKU unico por fornecedor."""
        return Produto.query.filter_by(fornecedor_id=fornecedor_id, sku=sku).first()

    @staticmethod
    def buscar_para_atualizacao(id):
        """READ com trava: usado pelos casos de uso que movimentam estoque."""
        return (
            Produto.query
            .filter(Produto.id == id)
            .with_for_update()
            .first()
        )

    def status_estoque(self):
        if self.quantidade <= 0:
            return "indisponivel"
        if self.quantidade <= self.estoque_minimo:
            return "baixo"
        return "disponivel"

    def to_dict(self):
        return {
            "id": self.id,
            "fornecedor_id": self.fornecedor_id,
            "fornecedor_nome": self.fornecedor.nome if self.fornecedor else None,
            "sku": self.sku,
            "nome": self.nome,
            "categoria": self.categoria,
            "preco_unitario": float(self.preco_unitario),
            "quantidade": self.quantidade,
            "estoque_minimo": self.estoque_minimo,
            "prazo_entrega_dias": self.prazo_entrega_dias,
            "ativo": self.ativo,
            "status_estoque": self.status_estoque(),
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }
```

- [ ] **Step 2: Verificar que a classe carrega e o relacionamento resolve**

Run:
```bash
cd /home/stock-map/backend && /home/stock-map/.venv/bin/python -c "
from models import fornecedor_model, produto_model
from sqlalchemy.orm import configure_mappers
configure_mappers()
print(produto_model.Produto.__tablename__)
print([c.name for c in produto_model.Produto.__table__.columns])
"
```
Expected: `produtos` e a lista de 12 colunas. Sem `InvalidRequestError`.

- [ ] **Step 3: Commit**

```bash
cd /home/stock-map
git add backend/models/produto_model.py
git commit -m "feat: adiciona model Produto com SQLAlchemy"
```

---

### Task 4: Models Pedido e ItemPedido

**Files:**
- Create: `backend/models/pedido_model.py`

**Interfaces:**
- Consumes: `models.database.db`, tabelas `lojistas`, `fornecedores`, `produtos`.
- Produces:
  - `Pedido(db.Model)` — constante de classe `STATUS_VALIDOS`, `salvar()`, `atualizar(**campos)`, `Pedido.listar_todos()`, `Pedido.buscar_por_id(id)`, `Pedido.buscar_para_atualizacao(id)`, `to_dict()`.
  - `ItemPedido(db.Model)` — `to_dict()`.

- [ ] **Step 1: Criar `backend/models/pedido_model.py`**

```python
from datetime import datetime

from .database import db


class Pedido(db.Model):
    __tablename__ = "pedidos"

    STATUS_VALIDOS = ("pendente", "confirmado", "despachado", "entregue", "cancelado")

    id = db.Column(db.Integer, primary_key=True)
    lojista_id = db.Column(db.Integer, db.ForeignKey("lojistas.id"), nullable=False)
    fornecedor_id = db.Column(
        db.Integer, db.ForeignKey("fornecedores.id"), nullable=False
    )
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_pedido"),
        nullable=False,
        default="pendente",
    )
    observacoes = db.Column(db.Text)
    valor_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    endereco_entrega = db.Column(db.String(220))
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    lojista = db.relationship("Lojista", backref="pedidos")
    fornecedor = db.relationship("Fornecedor", backref="pedidos")
    itens = db.relationship(
        "ItemPedido", backref="pedido", cascade="all, delete-orphan"
    )

    def salvar(self):
        """CREATE: salva um novo pedido no banco."""
        db.session.add(self)
        db.session.commit()

    def atualizar(self, **campos):
        """UPDATE: altera apenas os campos informados."""
        permitidos = ("status", "observacoes", "endereco_entrega", "valor_total")
        for nome_campo, valor in campos.items():
            if nome_campo in permitidos and valor is not None:
                setattr(self, nome_campo, valor)
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna todos os pedidos, do mais recente para o mais antigo."""
        return Pedido.query.order_by(Pedido.criado_em.desc()).all()

    @staticmethod
    def buscar_por_id(id):
        """READ: busca um pedido pelo id."""
        return db.session.get(Pedido, id)

    @staticmethod
    def buscar_para_atualizacao(id):
        """READ com trava: usado na troca de status, que devolve estoque."""
        return Pedido.query.filter(Pedido.id == id).with_for_update().first()

    def to_dict(self):
        return {
            "id": self.id,
            "lojista_id": self.lojista_id,
            "lojista_nome": self.lojista.nome if self.lojista else None,
            "fornecedor_id": self.fornecedor_id,
            "fornecedor_nome": self.fornecedor.nome if self.fornecedor else None,
            "status": self.status,
            "observacoes": self.observacoes,
            "valor_total": float(self.valor_total),
            "endereco_entrega": self.endereco_entrega,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class ItemPedido(db.Model):
    __tablename__ = "itens_pedido"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos.id"), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)

    produto = db.relationship("Produto")

    def to_dict(self):
        return {
            "id": self.id,
            "pedido_id": self.pedido_id,
            "produto_id": self.produto_id,
            "produto_nome": self.produto.nome if self.produto else None,
            "sku": self.produto.sku if self.produto else None,
            "quantidade": self.quantidade,
            "preco_unitario": float(self.preco_unitario),
            "subtotal": float(self.subtotal),
        }
```

- [ ] **Step 2: Verificar que as classes carregam**

Run:
```bash
cd /home/stock-map/backend && /home/stock-map/.venv/bin/python -c "
from models import fornecedor_model, lojista_model, produto_model, pedido_model
from sqlalchemy.orm import configure_mappers
configure_mappers()
print(pedido_model.Pedido.__tablename__, pedido_model.ItemPedido.__tablename__)
print(pedido_model.Pedido.STATUS_VALIDOS)
"
```
Expected: `pedidos itens_pedido` e a tupla dos 5 status.

- [ ] **Step 3: Commit**

```bash
cd /home/stock-map
git add backend/models/pedido_model.py
git commit -m "feat: adiciona models Pedido e ItemPedido com SQLAlchemy"
```

---

### Task 5: Models MovimentacaoEstoque, RotaEntrega e ParadaRota

**Files:**
- Create: `backend/models/movimentacao_estoque_model.py`
- Create: `backend/models/rota_model.py`

**Interfaces:**
- Consumes: `models.database.db`, tabelas `produtos`, `fornecedores`, `pedidos`, `lojistas`.
- Produces:
  - `MovimentacaoEstoque(db.Model)` — `TIPOS_VALIDOS`, `salvar()`, `MovimentacaoEstoque.listar_todos()`, `to_dict()`.
  - `RotaEntrega(db.Model)` — `STATUS_VALIDOS`, `salvar()`, `RotaEntrega.listar_todos()`, `RotaEntrega.buscar_por_id(id)`, `to_dict()`.
  - `ParadaRota(db.Model)` — `STATUS_VALIDOS`, `to_dict()`.

- [ ] **Step 1: Criar `backend/models/movimentacao_estoque_model.py`**

```python
from datetime import datetime

from .database import db


class MovimentacaoEstoque(db.Model):
    __tablename__ = "movimentacoes_estoque"

    TIPOS_VALIDOS = ("entrada", "saida", "ajuste")

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos.id"), nullable=False)
    fornecedor_id = db.Column(
        db.Integer, db.ForeignKey("fornecedores.id"), nullable=False
    )
    tipo_movimentacao = db.Column(
        db.Enum(*TIPOS_VALIDOS, name="tipo_movimentacao"), nullable=False
    )
    variacao_quantidade = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(180))
    referencia_tipo = db.Column(db.String(40))
    referencia_id = db.Column(db.Integer)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)

    produto = db.relationship("Produto")
    fornecedor = db.relationship("Fornecedor")

    def salvar(self):
        """CREATE: registra uma movimentacao de estoque."""
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna as movimentacoes da mais recente para a mais antiga."""
        return (
            MovimentacaoEstoque.query
            .order_by(MovimentacaoEstoque.criado_em.desc())
            .all()
        )

    def to_dict(self):
        return {
            "id": self.id,
            "produto_id": self.produto_id,
            "produto_nome": self.produto.nome if self.produto else None,
            "fornecedor_id": self.fornecedor_id,
            "fornecedor_nome": self.fornecedor.nome if self.fornecedor else None,
            "tipo_movimentacao": self.tipo_movimentacao,
            "variacao_quantidade": self.variacao_quantidade,
            "motivo": self.motivo,
            "referencia_tipo": self.referencia_tipo,
            "referencia_id": self.referencia_id,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
```

- [ ] **Step 2: Criar `backend/models/rota_model.py`**

```python
from datetime import datetime

from .database import db


class RotaEntrega(db.Model):
    __tablename__ = "rotas_entrega"

    STATUS_VALIDOS = ("planejada", "em_andamento", "concluida", "cancelada")

    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(
        db.Integer, db.ForeignKey("fornecedores.id"), nullable=False
    )
    data_rota = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_rota"), nullable=False, default="planejada"
    )
    distancia_total_km = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    fornecedor = db.relationship("Fornecedor")
    paradas = db.relationship(
        "ParadaRota", backref="rota", cascade="all, delete-orphan"
    )

    def salvar(self):
        """CREATE: salva uma nova rota de entrega."""
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def listar_todos():
        """READ: retorna as rotas da mais recente para a mais antiga."""
        return RotaEntrega.query.order_by(RotaEntrega.criado_em.desc()).all()

    @staticmethod
    def buscar_por_id(id):
        """READ: busca uma rota pelo id."""
        return db.session.get(RotaEntrega, id)

    def to_dict(self):
        return {
            "id": self.id,
            "fornecedor_id": self.fornecedor_id,
            "fornecedor_nome": self.fornecedor.nome if self.fornecedor else None,
            "data_rota": self.data_rota.isoformat() if self.data_rota else None,
            "status": self.status,
            "distancia_total_km": float(self.distancia_total_km),
            "observacoes": self.observacoes,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class ParadaRota(db.Model):
    __tablename__ = "paradas_rota"
    __table_args__ = (
        db.UniqueConstraint("rota_id", "ordem_parada", name="uq_paradas_rota_ordem"),
    )

    STATUS_VALIDOS = ("planejada", "concluida", "ignorada")

    id = db.Column(db.Integer, primary_key=True)
    rota_id = db.Column(db.Integer, db.ForeignKey("rotas_entrega.id"), nullable=False)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False)
    lojista_id = db.Column(db.Integer, db.ForeignKey("lojistas.id"), nullable=False)
    ordem_parada = db.Column(db.Integer, nullable=False)
    distancia_anterior_km = db.Column(db.Numeric(10, 2))
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_parada"),
        nullable=False,
        default="planejada",
    )
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)

    lojista = db.relationship("Lojista")

    def to_dict(self):
        return {
            "id": self.id,
            "rota_id": self.rota_id,
            "pedido_id": self.pedido_id,
            "lojista_id": self.lojista_id,
            "lojista_nome": self.lojista.nome if self.lojista else None,
            "ordem_parada": self.ordem_parada,
            "distancia_anterior_km": (
                float(self.distancia_anterior_km)
                if self.distancia_anterior_km is not None
                else None
            ),
            "status": self.status,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
```

- [ ] **Step 3: Verificar que os seis models carregam juntos**

Run:
```bash
cd /home/stock-map/backend && /home/stock-map/.venv/bin/python -c "
from models import (fornecedor_model, lojista_model, produto_model,
                    pedido_model, movimentacao_estoque_model, rota_model)
from models.database import db
from sqlalchemy.orm import configure_mappers
configure_mappers()
print(sorted(db.metadata.tables.keys()))
"
```
Expected exatamente:
```text
['fornecedores', 'itens_pedido', 'lojistas', 'movimentacoes_estoque', 'paradas_rota', 'pedidos', 'produtos', 'rotas_entrega']
```

- [ ] **Step 4: Criar as tabelas no banco e conferir a convivência**

Run:
```bash
cd /home/stock-map/backend && /home/stock-map/.venv/bin/python -c "
from app_novo import create_app
create_app()
print('tabelas criadas')
"
```
Expected: `tabelas criadas`.

Run:
```bash
cd /home/stock-map/backend && set -a && . ./.env && set +a && \
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -N \
  -e "SHOW TABLES;"
```
Expected: as 8 tabelas novas em português **e** as 8 antigas em inglês, lado a lado.

- [ ] **Step 5: Confirmar que produção continua no ar**

Run: `curl -s -o /dev/null -w "%{http_code}\n" https://stockmap.easytechnl.com.br/api/health`
Expected: `200`

- [ ] **Step 6: Commit**

```bash
cd /home/stock-map
git add backend/models/movimentacao_estoque_model.py backend/models/rota_model.py
git commit -m "feat: adiciona models de movimentacao de estoque e rotas"
```

---

### Task 6: Script do banco com seed e as 12 procedures

**Files:**
- Modify: `backend/database/create_database.sql` (reescrita completa)

**Interfaces:**
- Consumes: as 8 tabelas definidas nos models das Tasks 2 a 5.
- Produces: as 12 procedures consumidas pelos repositories da Task 7. Nomes e assinaturas:
  - `sp_produtos_com_status(IN p_fornecedor_id INT, IN p_busca VARCHAR(160))`
  - `sp_alertas_estoque_baixo()`
  - `sp_relatorio_resumo(IN p_data_inicio DATE, IN p_data_fim DATE)`
  - `sp_relatorio_top_produtos(IN p_data_inicio DATE, IN p_data_fim DATE)`
  - `sp_relatorio_desempenho_fornecedores(IN p_data_inicio DATE, IN p_data_fim DATE)`
  - `sp_pedidos_filtrados(IN p_status VARCHAR(20), IN p_lojista_id INT, IN p_data_inicio DATE, IN p_data_fim DATE)`
  - `sp_pedido_detalhe(IN p_pedido_id INT)`
  - `sp_pedido_itens(IN p_pedido_id INT)`
  - `sp_pedidos_para_roteirizar(IN p_fornecedor_id INT)`
  - `sp_rotas_listar()`
  - `sp_rota_paradas(IN p_rota_id INT)`
  - `sp_historico_movimentacoes(IN p_produto_id INT, IN p_fornecedor_id INT, IN p_data_inicio DATE, IN p_data_fim DATE)`

Todo parâmetro opcional é resolvido com `p_x IS NULL OR ...` dentro da procedure, evitando SQL dinâmico.

- [ ] **Step 1: Reescrever `backend/database/create_database.sql`**

```sql
CREATE DATABASE IF NOT EXISTS stock_map
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE stock_map;

-- ---------------------------------------------------------------------------
-- Tabelas. Espelham os models SQLAlchemy em backend/models/.
-- O db.create_all() tambem cria estas tabelas; este bloco existe para que o
-- script rode sozinho pelo cliente mysql.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fornecedores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(140) NOT NULL,
    cnpj VARCHAR(24),
    nome_contato VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL,
    telefone VARCHAR(40),
    endereco VARCHAR(220),
    cidade VARCHAR(100),
    estado VARCHAR(40),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_fornecedores_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS lojistas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(140) NOT NULL,
    cnpj VARCHAR(24),
    nome_contato VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL,
    telefone VARCHAR(40),
    endereco VARCHAR(220),
    cidade VARCHAR(100),
    estado VARCHAR(40),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_lojistas_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fornecedor_id INT NOT NULL,
    sku VARCHAR(60) NOT NULL,
    nome VARCHAR(160) NOT NULL,
    categoria VARCHAR(100),
    preco_unitario DECIMAL(10, 2) NOT NULL DEFAULT 0,
    quantidade INT NOT NULL DEFAULT 0,
    estoque_minimo INT NOT NULL DEFAULT 5,
    prazo_entrega_dias INT NOT NULL DEFAULT 2,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_produtos_fornecedor
        FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
    UNIQUE KEY uq_produtos_fornecedor_sku (fornecedor_id, sku),
    KEY idx_produtos_nome (nome),
    KEY idx_produtos_estoque (quantidade, estoque_minimo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lojista_id INT NOT NULL,
    fornecedor_id INT NOT NULL,
    status ENUM('pendente', 'confirmado', 'despachado', 'entregue', 'cancelado')
        NOT NULL DEFAULT 'pendente',
    observacoes TEXT,
    valor_total DECIMAL(12, 2) NOT NULL DEFAULT 0,
    endereco_entrega VARCHAR(220),
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pedidos_lojista FOREIGN KEY (lojista_id) REFERENCES lojistas(id),
    CONSTRAINT fk_pedidos_fornecedor FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
    KEY idx_pedidos_status_criado (status, criado_em),
    KEY idx_pedidos_lojista (lojista_id),
    KEY idx_pedidos_fornecedor (fornecedor_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS itens_pedido (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    produto_id INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    CONSTRAINT fk_itens_pedido_pedido
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    CONSTRAINT fk_itens_pedido_produto
        FOREIGN KEY (produto_id) REFERENCES produtos(id),
    KEY idx_itens_pedido_produto (produto_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
    id INT AUTO_INCREMENT PRIMARY KEY,
    produto_id INT NOT NULL,
    fornecedor_id INT NOT NULL,
    tipo_movimentacao ENUM('entrada', 'saida', 'ajuste') NOT NULL,
    variacao_quantidade INT NOT NULL,
    motivo VARCHAR(180),
    referencia_tipo VARCHAR(40),
    referencia_id INT,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_movimentacoes_produto
        FOREIGN KEY (produto_id) REFERENCES produtos(id),
    CONSTRAINT fk_movimentacoes_fornecedor
        FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
    KEY idx_movimentacoes_criado (criado_em),
    KEY idx_movimentacoes_produto (produto_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rotas_entrega (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fornecedor_id INT NOT NULL,
    data_rota DATE NOT NULL,
    status ENUM('planejada', 'em_andamento', 'concluida', 'cancelada')
        NOT NULL DEFAULT 'planejada',
    distancia_total_km DECIMAL(10, 2) NOT NULL DEFAULT 0,
    observacoes TEXT,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_rotas_fornecedor
        FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
    KEY idx_rotas_data (data_rota, status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS paradas_rota (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rota_id INT NOT NULL,
    pedido_id INT NOT NULL,
    lojista_id INT NOT NULL,
    ordem_parada INT NOT NULL,
    distancia_anterior_km DECIMAL(10, 2),
    status ENUM('planejada', 'concluida', 'ignorada') NOT NULL DEFAULT 'planejada',
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_paradas_rota
        FOREIGN KEY (rota_id) REFERENCES rotas_entrega(id) ON DELETE CASCADE,
    CONSTRAINT fk_paradas_pedido FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
    CONSTRAINT fk_paradas_lojista FOREIGN KEY (lojista_id) REFERENCES lojistas(id),
    UNIQUE KEY uq_paradas_rota_ordem (rota_id, ordem_parada)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- Dados de exemplo. INSERT IGNORE mantem o script reexecutavel.
-- ---------------------------------------------------------------------------

INSERT IGNORE INTO fornecedores
    (id, nome, cnpj, nome_contato, email, telefone, endereco, cidade, estado, latitude, longitude)
VALUES
    (1, 'Distribuidora Minas Norte', '12.345.678/0001-90', 'Carla Menezes',
     'contato@minasnorte.com.br', '(31) 3222-1010',
     'Av. Cristiano Machado, 1500', 'Belo Horizonte', 'MG', -19.8570000, -43.9350000),
    (2, 'Atacado Sul Suprimentos', '98.765.432/0001-10', 'Rogerio Alves',
     'vendas@sulsuprimentos.com.br', '(31) 3444-2020',
     'Rua Sao Paulo, 320', 'Contagem', 'MG', -19.9320000, -44.0540000);

INSERT IGNORE INTO lojistas
    (id, nome, cnpj, nome_contato, email, telefone, endereco, cidade, estado, latitude, longitude)
VALUES
    (1, 'Mercado Bom Preco', '11.222.333/0001-44', 'Juliana Rocha',
     'compras@bompreco.com.br', '(31) 3555-3030',
     'Rua da Bahia, 900', 'Belo Horizonte', 'MG', -19.9230000, -43.9380000),
    (2, 'Emporio Vila Nova', '55.666.777/0001-88', 'Marcos Diniz',
     'marcos@emporiovilanova.com.br', '(31) 3666-4040',
     'Av. Amazonas, 210', 'Betim', 'MG', -19.9680000, -44.1980000);

INSERT IGNORE INTO produtos
    (id, fornecedor_id, sku, nome, categoria, preco_unitario, quantidade, estoque_minimo, prazo_entrega_dias, ativo)
VALUES
    (1, 1, 'ARZ-5KG', 'Arroz tipo 1 - 5kg', 'Alimentos', 28.90, 120, 20, 2, 1),
    (2, 1, 'FJO-1KG', 'Feijao carioca - 1kg', 'Alimentos', 9.75, 8, 15, 2, 1),
    (3, 2, 'DTG-500', 'Detergente neutro 500ml', 'Limpeza', 3.40, 0, 10, 3, 1);

-- ---------------------------------------------------------------------------
-- Procedures. Todo acesso que vai alem do CRUD basico passa por aqui e e
-- chamado exclusivamente pela camada Repository.
-- ---------------------------------------------------------------------------

DROP PROCEDURE IF EXISTS sp_produtos_com_status;
DROP PROCEDURE IF EXISTS sp_alertas_estoque_baixo;
DROP PROCEDURE IF EXISTS sp_relatorio_resumo;
DROP PROCEDURE IF EXISTS sp_relatorio_top_produtos;
DROP PROCEDURE IF EXISTS sp_relatorio_desempenho_fornecedores;
DROP PROCEDURE IF EXISTS sp_pedidos_filtrados;
DROP PROCEDURE IF EXISTS sp_pedido_detalhe;
DROP PROCEDURE IF EXISTS sp_pedido_itens;
DROP PROCEDURE IF EXISTS sp_pedidos_para_roteirizar;
DROP PROCEDURE IF EXISTS sp_rotas_listar;
DROP PROCEDURE IF EXISTS sp_rota_paradas;
DROP PROCEDURE IF EXISTS sp_historico_movimentacoes;

DELIMITER //

CREATE PROCEDURE sp_produtos_com_status(
    IN p_fornecedor_id INT,
    IN p_busca VARCHAR(160)
)
BEGIN
    SELECT p.id, p.fornecedor_id, p.sku, p.nome, p.categoria, p.preco_unitario,
           p.quantidade, p.estoque_minimo, p.prazo_entrega_dias, p.ativo,
           p.criado_em, p.atualizado_em,
           f.nome AS fornecedor_nome,
           CASE
               WHEN p.quantidade <= 0 THEN 'indisponivel'
               WHEN p.quantidade <= p.estoque_minimo THEN 'baixo'
               ELSE 'disponivel'
           END AS status_estoque
      FROM produtos p
      INNER JOIN fornecedores f ON f.id = p.fornecedor_id
     WHERE p.ativo = 1
       AND (p_fornecedor_id IS NULL OR p.fornecedor_id = p_fornecedor_id)
       AND (p_busca IS NULL OR p_busca = ''
            OR p.nome LIKE CONCAT('%', p_busca, '%')
            OR p.sku LIKE CONCAT('%', p_busca, '%')
            OR p.categoria LIKE CONCAT('%', p_busca, '%'))
     ORDER BY p.nome;
END //

CREATE PROCEDURE sp_alertas_estoque_baixo()
BEGIN
    SELECT p.id AS produto_id, p.sku, p.nome AS produto_nome, p.quantidade,
           p.estoque_minimo, p.preco_unitario,
           f.id AS fornecedor_id, f.nome AS fornecedor_nome,
           CASE WHEN p.quantidade <= 0 THEN 'indisponivel' ELSE 'baixo' END AS severidade
      FROM produtos p
      INNER JOIN fornecedores f ON f.id = p.fornecedor_id
     WHERE p.ativo = 1
       AND p.quantidade <= p.estoque_minimo
     ORDER BY CASE WHEN p.quantidade <= 0 THEN 0 ELSE 1 END,
              p.quantidade ASC,
              p.nome ASC;
END //

CREATE PROCEDURE sp_relatorio_resumo(
    IN p_data_inicio DATE,
    IN p_data_fim DATE
)
BEGIN
    SELECT
        (SELECT COUNT(*) FROM fornecedores) AS fornecedores,
        (SELECT COUNT(*) FROM lojistas) AS lojistas,
        (SELECT COUNT(*) FROM produtos WHERE ativo = 1) AS produtos,
        (SELECT COALESCE(SUM(quantidade), 0) FROM produtos WHERE ativo = 1) AS unidades_estoque,
        (SELECT COUNT(*) FROM produtos WHERE ativo = 1 AND quantidade <= 0) AS produtos_indisponiveis,
        (SELECT COUNT(*) FROM produtos
          WHERE ativo = 1 AND quantidade > 0 AND quantidade <= estoque_minimo) AS produtos_estoque_baixo,
        (SELECT COUNT(*) FROM pedidos
          WHERE status IN ('pendente', 'confirmado', 'despachado')) AS pedidos_abertos,
        (SELECT COUNT(*) FROM pedidos
          WHERE DATE(criado_em) BETWEEN p_data_inicio AND p_data_fim) AS pedidos_periodo,
        (SELECT COALESCE(SUM(valor_total), 0) FROM pedidos
          WHERE DATE(criado_em) BETWEEN p_data_inicio AND p_data_fim
            AND status <> 'cancelado') AS faturamento_periodo;
END //

CREATE PROCEDURE sp_relatorio_top_produtos(
    IN p_data_inicio DATE,
    IN p_data_fim DATE
)
BEGIN
    SELECT p.id AS produto_id, p.nome, f.nome AS fornecedor_nome,
           SUM(ip.quantidade) AS demanda,
           SUM(ip.subtotal) AS total
      FROM itens_pedido ip
      INNER JOIN pedidos pe ON pe.id = ip.pedido_id
      INNER JOIN produtos p ON p.id = ip.produto_id
      INNER JOIN fornecedores f ON f.id = p.fornecedor_id
     WHERE pe.status <> 'cancelado'
       AND DATE(pe.criado_em) BETWEEN p_data_inicio AND p_data_fim
     GROUP BY p.id, p.nome, f.nome
     ORDER BY demanda DESC
     LIMIT 5;
END //

CREATE PROCEDURE sp_relatorio_desempenho_fornecedores(
    IN p_data_inicio DATE,
    IN p_data_fim DATE
)
BEGIN
    SELECT f.id AS fornecedor_id, f.nome,
           COUNT(pe.id) AS total_pedidos,
           COALESCE(SUM(CASE WHEN pe.status <> 'cancelado' THEN pe.valor_total ELSE 0 END), 0) AS total
      FROM fornecedores f
      LEFT JOIN pedidos pe
             ON pe.fornecedor_id = f.id
            AND DATE(pe.criado_em) BETWEEN p_data_inicio AND p_data_fim
     GROUP BY f.id, f.nome
     ORDER BY total DESC, total_pedidos DESC
     LIMIT 5;
END //

CREATE PROCEDURE sp_pedidos_filtrados(
    IN p_status VARCHAR(20),
    IN p_lojista_id INT,
    IN p_data_inicio DATE,
    IN p_data_fim DATE
)
BEGIN
    SELECT pe.id, pe.lojista_id, pe.fornecedor_id, pe.status, pe.observacoes,
           pe.valor_total, pe.endereco_entrega, pe.criado_em, pe.atualizado_em,
           l.nome AS lojista_nome, f.nome AS fornecedor_nome,
           COUNT(ip.id) AS total_itens
      FROM pedidos pe
      INNER JOIN lojistas l ON l.id = pe.lojista_id
      INNER JOIN fornecedores f ON f.id = pe.fornecedor_id
      LEFT JOIN itens_pedido ip ON ip.pedido_id = pe.id
     WHERE (p_status IS NULL OR p_status = '' OR pe.status = p_status)
       AND (p_lojista_id IS NULL OR pe.lojista_id = p_lojista_id)
       AND (p_data_inicio IS NULL OR DATE(pe.criado_em) >= p_data_inicio)
       AND (p_data_fim IS NULL OR DATE(pe.criado_em) <= p_data_fim)
     GROUP BY pe.id, pe.lojista_id, pe.fornecedor_id, pe.status, pe.observacoes,
              pe.valor_total, pe.endereco_entrega, pe.criado_em, pe.atualizado_em,
              l.nome, f.nome
     ORDER BY pe.criado_em DESC;
END //

CREATE PROCEDURE sp_pedido_detalhe(
    IN p_pedido_id INT
)
BEGIN
    SELECT pe.id, pe.lojista_id, pe.fornecedor_id, pe.status, pe.observacoes,
           pe.valor_total, pe.endereco_entrega, pe.criado_em, pe.atualizado_em,
           l.nome AS lojista_nome, f.nome AS fornecedor_nome
      FROM pedidos pe
      INNER JOIN lojistas l ON l.id = pe.lojista_id
      INNER JOIN fornecedores f ON f.id = pe.fornecedor_id
     WHERE pe.id = p_pedido_id;
END //

CREATE PROCEDURE sp_pedido_itens(
    IN p_pedido_id INT
)
BEGIN
    SELECT ip.id, ip.pedido_id, ip.produto_id, ip.quantidade,
           ip.preco_unitario, ip.subtotal,
           p.nome AS produto_nome, p.sku
      FROM itens_pedido ip
      INNER JOIN produtos p ON p.id = ip.produto_id
     WHERE ip.pedido_id = p_pedido_id
     ORDER BY ip.id;
END //

CREATE PROCEDURE sp_pedidos_para_roteirizar(
    IN p_fornecedor_id INT
)
BEGIN
    SELECT pe.id AS pedido_id, pe.endereco_entrega, pe.valor_total,
           l.id AS lojista_id, l.nome AS lojista_nome, l.cidade,
           l.latitude, l.longitude
      FROM pedidos pe
      INNER JOIN lojistas l ON l.id = pe.lojista_id
     WHERE pe.fornecedor_id = p_fornecedor_id
       AND pe.status IN ('confirmado', 'despachado')
     ORDER BY pe.criado_em ASC;
END //

CREATE PROCEDURE sp_rotas_listar()
BEGIN
    SELECT r.id, r.fornecedor_id, r.data_rota, r.status, r.distancia_total_km,
           r.observacoes, r.criado_em,
           f.nome AS fornecedor_nome,
           COUNT(pr.id) AS total_paradas
      FROM rotas_entrega r
      INNER JOIN fornecedores f ON f.id = r.fornecedor_id
      LEFT JOIN paradas_rota pr ON pr.rota_id = r.id
     GROUP BY r.id, r.fornecedor_id, r.data_rota, r.status, r.distancia_total_km,
              r.observacoes, r.criado_em, f.nome
     ORDER BY r.criado_em DESC;
END //

CREATE PROCEDURE sp_rota_paradas(
    IN p_rota_id INT
)
BEGIN
    SELECT pr.id, pr.rota_id, pr.pedido_id, pr.lojista_id, pr.ordem_parada,
           pr.distancia_anterior_km, pr.status,
           l.nome AS lojista_nome, l.endereco, l.cidade, l.estado
      FROM paradas_rota pr
      INNER JOIN lojistas l ON l.id = pr.lojista_id
     WHERE pr.rota_id = p_rota_id
     ORDER BY pr.ordem_parada;
END //

CREATE PROCEDURE sp_historico_movimentacoes(
    IN p_produto_id INT,
    IN p_fornecedor_id INT,
    IN p_data_inicio DATE,
    IN p_data_fim DATE
)
BEGIN
    SELECT m.id, m.produto_id, m.fornecedor_id, m.tipo_movimentacao,
           m.variacao_quantidade, m.motivo, m.referencia_tipo, m.referencia_id,
           m.criado_em,
           p.nome AS produto_nome, p.sku,
           f.nome AS fornecedor_nome
      FROM movimentacoes_estoque m
      INNER JOIN produtos p ON p.id = m.produto_id
      INNER JOIN fornecedores f ON f.id = m.fornecedor_id
     WHERE (p_produto_id IS NULL OR m.produto_id = p_produto_id)
       AND (p_fornecedor_id IS NULL OR m.fornecedor_id = p_fornecedor_id)
       AND (p_data_inicio IS NULL OR DATE(m.criado_em) >= p_data_inicio)
       AND (p_data_fim IS NULL OR DATE(m.criado_em) <= p_data_fim)
     ORDER BY m.criado_em DESC, m.id DESC;
END //

DELIMITER ;
```

- [ ] **Step 2: Executar o script**

`DELIMITER` é diretiva do cliente `mysql`, não SQL de servidor — o script precisa ser executado pelo cliente, não por Python.

Run:
```bash
cd /home/stock-map/backend && set -a && . ./.env && set +a && \
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" < database/create_database.sql
```
Expected: nenhuma saída, código de retorno 0.

Se o usuário `stock_map_app` não tiver privilégio `CREATE ROUTINE`, rodar como root:
```bash
sudo mysql < /home/stock-map/backend/database/create_database.sql
```

- [ ] **Step 3: Conferir que as 12 procedures existem**

Run:
```bash
cd /home/stock-map/backend && set -a && . ./.env && set +a && \
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -N \
  -e "SELECT routine_name FROM information_schema.routines
       WHERE routine_schema='stock_map' AND routine_type='PROCEDURE'
       ORDER BY routine_name;"
```
Expected: as 12 procedures, em ordem alfabética.

- [ ] **Step 4: Exercitar duas procedures direto no cliente**

Run:
```bash
cd /home/stock-map/backend && set -a && . ./.env && set +a && \
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" \
  -e "CALL sp_produtos_com_status(NULL, NULL); CALL sp_alertas_estoque_baixo();"
```
Expected: a primeira retorna 3 produtos com `status_estoque` `disponivel`, `baixo` e `indisponivel`; a segunda retorna os 2 produtos com estoque no limite (`FJO-1KG` e `DTG-500`), com `DTG-500` em primeiro por estar zerado.

- [ ] **Step 5: Commit**

```bash
cd /home/stock-map
git add backend/database/create_database.sql
git commit -m "feat: reescreve script do banco com tabelas em portugues e 12 procedures"
```

---

### Task 7: Camada Repository

**Files:**
- Create: `backend/repositories/conversor.py`
- Create: `backend/repositories/produto_repository.py`
- Create: `backend/repositories/pedido_repository.py`
- Create: `backend/repositories/alerta_repository.py`
- Create: `backend/repositories/relatorio_repository.py`
- Create: `backend/repositories/rota_repository.py`
- Create: `backend/repositories/movimentacao_repository.py`

**Interfaces:**
- Consumes: `models.database.db`, as 12 procedures da Task 6.
- Produces (todos `@staticmethod`, todos retornando `dict` ou `list[dict]` já serializáveis):
  - `ProdutoRepository.buscar_com_status(fornecedor_id, busca) -> list[dict]`
  - `PedidoRepository.buscar_filtrados(status, lojista_id, data_inicio, data_fim) -> list[dict]`
  - `PedidoRepository.buscar_detalhe(pedido_id) -> dict | None`
  - `PedidoRepository.buscar_itens(pedido_id) -> list[dict]`
  - `AlertaRepository.listar_estoque_baixo() -> list[dict]`
  - `RelatorioRepository.resumo(data_inicio, data_fim) -> dict`
  - `RelatorioRepository.top_produtos(data_inicio, data_fim) -> list[dict]`
  - `RelatorioRepository.desempenho_fornecedores(data_inicio, data_fim) -> list[dict]`
  - `RotaRepository.pedidos_para_roteirizar(fornecedor_id) -> list[dict]`
  - `RotaRepository.listar_com_paradas() -> list[dict]` (cada rota traz a chave `paradas`)
  - `MovimentacaoRepository.buscar_historico(produto_id, fornecedor_id, data_inicio, data_fim) -> list[dict]`

O `conversor.py` existe porque `jsonify` não serializa `Decimal`, e as procedures devolvem linhas cruas, não instâncias de model. É um utilitário interno da camada, não um desvio da arquitetura.

- [ ] **Step 1: Criar `backend/repositories/conversor.py`**

```python
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
```

- [ ] **Step 2: Criar `backend/repositories/produto_repository.py`**

```python
from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linhas


class ProdutoRepository:
    """Consultas de produto que vao alem do CRUD basico da Model."""

    @staticmethod
    def buscar_com_status(fornecedor_id=None, busca=None):
        sql = text("CALL sp_produtos_com_status(:fornecedor_id, :busca)")
        resultado = db.session.execute(
            sql, {"fornecedor_id": fornecedor_id, "busca": busca}
        )
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)
```

- [ ] **Step 3: Criar `backend/repositories/pedido_repository.py`**

```python
from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linha, converter_linhas


class PedidoRepository:
    """Consultas de pedido que envolvem filtros e juncao com outras tabelas."""

    @staticmethod
    def buscar_filtrados(status=None, lojista_id=None, data_inicio=None, data_fim=None):
        sql = text(
            "CALL sp_pedidos_filtrados(:status, :lojista_id, :data_inicio, :data_fim)"
        )
        resultado = db.session.execute(
            sql,
            {
                "status": status,
                "lojista_id": lojista_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
            },
        )
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)

    @staticmethod
    def buscar_detalhe(pedido_id):
        sql = text("CALL sp_pedido_detalhe(:pedido_id)")
        resultado = db.session.execute(sql, {"pedido_id": pedido_id})
        linhas = resultado.mappings().all()
        resultado.close()
        if not linhas:
            return None
        return converter_linha(linhas[0])

    @staticmethod
    def buscar_itens(pedido_id):
        sql = text("CALL sp_pedido_itens(:pedido_id)")
        resultado = db.session.execute(sql, {"pedido_id": pedido_id})
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)
```

- [ ] **Step 4: Criar `backend/repositories/alerta_repository.py`**

```python
from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linhas


class AlertaRepository:
    """Alertas de estoque, calculados por procedure."""

    @staticmethod
    def listar_estoque_baixo():
        sql = text("CALL sp_alertas_estoque_baixo()")
        resultado = db.session.execute(sql)
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)
```

- [ ] **Step 5: Criar `backend/repositories/relatorio_repository.py`**

```python
from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linha, converter_linhas


class RelatorioRepository:
    """Agregacoes e rankings usados nos relatorios."""

    @staticmethod
    def resumo(data_inicio, data_fim):
        sql = text("CALL sp_relatorio_resumo(:data_inicio, :data_fim)")
        resultado = db.session.execute(
            sql, {"data_inicio": data_inicio, "data_fim": data_fim}
        )
        linhas = resultado.mappings().all()
        resultado.close()
        if not linhas:
            return {}
        return converter_linha(linhas[0])

    @staticmethod
    def top_produtos(data_inicio, data_fim):
        sql = text("CALL sp_relatorio_top_produtos(:data_inicio, :data_fim)")
        resultado = db.session.execute(
            sql, {"data_inicio": data_inicio, "data_fim": data_fim}
        )
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)

    @staticmethod
    def desempenho_fornecedores(data_inicio, data_fim):
        sql = text("CALL sp_relatorio_desempenho_fornecedores(:data_inicio, :data_fim)")
        resultado = db.session.execute(
            sql, {"data_inicio": data_inicio, "data_fim": data_fim}
        )
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)
```

- [ ] **Step 6: Criar `backend/repositories/rota_repository.py`**

```python
from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linhas


class RotaRepository:
    """Consultas de roteirizacao e listagem de rotas com suas paradas."""

    @staticmethod
    def pedidos_para_roteirizar(fornecedor_id):
        sql = text("CALL sp_pedidos_para_roteirizar(:fornecedor_id)")
        resultado = db.session.execute(sql, {"fornecedor_id": fornecedor_id})
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)

    @staticmethod
    def listar_com_paradas():
        sql_rotas = text("CALL sp_rotas_listar()")
        resultado = db.session.execute(sql_rotas)
        rotas = converter_linhas(resultado.mappings().all())
        resultado.close()

        for rota in rotas:
            sql_paradas = text("CALL sp_rota_paradas(:rota_id)")
            resultado_paradas = db.session.execute(sql_paradas, {"rota_id": rota["id"]})
            rota["paradas"] = converter_linhas(resultado_paradas.mappings().all())
            resultado_paradas.close()

        return rotas
```

- [ ] **Step 7: Criar `backend/repositories/movimentacao_repository.py`**

```python
from sqlalchemy import text

from models.database import db
from repositories.conversor import converter_linhas


class MovimentacaoRepository:
    """Historico de entradas, saidas e ajustes de estoque."""

    @staticmethod
    def buscar_historico(produto_id=None, fornecedor_id=None,
                         data_inicio=None, data_fim=None):
        sql = text(
            "CALL sp_historico_movimentacoes("
            ":produto_id, :fornecedor_id, :data_inicio, :data_fim)"
        )
        resultado = db.session.execute(
            sql,
            {
                "produto_id": produto_id,
                "fornecedor_id": fornecedor_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
            },
        )
        linhas = resultado.mappings().all()
        resultado.close()
        return converter_linhas(linhas)
```

- [ ] **Step 8: Verificar cada repository contra o banco real**

Run:
```bash
cd /home/stock-map/backend && /home/stock-map/.venv/bin/python -c "
from app_novo import create_app
from repositories.produto_repository import ProdutoRepository
from repositories.alerta_repository import AlertaRepository
from repositories.pedido_repository import PedidoRepository
from repositories.relatorio_repository import RelatorioRepository
from repositories.rota_repository import RotaRepository
from repositories.movimentacao_repository import MovimentacaoRepository

app = create_app()
with app.app_context():
    produtos = ProdutoRepository.buscar_com_status(None, None)
    print('produtos:', len(produtos), produtos[0]['status_estoque'])
    print('busca arroz:', len(ProdutoRepository.buscar_com_status(None, 'Arroz')))
    print('alertas:', len(AlertaRepository.listar_estoque_baixo()))
    print('pedidos:', len(PedidoRepository.buscar_filtrados()))
    print('resumo:', RelatorioRepository.resumo('2020-01-01', '2030-12-31'))
    print('top:', RelatorioRepository.top_produtos('2020-01-01', '2030-12-31'))
    print('desempenho:', len(RelatorioRepository.desempenho_fornecedores('2020-01-01', '2030-12-31')))
    print('roteirizar:', RotaRepository.pedidos_para_roteirizar(1))
    print('rotas:', RotaRepository.listar_com_paradas())
    print('movimentacoes:', len(MovimentacaoRepository.buscar_historico()))
"
```
Expected:
- `produtos: 3 disponivel`
- `busca arroz: 1`
- `alertas: 2`
- `pedidos: 0`
- `resumo:` dicionário com `fornecedores: 2`, `lojistas: 2`, `produtos: 3`, `unidades_estoque: 128.0` ou `128`, e valores numéricos (nenhum `Decimal`)
- `top: []`
- `desempenho: 2`
- `roteirizar: []`
- `rotas: []`
- `movimentacoes: 0`

Nenhuma exceção de serialização.

- [ ] **Step 9: Commit**

```bash
cd /home/stock-map
git add backend/repositories/conversor.py backend/repositories/produto_repository.py \
        backend/repositories/pedido_repository.py backend/repositories/alerta_repository.py \
        backend/repositories/relatorio_repository.py backend/repositories/rota_repository.py \
        backend/repositories/movimentacao_repository.py
git commit -m "feat: adiciona repositories chamando as stored procedures"
```

---

### Task 8: Caso de uso Fornecedor — 5 services e o controller

**Files:**
- Create: `backend/services/criar_fornecedor_service.py`
- Create: `backend/services/listar_fornecedores_service.py`
- Create: `backend/services/buscar_fornecedor_por_id_service.py`
- Create: `backend/services/atualizar_fornecedor_service.py`
- Create: `backend/services/deletar_fornecedor_service.py`
- Create: `backend/controllers/fornecedor_controller.py`
- Modify: `backend/app_novo.py`

**Interfaces:**
- Consumes: `Fornecedor` da Task 2.
- Produces:
  - `CriarFornecedorService().executar(dados) -> dict`
  - `ListarFornecedoresService().executar() -> list[dict]`
  - `BuscarFornecedorPorIdService().executar(fornecedor_id) -> dict | None`
  - `AtualizarFornecedorService().executar(fornecedor_id, dados) -> dict | None`
  - `DeletarFornecedorService().executar(fornecedor_id) -> bool`
  - Blueprint `fornecedor_controller`, registrado no `app_novo.py`.

`None` significa "não encontrado" e o controller traduz para 404. `ValueError` significa entrada inválida e vira 400.

- [ ] **Step 1: Criar `backend/services/criar_fornecedor_service.py`**

```python
from models.fornecedor_model import Fornecedor


class CriarFornecedorService:
    CAMPOS_OBRIGATORIOS = ("nome", "nome_contato", "email")

    def executar(self, dados):
        for campo in self.CAMPOS_OBRIGATORIOS:
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        if Fornecedor.buscar_por_email(dados["email"]):
            raise ValueError("Já existe um fornecedor cadastrado com este e-mail.")

        fornecedor = Fornecedor(
            nome=dados["nome"],
            cnpj=dados.get("cnpj"),
            nome_contato=dados["nome_contato"],
            email=dados["email"],
            telefone=dados.get("telefone"),
            endereco=dados.get("endereco"),
            cidade=dados.get("cidade"),
            estado=dados.get("estado"),
            latitude=dados.get("latitude"),
            longitude=dados.get("longitude"),
        )
        fornecedor.salvar()
        return fornecedor.to_dict()
```

- [ ] **Step 2: Criar `backend/services/listar_fornecedores_service.py`**

```python
from models.fornecedor_model import Fornecedor


class ListarFornecedoresService:
    def executar(self):
        fornecedores = Fornecedor.listar_todos()
        return [fornecedor.to_dict() for fornecedor in fornecedores]
```

- [ ] **Step 3: Criar `backend/services/buscar_fornecedor_por_id_service.py`**

```python
from models.fornecedor_model import Fornecedor


class BuscarFornecedorPorIdService:
    def executar(self, fornecedor_id):
        fornecedor = Fornecedor.buscar_por_id(fornecedor_id)
        if fornecedor is None:
            return None
        return fornecedor.to_dict()
```

- [ ] **Step 4: Criar `backend/services/atualizar_fornecedor_service.py`**

```python
from models.fornecedor_model import Fornecedor


class AtualizarFornecedorService:
    def executar(self, fornecedor_id, dados):
        fornecedor = Fornecedor.buscar_por_id(fornecedor_id)
        if fornecedor is None:
            return None

        novo_email = dados.get("email")
        if novo_email:
            existente = Fornecedor.buscar_por_email(novo_email)
            if existente and existente.id != fornecedor.id:
                raise ValueError("Já existe outro fornecedor cadastrado com este e-mail.")

        fornecedor.atualizar(
            nome=dados.get("nome"),
            cnpj=dados.get("cnpj"),
            nome_contato=dados.get("nome_contato"),
            email=dados.get("email"),
            telefone=dados.get("telefone"),
            endereco=dados.get("endereco"),
            cidade=dados.get("cidade"),
            estado=dados.get("estado"),
            latitude=dados.get("latitude"),
            longitude=dados.get("longitude"),
        )
        return fornecedor.to_dict()
```

- [ ] **Step 5: Criar `backend/services/deletar_fornecedor_service.py`**

```python
from models.fornecedor_model import Fornecedor
from models.produto_model import Produto


class DeletarFornecedorService:
    def executar(self, fornecedor_id):
        fornecedor = Fornecedor.buscar_por_id(fornecedor_id)
        if fornecedor is None:
            return False

        produtos = Produto.query.filter_by(fornecedor_id=fornecedor_id).count()
        if produtos > 0:
            raise ValueError(
                "Não é possível remover um fornecedor que possui produtos cadastrados."
            )

        fornecedor.deletar()
        return True
```

- [ ] **Step 6: Criar `backend/controllers/fornecedor_controller.py`**

```python
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.criar_fornecedor_service import CriarFornecedorService
from services.listar_fornecedores_service import ListarFornecedoresService
from services.buscar_fornecedor_por_id_service import BuscarFornecedorPorIdService
from services.atualizar_fornecedor_service import AtualizarFornecedorService
from services.deletar_fornecedor_service import DeletarFornecedorService

fornecedor_controller = Blueprint("fornecedor_controller", __name__)


@fornecedor_controller.get("/fornecedores")
def listar_fornecedores():
    try:
        service = ListarFornecedoresService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar fornecedores."}), 500


@fornecedor_controller.post("/fornecedores")
def criar_fornecedor():
    try:
        dados = request.get_json() or {}
        service = CriarFornecedorService()
        return jsonify(service.executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar fornecedor no banco de dados."}), 500


@fornecedor_controller.get("/fornecedores/<int:fornecedor_id>")
def buscar_fornecedor_por_id(fornecedor_id):
    try:
        service = BuscarFornecedorPorIdService()
        fornecedor = service.executar(fornecedor_id)
        if fornecedor is None:
            return jsonify({"erro": "Fornecedor não encontrado."}), 404
        return jsonify(fornecedor), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao buscar fornecedor."}), 500


@fornecedor_controller.put("/fornecedores/<int:fornecedor_id>")
def atualizar_fornecedor(fornecedor_id):
    try:
        dados = request.get_json() or {}
        service = AtualizarFornecedorService()
        fornecedor = service.executar(fornecedor_id, dados)
        if fornecedor is None:
            return jsonify({"erro": "Fornecedor não encontrado."}), 404
        return jsonify(fornecedor), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar fornecedor no banco de dados."}), 500


@fornecedor_controller.delete("/fornecedores/<int:fornecedor_id>")
def deletar_fornecedor(fornecedor_id):
    try:
        service = DeletarFornecedorService()
        if service.executar(fornecedor_id) is False:
            return jsonify({"erro": "Fornecedor não encontrado."}), 404
        return "", 204
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao remover fornecedor do banco de dados."}), 500
```

- [ ] **Step 7: Registrar o blueprint no `backend/app_novo.py`**

Acrescentar o import junto aos demais imports do topo:

```python
from controllers.fornecedor_controller import fornecedor_controller
```

E dentro de `create_app()`, logo após `db.init_app(app)`:

```python
    app.register_blueprint(fornecedor_controller)
```

- [ ] **Step 8: Subir o servidor de desenvolvimento na porta 5001**

Run (deixar rodando em outro terminal ou em background):
```bash
cd /home/stock-map/backend && \
/home/stock-map/.venv/bin/python -m flask --app app_novo run --port 5001
```
Expected: `Running on http://127.0.0.1:5001`

- [ ] **Step 9: Exercitar as 5 rotas**

Run:
```bash
curl -s http://127.0.0.1:5001/fornecedores | head -c 300; echo
curl -s -X POST http://127.0.0.1:5001/fornecedores \
  -H 'Content-Type: application/json' \
  -d '{"nome":"Teste Ltda","nome_contato":"Fulano","email":"teste@ex.com","cidade":"Betim","estado":"MG"}' \
  -w ' [%{http_code}]\n'
curl -s -X POST http://127.0.0.1:5001/fornecedores \
  -H 'Content-Type: application/json' -d '{"nome":"Sem contato"}' -w ' [%{http_code}]\n'
curl -s http://127.0.0.1:5001/fornecedores/999 -w ' [%{http_code}]\n'
```
Expected:
- listagem: array JSON começando em `[{"atualizado_em":...` com os 2 fornecedores do seed
- criação válida: `201`
- criação sem `nome_contato`: `{"erro":"O campo 'nome_contato' é obrigatório."} [400]`
- id inexistente: `{"erro":"Fornecedor não encontrado."} [404]`

Run (limpar o registro de teste):
```bash
ID=$(curl -s http://127.0.0.1:5001/fornecedores | \
  /home/stock-map/.venv/bin/python -c "import sys,json; print([f['id'] for f in json.load(sys.stdin) if f['email']=='teste@ex.com'][0])")
curl -s -X DELETE http://127.0.0.1:5001/fornecedores/$ID -w '[%{http_code}]\n'
```
Expected: `[204]`

- [ ] **Step 10: Commit**

```bash
cd /home/stock-map
git add backend/services/criar_fornecedor_service.py \
        backend/services/listar_fornecedores_service.py \
        backend/services/buscar_fornecedor_por_id_service.py \
        backend/services/atualizar_fornecedor_service.py \
        backend/services/deletar_fornecedor_service.py \
        backend/controllers/fornecedor_controller.py backend/app_novo.py
git commit -m "feat: adiciona caso de uso de fornecedor com services por classe"
```

---

### Task 9: Caso de uso Lojista — 5 services e o controller

**Files:**
- Create: `backend/services/criar_lojista_service.py`
- Create: `backend/services/listar_lojistas_service.py`
- Create: `backend/services/buscar_lojista_por_id_service.py`
- Create: `backend/services/atualizar_lojista_service.py`
- Create: `backend/services/deletar_lojista_service.py`
- Create: `backend/controllers/lojista_controller.py`
- Modify: `backend/app_novo.py`

**Interfaces:**
- Consumes: `Lojista` da Task 2, `Pedido` da Task 4.
- Produces:
  - `CriarLojistaService().executar(dados) -> dict`
  - `ListarLojistasService().executar() -> list[dict]`
  - `BuscarLojistaPorIdService().executar(lojista_id) -> dict | None`
  - `AtualizarLojistaService().executar(lojista_id, dados) -> dict | None`
  - `DeletarLojistaService().executar(lojista_id) -> bool`
  - Blueprint `lojista_controller`.

- [ ] **Step 1: Criar `backend/services/criar_lojista_service.py`**

```python
from models.lojista_model import Lojista


class CriarLojistaService:
    CAMPOS_OBRIGATORIOS = ("nome", "nome_contato", "email")

    def executar(self, dados):
        for campo in self.CAMPOS_OBRIGATORIOS:
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        if Lojista.buscar_por_email(dados["email"]):
            raise ValueError("Já existe um lojista cadastrado com este e-mail.")

        lojista = Lojista(
            nome=dados["nome"],
            cnpj=dados.get("cnpj"),
            nome_contato=dados["nome_contato"],
            email=dados["email"],
            telefone=dados.get("telefone"),
            endereco=dados.get("endereco"),
            cidade=dados.get("cidade"),
            estado=dados.get("estado"),
            latitude=dados.get("latitude"),
            longitude=dados.get("longitude"),
        )
        lojista.salvar()
        return lojista.to_dict()
```

- [ ] **Step 2: Criar `backend/services/listar_lojistas_service.py`**

```python
from models.lojista_model import Lojista


class ListarLojistasService:
    def executar(self):
        lojistas = Lojista.listar_todos()
        return [lojista.to_dict() for lojista in lojistas]
```

- [ ] **Step 3: Criar `backend/services/buscar_lojista_por_id_service.py`**

```python
from models.lojista_model import Lojista


class BuscarLojistaPorIdService:
    def executar(self, lojista_id):
        lojista = Lojista.buscar_por_id(lojista_id)
        if lojista is None:
            return None
        return lojista.to_dict()
```

- [ ] **Step 4: Criar `backend/services/atualizar_lojista_service.py`**

```python
from models.lojista_model import Lojista


class AtualizarLojistaService:
    def executar(self, lojista_id, dados):
        lojista = Lojista.buscar_por_id(lojista_id)
        if lojista is None:
            return None

        novo_email = dados.get("email")
        if novo_email:
            existente = Lojista.buscar_por_email(novo_email)
            if existente and existente.id != lojista.id:
                raise ValueError("Já existe outro lojista cadastrado com este e-mail.")

        lojista.atualizar(
            nome=dados.get("nome"),
            cnpj=dados.get("cnpj"),
            nome_contato=dados.get("nome_contato"),
            email=dados.get("email"),
            telefone=dados.get("telefone"),
            endereco=dados.get("endereco"),
            cidade=dados.get("cidade"),
            estado=dados.get("estado"),
            latitude=dados.get("latitude"),
            longitude=dados.get("longitude"),
        )
        return lojista.to_dict()
```

- [ ] **Step 5: Criar `backend/services/deletar_lojista_service.py`**

```python
from models.lojista_model import Lojista
from models.pedido_model import Pedido


class DeletarLojistaService:
    def executar(self, lojista_id):
        lojista = Lojista.buscar_por_id(lojista_id)
        if lojista is None:
            return False

        pedidos = Pedido.query.filter_by(lojista_id=lojista_id).count()
        if pedidos > 0:
            raise ValueError(
                "Não é possível remover um lojista que possui pedidos registrados."
            )

        lojista.deletar()
        return True
```

- [ ] **Step 6: Criar `backend/controllers/lojista_controller.py`**

```python
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.criar_lojista_service import CriarLojistaService
from services.listar_lojistas_service import ListarLojistasService
from services.buscar_lojista_por_id_service import BuscarLojistaPorIdService
from services.atualizar_lojista_service import AtualizarLojistaService
from services.deletar_lojista_service import DeletarLojistaService

lojista_controller = Blueprint("lojista_controller", __name__)


@lojista_controller.get("/lojistas")
def listar_lojistas():
    try:
        service = ListarLojistasService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar lojistas."}), 500


@lojista_controller.post("/lojistas")
def criar_lojista():
    try:
        dados = request.get_json() or {}
        service = CriarLojistaService()
        return jsonify(service.executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar lojista no banco de dados."}), 500


@lojista_controller.get("/lojistas/<int:lojista_id>")
def buscar_lojista_por_id(lojista_id):
    try:
        service = BuscarLojistaPorIdService()
        lojista = service.executar(lojista_id)
        if lojista is None:
            return jsonify({"erro": "Lojista não encontrado."}), 404
        return jsonify(lojista), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao buscar lojista."}), 500


@lojista_controller.put("/lojistas/<int:lojista_id>")
def atualizar_lojista(lojista_id):
    try:
        dados = request.get_json() or {}
        service = AtualizarLojistaService()
        lojista = service.executar(lojista_id, dados)
        if lojista is None:
            return jsonify({"erro": "Lojista não encontrado."}), 404
        return jsonify(lojista), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar lojista no banco de dados."}), 500


@lojista_controller.delete("/lojistas/<int:lojista_id>")
def deletar_lojista(lojista_id):
    try:
        service = DeletarLojistaService()
        if service.executar(lojista_id) is False:
            return jsonify({"erro": "Lojista não encontrado."}), 404
        return "", 204
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao remover lojista do banco de dados."}), 500
```

- [ ] **Step 7: Registrar o blueprint no `backend/app_novo.py`**

Import no topo:
```python
from controllers.lojista_controller import lojista_controller
```

Dentro de `create_app()`, junto do registro anterior:
```python
    app.register_blueprint(lojista_controller)
```

- [ ] **Step 8: Exercitar as rotas**

Reiniciar o servidor da porta 5001 e rodar:
```bash
curl -s http://127.0.0.1:5001/lojistas -w ' [%{http_code}]\n' | head -c 300; echo
curl -s -X POST http://127.0.0.1:5001/lojistas -H 'Content-Type: application/json' \
  -d '{"nome":"Loja Teste","nome_contato":"Beltrano","email":"loja@ex.com"}' -w ' [%{http_code}]\n'
curl -s -X DELETE http://127.0.0.1:5001/lojistas/1 -w ' [%{http_code}]\n'
```
Expected: listagem com os 2 lojistas do seed e `200`; criação `201`; a remoção do lojista 1 retorna `204` (ele ainda não tem pedidos neste ponto do plano).

Recriar o lojista 1 para não furar o seed dos passos seguintes:
```bash
curl -s -X POST http://127.0.0.1:5001/lojistas -H 'Content-Type: application/json' \
  -d '{"nome":"Mercado Bom Preco","nome_contato":"Juliana Rocha","email":"compras@bompreco.com.br","endereco":"Rua da Bahia, 900","cidade":"Belo Horizonte","estado":"MG","latitude":-19.923,"longitude":-43.938}' \
  -w ' [%{http_code}]\n'
curl -s -X DELETE "http://127.0.0.1:5001/lojistas/$(curl -s http://127.0.0.1:5001/lojistas | /home/stock-map/.venv/bin/python -c "import sys,json; print([l['id'] for l in json.load(sys.stdin) if l['email']=='loja@ex.com'][0])")" -w '[%{http_code}]\n'
```
Expected: `201` e `204`.

- [ ] **Step 9: Commit**

```bash
cd /home/stock-map
git add backend/services/criar_lojista_service.py \
        backend/services/listar_lojistas_service.py \
        backend/services/buscar_lojista_por_id_service.py \
        backend/services/atualizar_lojista_service.py \
        backend/services/deletar_lojista_service.py \
        backend/controllers/lojista_controller.py backend/app_novo.py
git commit -m "feat: adiciona caso de uso de lojista com services por classe"
```

---

### Task 10: Caso de uso Produto — 6 services e o controller

**Files:**
- Create: `backend/services/criar_produto_service.py`
- Create: `backend/services/listar_produtos_service.py`
- Create: `backend/services/buscar_produto_por_id_service.py`
- Create: `backend/services/atualizar_produto_service.py`
- Create: `backend/services/deletar_produto_service.py`
- Create: `backend/services/atualizar_estoque_produto_service.py`
- Create: `backend/controllers/produto_controller.py`
- Modify: `backend/app_novo.py`

**Interfaces:**
- Consumes: `Produto` (Task 3), `Fornecedor` (Task 2), `MovimentacaoEstoque` (Task 5), `ProdutoRepository.buscar_com_status` (Task 7).
- Produces:
  - `CriarProdutoService().executar(dados) -> dict`
  - `ListarProdutosService().executar(fornecedor_id=None, busca=None) -> list[dict]` — via Repository
  - `BuscarProdutoPorIdService().executar(produto_id) -> dict | None`
  - `AtualizarProdutoService().executar(produto_id, dados) -> dict | None`
  - `DeletarProdutoService().executar(produto_id) -> bool` — remoção lógica
  - `AtualizarEstoqueProdutoService().executar(produto_id, dados) -> dict | None`
  - Blueprint `produto_controller`.

- [ ] **Step 1: Criar `backend/services/criar_produto_service.py`**

```python
from models.fornecedor_model import Fornecedor
from models.produto_model import Produto


class CriarProdutoService:
    CAMPOS_OBRIGATORIOS = ("fornecedor_id", "sku", "nome", "preco_unitario")

    def executar(self, dados):
        for campo in self.CAMPOS_OBRIGATORIOS:
            if dados.get(campo) in (None, ""):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        fornecedor_id = self._inteiro(dados["fornecedor_id"], "fornecedor_id", minimo=1)
        if Fornecedor.buscar_por_id(fornecedor_id) is None:
            raise ValueError("Fornecedor não encontrado.")

        if Produto.buscar_por_sku(fornecedor_id, dados["sku"]):
            raise ValueError("Já existe um produto com este SKU para o fornecedor.")

        produto = Produto(
            fornecedor_id=fornecedor_id,
            sku=dados["sku"],
            nome=dados["nome"],
            categoria=dados.get("categoria"),
            preco_unitario=self._decimal(dados["preco_unitario"], "preco_unitario"),
            quantidade=self._inteiro(dados.get("quantidade", 0), "quantidade", minimo=0),
            estoque_minimo=self._inteiro(dados.get("estoque_minimo", 5), "estoque_minimo", minimo=0),
            prazo_entrega_dias=self._inteiro(
                dados.get("prazo_entrega_dias", 2), "prazo_entrega_dias", minimo=0
            ),
            ativo=True,
        )
        produto.salvar()
        return produto.to_dict()

    @staticmethod
    def _inteiro(valor, nome_campo, minimo=None):
        try:
            numero = int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O campo '{nome_campo}' deve ser um número inteiro.") from erro
        if minimo is not None and numero < minimo:
            raise ValueError(f"O campo '{nome_campo}' deve ser maior ou igual a {minimo}.")
        return numero

    @staticmethod
    def _decimal(valor, nome_campo):
        try:
            numero = float(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O campo '{nome_campo}' deve ser um número.") from erro
        if numero < 0:
            raise ValueError(f"O campo '{nome_campo}' não pode ser negativo.")
        return numero
```

- [ ] **Step 2: Criar `backend/services/listar_produtos_service.py`**

```python
from repositories.produto_repository import ProdutoRepository


class ListarProdutosService:
    def executar(self, fornecedor_id=None, busca=None):
        if fornecedor_id in (None, ""):
            fornecedor_id_convertido = None
        else:
            try:
                fornecedor_id_convertido = int(fornecedor_id)
            except (TypeError, ValueError) as erro:
                raise ValueError("O filtro 'fornecedor_id' deve ser um número inteiro.") from erro

        termo = busca.strip() if isinstance(busca, str) and busca.strip() else None

        return ProdutoRepository.buscar_com_status(fornecedor_id_convertido, termo)
```

- [ ] **Step 3: Criar `backend/services/buscar_produto_por_id_service.py`**

```python
from models.produto_model import Produto


class BuscarProdutoPorIdService:
    def executar(self, produto_id):
        produto = Produto.buscar_por_id(produto_id)
        if produto is None:
            return None
        return produto.to_dict()
```

- [ ] **Step 4: Criar `backend/services/atualizar_produto_service.py`**

```python
from models.fornecedor_model import Fornecedor
from models.produto_model import Produto


class AtualizarProdutoService:
    def executar(self, produto_id, dados):
        produto = Produto.buscar_por_id(produto_id)
        if produto is None:
            return None

        fornecedor_id = produto.fornecedor_id
        if dados.get("fornecedor_id") not in (None, ""):
            fornecedor_id = int(dados["fornecedor_id"])
            if Fornecedor.buscar_por_id(fornecedor_id) is None:
                raise ValueError("Fornecedor não encontrado.")

        novo_sku = dados.get("sku") or produto.sku
        existente = Produto.buscar_por_sku(fornecedor_id, novo_sku)
        if existente and existente.id != produto.id:
            raise ValueError("Já existe um produto com este SKU para o fornecedor.")

        produto.atualizar(
            fornecedor_id=fornecedor_id,
            sku=dados.get("sku"),
            nome=dados.get("nome"),
            categoria=dados.get("categoria"),
            preco_unitario=dados.get("preco_unitario"),
            estoque_minimo=dados.get("estoque_minimo"),
            prazo_entrega_dias=dados.get("prazo_entrega_dias"),
            ativo=dados.get("ativo"),
        )
        return produto.to_dict()
```

`quantidade` não entra aqui de propósito: mudar estoque é o caso de uso do
`AtualizarEstoqueProdutoService`, que também registra a movimentação.

- [ ] **Step 5: Criar `backend/services/deletar_produto_service.py`**

```python
from models.produto_model import Produto


class DeletarProdutoService:
    def executar(self, produto_id):
        produto = Produto.buscar_por_id(produto_id)
        if produto is None:
            return False

        # Remocao logica: o produto pode estar referenciado em pedidos antigos.
        produto.desativar()
        return True
```

- [ ] **Step 6: Criar `backend/services/atualizar_estoque_produto_service.py`**

```python
from models.database import db
from models.movimentacao_estoque_model import MovimentacaoEstoque
from models.produto_model import Produto


class AtualizarEstoqueProdutoService:
    def executar(self, produto_id, dados):
        if dados.get("quantidade") in (None, ""):
            raise ValueError("O campo 'quantidade' é obrigatório.")

        try:
            quantidade = int(dados["quantidade"])
        except (TypeError, ValueError) as erro:
            raise ValueError("O campo 'quantidade' deve ser um número inteiro.") from erro

        if quantidade < 0:
            raise ValueError("O campo 'quantidade' não pode ser negativo.")

        motivo = dados.get("motivo") or "Atualização manual"

        try:
            produto = Produto.buscar_para_atualizacao(produto_id)
            if produto is None:
                db.session.rollback()
                return None

            variacao = quantidade - produto.quantidade
            produto.quantidade = quantidade

            db.session.add(
                MovimentacaoEstoque(
                    produto_id=produto.id,
                    fornecedor_id=produto.fornecedor_id,
                    tipo_movimentacao="ajuste",
                    variacao_quantidade=variacao,
                    motivo=motivo,
                    referencia_tipo="manual",
                    referencia_id=None,
                )
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return produto.to_dict()
```

- [ ] **Step 7: Criar `backend/controllers/produto_controller.py`**

```python
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.criar_produto_service import CriarProdutoService
from services.listar_produtos_service import ListarProdutosService
from services.buscar_produto_por_id_service import BuscarProdutoPorIdService
from services.atualizar_produto_service import AtualizarProdutoService
from services.deletar_produto_service import DeletarProdutoService
from services.atualizar_estoque_produto_service import AtualizarEstoqueProdutoService

produto_controller = Blueprint("produto_controller", __name__)


@produto_controller.get("/produtos")
def listar_produtos():
    try:
        service = ListarProdutosService()
        produtos = service.executar(
            fornecedor_id=request.args.get("fornecedor_id"),
            busca=request.args.get("busca"),
        )
        return jsonify(produtos), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar produtos."}), 500


@produto_controller.post("/produtos")
def criar_produto():
    try:
        dados = request.get_json() or {}
        service = CriarProdutoService()
        return jsonify(service.executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar produto no banco de dados."}), 500


@produto_controller.get("/produtos/<int:produto_id>")
def buscar_produto_por_id(produto_id):
    try:
        service = BuscarProdutoPorIdService()
        produto = service.executar(produto_id)
        if produto is None:
            return jsonify({"erro": "Produto não encontrado."}), 404
        return jsonify(produto), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao buscar produto."}), 500


@produto_controller.put("/produtos/<int:produto_id>")
def atualizar_produto(produto_id):
    try:
        dados = request.get_json() or {}
        service = AtualizarProdutoService()
        produto = service.executar(produto_id, dados)
        if produto is None:
            return jsonify({"erro": "Produto não encontrado."}), 404
        return jsonify(produto), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar produto no banco de dados."}), 500


@produto_controller.delete("/produtos/<int:produto_id>")
def deletar_produto(produto_id):
    try:
        service = DeletarProdutoService()
        if service.executar(produto_id) is False:
            return jsonify({"erro": "Produto não encontrado."}), 404
        return "", 204
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao remover produto do banco de dados."}), 500


@produto_controller.patch("/produtos/<int:produto_id>/estoque")
def atualizar_estoque_produto(produto_id):
    try:
        dados = request.get_json() or {}
        service = AtualizarEstoqueProdutoService()
        produto = service.executar(produto_id, dados)
        if produto is None:
            return jsonify({"erro": "Produto não encontrado."}), 404
        return jsonify(produto), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar o estoque do produto."}), 500
```

- [ ] **Step 8: Registrar o blueprint no `backend/app_novo.py`**

```python
from controllers.produto_controller import produto_controller
```
```python
    app.register_blueprint(produto_controller)
```

- [ ] **Step 9: Exercitar as rotas**

Reiniciar o servidor da 5001 e rodar:
```bash
curl -s http://127.0.0.1:5001/produtos -w ' [%{http_code}]\n' | head -c 400; echo
curl -s "http://127.0.0.1:5001/produtos?busca=Arroz" | /home/stock-map/.venv/bin/python -c "import sys,json; d=json.load(sys.stdin); print(len(d), d[0]['nome'], d[0]['status_estoque'])"
curl -s "http://127.0.0.1:5001/produtos?fornecedor_id=2" | /home/stock-map/.venv/bin/python -c "import sys,json; print(len(json.load(sys.stdin)))"
curl -s -X PATCH http://127.0.0.1:5001/produtos/2/estoque -H 'Content-Type: application/json' \
  -d '{"quantidade":40,"motivo":"Reposicao de teste"}' -w ' [%{http_code}]\n'
curl -s -X POST http://127.0.0.1:5001/produtos -H 'Content-Type: application/json' \
  -d '{"fornecedor_id":1,"sku":"ARZ-5KG","nome":"Duplicado","preco_unitario":1}' -w ' [%{http_code}]\n'
```
Expected:
- listagem: 3 produtos, `200`
- busca `Arroz`: `1 Arroz tipo 1 - 5kg disponivel`
- filtro por fornecedor 2: `1`
- ajuste de estoque: `200`, e o corpo mostra `"quantidade": 40` com `"status_estoque": "disponivel"`
- SKU duplicado: `{"erro":"Já existe um produto com este SKU para o fornecedor."} [400]`

Confirmar que a movimentação de ajuste foi registrada:
```bash
cd /home/stock-map/backend && set -a && . ./.env && set +a && \
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -N \
  -e "SELECT tipo_movimentacao, variacao_quantidade, motivo FROM movimentacoes_estoque ORDER BY id DESC LIMIT 1;"
```
Expected: `ajuste	32	Reposicao de teste`

- [ ] **Step 10: Commit**

```bash
cd /home/stock-map
git add backend/services/criar_produto_service.py backend/services/listar_produtos_service.py \
        backend/services/buscar_produto_por_id_service.py backend/services/atualizar_produto_service.py \
        backend/services/deletar_produto_service.py backend/services/atualizar_estoque_produto_service.py \
        backend/controllers/produto_controller.py backend/app_novo.py
git commit -m "feat: adiciona caso de uso de produto usando repository e movimentacao"
```

---

### Task 11: Caso de uso Pedido — 4 services e o controller

**Files:**
- Create: `backend/services/criar_pedido_service.py`
- Create: `backend/services/listar_pedidos_service.py`
- Create: `backend/services/buscar_pedido_por_id_service.py`
- Create: `backend/services/atualizar_status_pedido_service.py`
- Create: `backend/controllers/pedido_controller.py`
- Modify: `backend/app_novo.py`

**Interfaces:**
- Consumes: `Pedido`, `ItemPedido` (Task 4), `Produto` (Task 3), `Lojista`, `Fornecedor` (Task 2), `MovimentacaoEstoque` (Task 5), `PedidoRepository` (Task 7).
- Produces:
  - `CriarPedidoService().executar(dados) -> dict`
  - `ListarPedidosService().executar(status=None, lojista_id=None, data_inicio=None, data_fim=None) -> list[dict]`
  - `BuscarPedidoPorIdService().executar(pedido_id) -> dict | None` — o dicionário traz a chave `itens`
  - `AtualizarStatusPedidoService().executar(pedido_id, dados) -> dict | None`
  - Blueprint `pedido_controller`.

`CriarPedidoService` e `AtualizarStatusPedidoService` são os casos transacionais: usam `db.session` com um único `commit()`, conforme a seção "Transações" do spec.

- [ ] **Step 1: Criar `backend/services/criar_pedido_service.py`**

```python
from decimal import Decimal

from models.database import db
from models.fornecedor_model import Fornecedor
from models.lojista_model import Lojista
from models.movimentacao_estoque_model import MovimentacaoEstoque
from models.pedido_model import ItemPedido, Pedido
from models.produto_model import Produto


class CriarPedidoService:
    """Grava pedido, itens, baixa de estoque e movimentacoes em uma transacao."""

    def executar(self, dados):
        lojista_id = self._inteiro(dados.get("lojista_id"), "lojista_id", minimo=1)
        fornecedor_id = self._inteiro(dados.get("fornecedor_id"), "fornecedor_id", minimo=1)

        itens = dados.get("itens") or []
        if not itens:
            raise ValueError("Inclua ao menos um item no pedido.")

        lojista = Lojista.buscar_por_id(lojista_id)
        if lojista is None:
            raise ValueError("Lojista não encontrado.")
        if Fornecedor.buscar_por_id(fornecedor_id) is None:
            raise ValueError("Fornecedor não encontrado.")

        try:
            pedido = Pedido(
                lojista_id=lojista_id,
                fornecedor_id=fornecedor_id,
                status="confirmado",
                observacoes=dados.get("observacoes"),
                valor_total=Decimal("0"),
                endereco_entrega=dados.get("endereco_entrega") or lojista.endereco,
            )
            db.session.add(pedido)
            db.session.flush()  # atribui pedido.id sem encerrar a transacao

            total = Decimal("0")
            for item in itens:
                produto_id = self._inteiro(item.get("produto_id"), "produto_id", minimo=1)
                quantidade = self._inteiro(item.get("quantidade"), "quantidade", minimo=1)

                produto = Produto.buscar_para_atualizacao(produto_id)
                if produto is None or not produto.ativo:
                    raise ValueError("Produto não encontrado.")
                if produto.fornecedor_id != fornecedor_id:
                    raise ValueError(
                        f"O produto {produto.nome} não pertence ao fornecedor selecionado."
                    )
                if produto.quantidade < quantidade:
                    raise ValueError(
                        f"Estoque insuficiente para {produto.nome}. "
                        f"Disponível: {produto.quantidade}."
                    )

                subtotal = produto.preco_unitario * quantidade
                total += subtotal

                db.session.add(
                    ItemPedido(
                        pedido_id=pedido.id,
                        produto_id=produto.id,
                        quantidade=quantidade,
                        preco_unitario=produto.preco_unitario,
                        subtotal=subtotal,
                    )
                )
                produto.quantidade = produto.quantidade - quantidade
                db.session.add(
                    MovimentacaoEstoque(
                        produto_id=produto.id,
                        fornecedor_id=fornecedor_id,
                        tipo_movimentacao="saida",
                        variacao_quantidade=-quantidade,
                        motivo="Pedido confirmado",
                        referencia_tipo="pedido",
                        referencia_id=pedido.id,
                    )
                )

            pedido.valor_total = total
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return pedido.to_dict()

    @staticmethod
    def _inteiro(valor, nome_campo, minimo=None):
        try:
            numero = int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O campo '{nome_campo}' deve ser um número inteiro.") from erro
        if minimo is not None and numero < minimo:
            raise ValueError(f"O campo '{nome_campo}' deve ser maior ou igual a {minimo}.")
        return numero
```

- [ ] **Step 2: Criar `backend/services/listar_pedidos_service.py`**

```python
from datetime import datetime

from models.pedido_model import Pedido
from repositories.pedido_repository import PedidoRepository


class ListarPedidosService:
    def executar(self, status=None, lojista_id=None, data_inicio=None, data_fim=None):
        if status not in (None, "") and status not in Pedido.STATUS_VALIDOS:
            raise ValueError(
                "Status inválido. Use: " + ", ".join(Pedido.STATUS_VALIDOS) + "."
            )

        return PedidoRepository.buscar_filtrados(
            status=status or None,
            lojista_id=self._inteiro(lojista_id, "lojista_id"),
            data_inicio=self._data(data_inicio, "data_inicio"),
            data_fim=self._data(data_fim, "data_fim"),
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
            raise ValueError(f"O filtro '{nome_campo}' deve estar no formato AAAA-MM-DD.") from erro
```

- [ ] **Step 3: Criar `backend/services/buscar_pedido_por_id_service.py`**

```python
from repositories.pedido_repository import PedidoRepository


class BuscarPedidoPorIdService:
    def executar(self, pedido_id):
        pedido = PedidoRepository.buscar_detalhe(pedido_id)
        if pedido is None:
            return None
        pedido["itens"] = PedidoRepository.buscar_itens(pedido_id)
        return pedido
```

- [ ] **Step 4: Criar `backend/services/atualizar_status_pedido_service.py`**

```python
from models.database import db
from models.movimentacao_estoque_model import MovimentacaoEstoque
from models.pedido_model import ItemPedido, Pedido
from models.produto_model import Produto


class AtualizarStatusPedidoService:
    """Troca o status do pedido e devolve o estoque quando ele e cancelado."""

    def executar(self, pedido_id, dados):
        status = dados.get("status")
        if status not in Pedido.STATUS_VALIDOS:
            raise ValueError(
                "Status inválido. Use: " + ", ".join(Pedido.STATUS_VALIDOS) + "."
            )

        try:
            pedido = Pedido.buscar_para_atualizacao(pedido_id)
            if pedido is None:
                db.session.rollback()
                return None

            anterior = pedido.status
            if anterior == status:
                db.session.rollback()
                return pedido.to_dict()

            if anterior == "cancelado":
                raise ValueError("Pedido cancelado não pode mudar de status.")

            if status == "cancelado":
                itens = ItemPedido.query.filter_by(pedido_id=pedido.id).all()
                for item in itens:
                    produto = Produto.buscar_para_atualizacao(item.produto_id)
                    if produto is None:
                        continue
                    produto.quantidade = produto.quantidade + item.quantidade
                    db.session.add(
                        MovimentacaoEstoque(
                            produto_id=produto.id,
                            fornecedor_id=pedido.fornecedor_id,
                            tipo_movimentacao="entrada",
                            variacao_quantidade=item.quantidade,
                            motivo="Pedido cancelado",
                            referencia_tipo="cancelamento_pedido",
                            referencia_id=pedido.id,
                        )
                    )

            pedido.status = status
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return pedido.to_dict()
```

- [ ] **Step 5: Criar `backend/controllers/pedido_controller.py`**

```python
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.criar_pedido_service import CriarPedidoService
from services.listar_pedidos_service import ListarPedidosService
from services.buscar_pedido_por_id_service import BuscarPedidoPorIdService
from services.atualizar_status_pedido_service import AtualizarStatusPedidoService

pedido_controller = Blueprint("pedido_controller", __name__)


@pedido_controller.get("/pedidos")
def listar_pedidos():
    try:
        service = ListarPedidosService()
        pedidos = service.executar(
            status=request.args.get("status"),
            lojista_id=request.args.get("lojista_id"),
            data_inicio=request.args.get("data_inicio"),
            data_fim=request.args.get("data_fim"),
        )
        return jsonify(pedidos), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar pedidos."}), 500


@pedido_controller.post("/pedidos")
def criar_pedido():
    try:
        dados = request.get_json() or {}
        service = CriarPedidoService()
        return jsonify(service.executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar pedido no banco de dados."}), 500


@pedido_controller.get("/pedidos/<int:pedido_id>")
def buscar_pedido_por_id(pedido_id):
    try:
        service = BuscarPedidoPorIdService()
        pedido = service.executar(pedido_id)
        if pedido is None:
            return jsonify({"erro": "Pedido não encontrado."}), 404
        return jsonify(pedido), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao buscar pedido."}), 500


@pedido_controller.patch("/pedidos/<int:pedido_id>/status")
def atualizar_status_pedido(pedido_id):
    try:
        dados = request.get_json() or {}
        service = AtualizarStatusPedidoService()
        pedido = service.executar(pedido_id, dados)
        if pedido is None:
            return jsonify({"erro": "Pedido não encontrado."}), 404
        return jsonify(pedido), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar o status do pedido."}), 500
```

- [ ] **Step 6: Registrar o blueprint no `backend/app_novo.py`**

```python
from controllers.pedido_controller import pedido_controller
```
```python
    app.register_blueprint(pedido_controller)
```

- [ ] **Step 7: Verificar o caminho feliz e a baixa de estoque**

Reiniciar o servidor da 5001. Guardar a quantidade do produto 1 antes:
```bash
ANTES=$(curl -s http://127.0.0.1:5001/produtos/1 | /home/stock-map/.venv/bin/python -c "import sys,json; print(json.load(sys.stdin)['quantidade'])")
echo "antes: $ANTES"
curl -s -X POST http://127.0.0.1:5001/pedidos -H 'Content-Type: application/json' \
  -d '{"lojista_id":1,"fornecedor_id":1,"itens":[{"produto_id":1,"quantidade":5}],"observacoes":"Pedido de teste"}' \
  -w ' [%{http_code}]\n'
DEPOIS=$(curl -s http://127.0.0.1:5001/produtos/1 | /home/stock-map/.venv/bin/python -c "import sys,json; print(json.load(sys.stdin)['quantidade'])")
echo "depois: $DEPOIS"
```
Expected: criação `201` com `"valor_total": 144.5`; `depois` é exatamente `antes - 5`.

- [ ] **Step 8: Verificar estoque insuficiente e produto de outro fornecedor**

Run:
```bash
curl -s -X POST http://127.0.0.1:5001/pedidos -H 'Content-Type: application/json' \
  -d '{"lojista_id":1,"fornecedor_id":1,"itens":[{"produto_id":1,"quantidade":99999}]}' -w ' [%{http_code}]\n'
curl -s -X POST http://127.0.0.1:5001/pedidos -H 'Content-Type: application/json' \
  -d '{"lojista_id":1,"fornecedor_id":1,"itens":[{"produto_id":3,"quantidade":1}]}' -w ' [%{http_code}]\n'
curl -s -X POST http://127.0.0.1:5001/pedidos -H 'Content-Type: application/json' \
  -d '{"lojista_id":1,"fornecedor_id":1,"itens":[]}' -w ' [%{http_code}]\n'
```
Expected, todos `400`:
- `{"erro":"Estoque insuficiente para Arroz tipo 1 - 5kg. Disponível: ..."}`
- `{"erro":"O produto Detergente neutro 500ml não pertence ao fornecedor selecionado."}`
- `{"erro":"Inclua ao menos um item no pedido."}`

Conferir que nenhum pedido órfão sobrou do rollback:
```bash
cd /home/stock-map/backend && set -a && . ./.env && set +a && \
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -N \
  -e "SELECT COUNT(*) FROM pedidos; SELECT COUNT(*) FROM itens_pedido;"
```
Expected: `1` e `1` — apenas o pedido válido do Step 7.

- [ ] **Step 9: Verificar filtros, detalhe e cancelamento**

Run:
```bash
curl -s "http://127.0.0.1:5001/pedidos" | /home/stock-map/.venv/bin/python -c "import sys,json; d=json.load(sys.stdin); print(len(d), d[0]['status'], d[0]['total_itens'], d[0]['lojista_nome'])"
curl -s "http://127.0.0.1:5001/pedidos?status=cancelado" | /home/stock-map/.venv/bin/python -c "import sys,json; print(len(json.load(sys.stdin)))"
curl -s "http://127.0.0.1:5001/pedidos?status=invalido" -w ' [%{http_code}]\n'
curl -s http://127.0.0.1:5001/pedidos/1 | /home/stock-map/.venv/bin/python -c "import sys,json; d=json.load(sys.stdin); print(d['status'], len(d['itens']), d['itens'][0]['produto_nome'])"
curl -s -X PATCH http://127.0.0.1:5001/pedidos/1/status -H 'Content-Type: application/json' \
  -d '{"status":"cancelado"}' -w ' [%{http_code}]\n'
curl -s http://127.0.0.1:5001/produtos/1 | /home/stock-map/.venv/bin/python -c "import sys,json; print('estoque devolvido:', json.load(sys.stdin)['quantidade'])"
curl -s -X PATCH http://127.0.0.1:5001/pedidos/1/status -H 'Content-Type: application/json' \
  -d '{"status":"entregue"}' -w ' [%{http_code}]\n'
```
Expected:
- listagem: `1 confirmado 1 Mercado Bom Preco`
- filtro `cancelado`: `0`
- filtro inválido: `400`
- detalhe: `confirmado 1 Arroz tipo 1 - 5kg`
- cancelamento: `200`
- estoque volta ao valor de `$ANTES` do Step 7
- reabrir pedido cancelado: `{"erro":"Pedido cancelado não pode mudar de status."} [400]`

- [ ] **Step 10: Commit**

```bash
cd /home/stock-map
git add backend/services/criar_pedido_service.py backend/services/listar_pedidos_service.py \
        backend/services/buscar_pedido_por_id_service.py \
        backend/services/atualizar_status_pedido_service.py \
        backend/controllers/pedido_controller.py backend/app_novo.py
git commit -m "feat: adiciona caso de uso de pedido com transacao e filtros por procedure"
```

---

### Task 12: Alertas, Relatórios e Movimentações — 3 services e 3 controllers

**Files:**
- Create: `backend/services/listar_alertas_estoque_baixo_service.py`
- Create: `backend/services/gerar_relatorio_service.py`
- Create: `backend/services/listar_historico_movimentacoes_service.py`
- Create: `backend/controllers/alerta_controller.py`
- Create: `backend/controllers/relatorio_controller.py`
- Create: `backend/controllers/movimentacao_controller.py`
- Modify: `backend/app_novo.py`

**Interfaces:**
- Consumes: `AlertaRepository`, `RelatorioRepository`, `MovimentacaoRepository` (Task 7).
- Produces:
  - `ListarAlertasEstoqueBaixoService().executar() -> list[dict]`
  - `GerarRelatorioService().executar(data_inicio=None, data_fim=None) -> dict` com as chaves `periodo`, `resumo`, `top_produtos`, `desempenho_fornecedores`
  - `ListarHistoricoMovimentacoesService().executar(produto_id=None, fornecedor_id=None, data_inicio=None, data_fim=None) -> list[dict]`
  - Blueprints `alerta_controller`, `relatorio_controller`, `movimentacao_controller`.

- [ ] **Step 1: Criar `backend/services/listar_alertas_estoque_baixo_service.py`**

```python
from repositories.alerta_repository import AlertaRepository


class ListarAlertasEstoqueBaixoService:
    def executar(self):
        return AlertaRepository.listar_estoque_baixo()
```

- [ ] **Step 2: Criar `backend/services/gerar_relatorio_service.py`**

```python
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
```

- [ ] **Step 3: Criar `backend/services/listar_historico_movimentacoes_service.py`**

```python
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
```

- [ ] **Step 4: Criar `backend/controllers/alerta_controller.py`**

```python
from flask import Blueprint, jsonify
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.listar_alertas_estoque_baixo_service import ListarAlertasEstoqueBaixoService

alerta_controller = Blueprint("alerta_controller", __name__)


@alerta_controller.get("/alertas")
def listar_alertas():
    try:
        service = ListarAlertasEstoqueBaixoService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar alertas de estoque."}), 500
```

- [ ] **Step 5: Criar `backend/controllers/relatorio_controller.py`**

```python
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.gerar_relatorio_service import GerarRelatorioService

relatorio_controller = Blueprint("relatorio_controller", __name__)


@relatorio_controller.get("/relatorios")
def gerar_relatorio():
    try:
        service = GerarRelatorioService()
        relatorio = service.executar(
            data_inicio=request.args.get("data_inicio"),
            data_fim=request.args.get("data_fim"),
        )
        return jsonify(relatorio), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao gerar o relatório."}), 500
```

- [ ] **Step 6: Criar `backend/controllers/movimentacao_controller.py`**

```python
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.listar_historico_movimentacoes_service import (
    ListarHistoricoMovimentacoesService,
)

movimentacao_controller = Blueprint("movimentacao_controller", __name__)


@movimentacao_controller.get("/movimentacoes")
def listar_movimentacoes():
    try:
        service = ListarHistoricoMovimentacoesService()
        movimentacoes = service.executar(
            produto_id=request.args.get("produto_id"),
            fornecedor_id=request.args.get("fornecedor_id"),
            data_inicio=request.args.get("data_inicio"),
            data_fim=request.args.get("data_fim"),
        )
        return jsonify(movimentacoes), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar o histórico de movimentações."}), 500
```

- [ ] **Step 7: Registrar os três blueprints no `backend/app_novo.py`**

```python
from controllers.alerta_controller import alerta_controller
from controllers.relatorio_controller import relatorio_controller
from controllers.movimentacao_controller import movimentacao_controller
```
```python
    app.register_blueprint(alerta_controller)
    app.register_blueprint(relatorio_controller)
    app.register_blueprint(movimentacao_controller)
```

- [ ] **Step 8: Exercitar as três rotas**

Reiniciar o servidor da 5001 e rodar:
```bash
curl -s http://127.0.0.1:5001/alertas | /home/stock-map/.venv/bin/python -c "import sys,json; d=json.load(sys.stdin); print(len(d), [a['severidade'] for a in d])"
curl -s http://127.0.0.1:5001/relatorios | /home/stock-map/.venv/bin/python -c "import sys,json; d=json.load(sys.stdin); print(d['periodo']); print(d['resumo']['fornecedores'], d['resumo']['lojistas'], d['resumo']['produtos']); print(len(d['desempenho_fornecedores']))"
curl -s "http://127.0.0.1:5001/relatorios?data_inicio=2020-01-01&data_fim=2030-12-31" | /home/stock-map/.venv/bin/python -c "import sys,json; print(len(json.load(sys.stdin)['top_produtos']))"
curl -s "http://127.0.0.1:5001/relatorios?data_inicio=2030-01-01&data_fim=2020-01-01" -w ' [%{http_code}]\n'
curl -s "http://127.0.0.1:5001/relatorios?data_inicio=01-01-2020" -w ' [%{http_code}]\n'
curl -s http://127.0.0.1:5001/movimentacoes | /home/stock-map/.venv/bin/python -c "import sys,json; d=json.load(sys.stdin); print(len(d), [m['tipo_movimentacao'] for m in d])"
curl -s "http://127.0.0.1:5001/movimentacoes?produto_id=1" | /home/stock-map/.venv/bin/python -c "import sys,json; print(len(json.load(sys.stdin)))"
```
Expected:
- alertas: `1 ['indisponivel']` (o produto 2 foi reposto para 40 na Task 10; sobra só o detergente zerado)
- relatórios: período com 30 dias de janela, `2 2 3`, e `2` fornecedores no desempenho
- top produtos no período largo: `1` (o arroz do pedido criado e depois cancelado não conta — o pedido está `cancelado`, então esperar `0`)
- data invertida: `400`
- data em formato errado: `400`
- movimentações: `4 ['entrada', 'saida', 'ajuste', ...]` — pelo menos o ajuste da Task 10, a saída e a entrada da Task 11
- filtro por produto 1: `2` (saída do pedido e entrada do cancelamento)

Se o número de `top_produtos` divergir, conferir o status do pedido criado na Task 11 antes de tratar como falha.

- [ ] **Step 9: Commit**

```bash
cd /home/stock-map
git add backend/services/listar_alertas_estoque_baixo_service.py \
        backend/services/gerar_relatorio_service.py \
        backend/services/listar_historico_movimentacoes_service.py \
        backend/controllers/alerta_controller.py backend/controllers/relatorio_controller.py \
        backend/controllers/movimentacao_controller.py backend/app_novo.py
git commit -m "feat: adiciona alertas, relatorio por periodo e historico de movimentacoes"
```

---

### Task 13: Caso de uso Rota — 2 services e o controller

**Files:**
- Create: `backend/services/planejar_rota_service.py`
- Create: `backend/services/listar_rotas_service.py`
- Create: `backend/controllers/rota_controller.py`
- Modify: `backend/app_novo.py`

**Interfaces:**
- Consumes: `Fornecedor` (Task 2), `RotaEntrega`, `ParadaRota` (Task 5), `RotaRepository` (Task 7).
- Produces:
  - `PlanejarRotaService().executar(dados) -> dict`
  - `ListarRotasService().executar() -> list[dict]`
  - Blueprint `rota_controller`.

A ordenação das paradas é vizinho mais próximo por haversine, partindo das coordenadas do fornecedor. Sem coordenadas, cai para ordenação por cidade e nome do lojista.

- [ ] **Step 1: Criar `backend/services/planejar_rota_service.py`**

```python
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
```

- [ ] **Step 2: Criar `backend/services/listar_rotas_service.py`**

```python
from repositories.rota_repository import RotaRepository


class ListarRotasService:
    def executar(self):
        return RotaRepository.listar_com_paradas()
```

- [ ] **Step 3: Criar `backend/controllers/rota_controller.py`**

```python
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.planejar_rota_service import PlanejarRotaService
from services.listar_rotas_service import ListarRotasService

rota_controller = Blueprint("rota_controller", __name__)


@rota_controller.get("/rotas")
def listar_rotas():
    try:
        service = ListarRotasService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao listar rotas."}), 500


@rota_controller.post("/rotas")
def planejar_rota():
    try:
        dados = request.get_json() or {}
        service = PlanejarRotaService()
        return jsonify(service.executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao planejar a rota de entrega."}), 500
```

- [ ] **Step 4: Registrar o blueprint no `backend/app_novo.py`**

```python
from controllers.rota_controller import rota_controller
```
```python
    app.register_blueprint(rota_controller)
```

- [ ] **Step 5: Preparar um pedido confirmado e planejar a rota**

O pedido da Task 11 ficou cancelado, então a roteirização não tem o que planejar. Criar dois pedidos confirmados, um para cada lojista:

```bash
curl -s -X POST http://127.0.0.1:5001/pedidos -H 'Content-Type: application/json' \
  -d '{"lojista_id":1,"fornecedor_id":1,"itens":[{"produto_id":1,"quantidade":2}]}' -w ' [%{http_code}]\n'
curl -s -X POST http://127.0.0.1:5001/pedidos -H 'Content-Type: application/json' \
  -d '{"lojista_id":2,"fornecedor_id":1,"itens":[{"produto_id":1,"quantidade":3}]}' -w ' [%{http_code}]\n'
curl -s -X POST http://127.0.0.1:5001/rotas -H 'Content-Type: application/json' \
  -d '{"fornecedor_id":1,"observacoes":"Rota de teste"}' -w ' [%{http_code}]\n'
curl -s http://127.0.0.1:5001/rotas | /home/stock-map/.venv/bin/python -c "
import sys, json
rotas = json.load(sys.stdin)
print('rotas:', len(rotas))
rota = rotas[0]
print('distancia:', rota['distancia_total_km'], 'paradas:', rota['total_paradas'])
for parada in rota['paradas']:
    print(parada['ordem_parada'], parada['lojista_nome'], parada['distancia_anterior_km'])
"
```
Expected:
- os dois pedidos: `201`
- planejamento: `201`
- listagem: `rotas: 1`, `paradas: 2`, e as paradas em ordem `1` e `2`. O fornecedor 1 está em Belo Horizonte (-19.857, -43.935), então a parada 1 é o `Mercado Bom Preco` (BH, ~7 km) e a parada 2 é o `Emporio Vila Nova` (Betim, mais distante).

- [ ] **Step 6: Verificar o caso sem pedidos para roteirizar**

Run:
```bash
curl -s -X POST http://127.0.0.1:5001/rotas -H 'Content-Type: application/json' \
  -d '{"fornecedor_id":2}' -w ' [%{http_code}]\n'
curl -s -X POST http://127.0.0.1:5001/rotas -H 'Content-Type: application/json' \
  -d '{"fornecedor_id":999}' -w ' [%{http_code}]\n'
```
Expected:
- `{"erro":"Não existem pedidos confirmados para roteirizar."} [400]`
- `{"erro":"Fornecedor não encontrado."} [400]`

- [ ] **Step 7: Commit**

```bash
cd /home/stock-map
git add backend/services/planejar_rota_service.py backend/services/listar_rotas_service.py \
        backend/controllers/rota_controller.py backend/app_novo.py
git commit -m "feat: adiciona planejamento e listagem de rotas de entrega"
```

---

### Task 14: Frontend — estrutura de pastas e HTML sem Jinja

**Files:**
- Create: `frontend/index.html` (a partir de `frontend/templates/index.html`)
- Create: `frontend/css/style.css` (movido de `frontend/static/css/styles.css`)
- Create: `frontend/img/stockmap-logo.svg` (movido de `frontend/static/img/`)
- Create: `frontend/js/app.js` (movido de `frontend/static/js/app.js`, reescrito na Task 15)

**Interfaces:**
- Consumes: nada do backend em tempo de build.
- Produces: os `id` e `data-view` que o `app.js` da Task 15 consulta. Nomes novos listados abaixo.

- [ ] **Step 1: Mover os arquivos com `git mv`**

```bash
cd /home/stock-map
mkdir -p frontend/css frontend/js frontend/img
git mv frontend/static/css/styles.css frontend/css/style.css
git mv frontend/static/js/app.js frontend/js/app.js
git mv frontend/static/img/stockmap-logo.svg frontend/img/stockmap-logo.svg
git mv frontend/templates/index.html frontend/index.html
rmdir frontend/static/css frontend/static/js frontend/static/img frontend/static frontend/templates
```

- [ ] **Step 2: Trocar as quatro referências Jinja do `frontend/index.html`**

| Linha original | Substituir por |
|---|---|
| `href="{{ url_for('static', filename='img/stockmap-logo.svg') }}"` (favicon) | `href="img/stockmap-logo.svg"` |
| `href="{{ url_for('static', filename='css/styles.css') }}"` | `href="css/style.css"` |
| `src="{{ url_for('static', filename='img/stockmap-logo.svg') }}"` (logo) | `src="img/stockmap-logo.svg"` |
| `src="{{ url_for('static', filename='js/app.js') }}"` | `src="js/app.js"` |

Depois disso o arquivo não pode conter nenhum `{{` nem `{%`.

- [ ] **Step 3: Renomear os `data-view` e os `id` das seções para português**

Na `<nav class="nav-list">`, trocar os `data-view` e acrescentar o item novo:

```html
        <nav class="nav-list">
          <button class="nav-link active" type="button" data-view="painel">Painel</button>
          <button class="nav-link" type="button" data-view="fornecedores">Fornecedores</button>
          <button class="nav-link" type="button" data-view="lojistas">Lojistas</button>
          <button class="nav-link" type="button" data-view="produtos">Produtos</button>
          <button class="nav-link" type="button" data-view="pedidos">Pedidos</button>
          <button class="nav-link" type="button" data-view="alertas">Alertas</button>
          <button class="nav-link" type="button" data-view="relatorios">Relatorios</button>
          <button class="nav-link" type="button" data-view="rotas">Rotas</button>
          <button class="nav-link" type="button" data-view="movimentacoes">Movimentacoes</button>
        </nav>
```

E os `id` das `<section class="view">`, na mesma ordem: `dashboard` → `painel`, `suppliers` → `fornecedores`, `retailers` → `lojistas`, `products` → `produtos`, `orders` → `pedidos`, `alerts` → `alertas`, `reports` → `relatorios`, `routes` → `rotas`.

- [ ] **Step 4: Renomear os `name` dos campos dos formulários**

O `app.js` monta o JSON a partir do `name` de cada input, então os nomes precisam bater com o contrato da API.

Formulários `#supplier-form` e `#retailer-form`:

| `name` atual | `name` novo |
|---|---|
| `name` | `nome` |
| `contact_name` | `nome_contato` |
| `phone` | `telefone` |
| `address` | `endereco` |
| `city` | `cidade` |
| `state` | `estado` |

`cnpj`, `email`, `latitude` e `longitude` não mudam.

Formulário `#product-form`:

| `name` atual | `name` novo |
|---|---|
| `supplier_id` | `fornecedor_id` |
| `name` | `nome` |
| `category` | `categoria` |
| `unit_price` | `preco_unitario` |
| `quantity` | `quantidade` |
| `min_stock` | `estoque_minimo` |
| `lead_time_days` | `prazo_entrega_dias` |

`sku` não muda.

Formulário `#order-form`:

| `name` atual | `name` novo |
|---|---|
| `retailer_id` | `lojista_id` |
| `supplier_id` | `fornecedor_id` |
| `delivery_address` | `endereco_entrega` |
| `notes` | `observacoes` |

Formulário `#route-form`:

| `name` atual | `name` novo |
|---|---|
| `supplier_id` | `fornecedor_id` |
| `notes` | `observacoes` |

- [ ] **Step 5: Renomear os `id` usados pelo JavaScript**

| `id` atual | `id` novo |
|---|---|
| `supplier-form` | `form-fornecedor` |
| `supplier-list` | `lista-fornecedores` |
| `supplier-count` | `contador-fornecedores` |
| `retailer-form` | `form-lojista` |
| `retailer-list` | `lista-lojistas` |
| `retailer-count` | `contador-lojistas` |
| `product-form` | `form-produto` |
| `product-supplier` | `produto-fornecedor` |
| `product-table` | `tabela-produtos` |
| `product-search` | `busca-produto` |
| `order-form` | `form-pedido` |
| `order-retailer` | `pedido-lojista` |
| `order-supplier` | `pedido-fornecedor` |
| `order-product` | `pedido-produto` |
| `order-quantity` | `pedido-quantidade` |
| `add-order-item` | `adicionar-item-pedido` |
| `order-items` | `itens-pedido` |
| `order-table` | `tabela-pedidos` |
| `order-count` | `contador-pedidos` |
| `alert-list` | `lista-alertas` |
| `alert-count` | `contador-alertas` |
| `alerts-view-count` | `contador-alertas-tela` |
| `dashboard-alerts` | `painel-alertas` |
| `recent-orders` | `pedidos-recentes` |
| `metric-grid` | `grade-metricas` |
| `top-products` | `top-produtos` |
| `supplier-performance` | `desempenho-fornecedores` |
| `route-form` | `form-rota` |
| `route-supplier` | `rota-fornecedor` |
| `route-list` | `lista-rotas` |
| `route-count` | `contador-rotas` |
| `refresh-button` | `botao-atualizar` |
| `view-title` | `titulo-tela` |
| `chart-order-status` | `grafico-status-pedidos` |
| `chart-stock-status` | `grafico-status-estoque` |
| `chart-top-products` | `grafico-top-produtos` |
| `chart-supplier-revenue` | `grafico-faturamento-fornecedor` |

`#toast` e `#main` não mudam.

- [ ] **Step 6: Acrescentar a barra de filtros na tela de Pedidos**

Dentro de `<section id="pedidos" class="view">`, logo antes de `<div class="form-grid">`:

```html
          <form id="filtros-pedidos" class="panel filter-bar">
            <label>Status
              <select name="status">
                <option value="">Todos</option>
                <option value="pendente">Pendente</option>
                <option value="confirmado">Confirmado</option>
                <option value="despachado">Despachado</option>
                <option value="entregue">Entregue</option>
                <option value="cancelado">Cancelado</option>
              </select>
            </label>
            <label>Lojista<select name="lojista_id" id="filtro-pedido-lojista"></select></label>
            <label>De<input name="data_inicio" type="date"></label>
            <label>Ate<input name="data_fim" type="date"></label>
            <button class="btn btn-secondary" type="submit">Filtrar</button>
            <button class="btn btn-secondary" type="button" id="limpar-filtros-pedidos">Limpar</button>
          </form>
```

- [ ] **Step 7: Acrescentar o seletor de período na tela de Relatórios**

Dentro de `<section id="relatorios" class="view">`, antes de `<div class="split-grid">`:

```html
          <form id="filtros-relatorio" class="panel filter-bar">
            <label>De<input name="data_inicio" type="date"></label>
            <label>Ate<input name="data_fim" type="date"></label>
            <button class="btn btn-secondary" type="submit">Aplicar periodo</button>
            <span class="pill" id="periodo-relatorio">Ultimos 30 dias</span>
          </form>
```

- [ ] **Step 8: Acrescentar a tela nova de Movimentações**

Depois de `<section id="rotas" class="view">...</section>` e antes do fechamento de `</main>`:

```html
        <section id="movimentacoes" class="view" aria-labelledby="titulo-tela">
          <form id="filtros-movimentacoes" class="panel filter-bar">
            <label>Produto<select name="produto_id" id="filtro-movimentacao-produto"></select></label>
            <label>Fornecedor<select name="fornecedor_id" id="filtro-movimentacao-fornecedor"></select></label>
            <label>De<input name="data_inicio" type="date"></label>
            <label>Ate<input name="data_fim" type="date"></label>
            <button class="btn btn-secondary" type="submit">Filtrar</button>
            <button class="btn btn-secondary" type="button" id="limpar-filtros-movimentacoes">Limpar</button>
          </form>
          <section class="panel">
            <div class="panel-heading">
              <h2>Historico de estoque</h2>
              <span class="pill" id="contador-movimentacoes">0</span>
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Produto</th>
                    <th>Fornecedor</th>
                    <th>Tipo</th>
                    <th>Variacao</th>
                    <th>Motivo</th>
                  </tr>
                </thead>
                <tbody id="tabela-movimentacoes"></tbody>
              </table>
            </div>
          </section>
        </section>
```

- [ ] **Step 9: Acrescentar o estilo da barra de filtros ao `frontend/css/style.css`**

No fim do arquivo:

```css
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 18px;
}

.filter-bar label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
}

.filter-bar input,
.filter-bar select {
  min-width: 150px;
}
```

- [ ] **Step 10: Verificar que não sobrou Jinja e que a estrutura fecha**

Run:
```bash
cd /home/stock-map
grep -c "{{\|{%" frontend/index.html || echo "0 ocorrencias de Jinja"
grep -o 'data-view="[a-z]*"' frontend/index.html
grep -o 'id="\(painel\|fornecedores\|lojistas\|produtos\|pedidos\|alertas\|relatorios\|rotas\|movimentacoes\)"' frontend/index.html
/home/stock-map/.venv/bin/python -c "
import html.parser, sys
class Verificador(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.pilha = []
    def handle_starttag(self, tag, attrs):
        if tag not in ('meta','link','img','input','br','hr'):
            self.pilha.append(tag)
    def handle_endtag(self, tag):
        if self.pilha and self.pilha[-1] == tag:
            self.pilha.pop()
        else:
            print('desbalanceado em', tag, self.pilha[-3:])
v = Verificador(); v.feed(open('frontend/index.html', encoding='utf-8').read())
print('tags abertas sobrando:', v.pilha)
"
```
Expected: `0 ocorrencias de Jinja`; os 9 `data-view` em português; os 9 `id` de seção; e `tags abertas sobrando: ['html']` ou lista vazia, sem nenhuma linha `desbalanceado`.

- [ ] **Step 11: Commit**

```bash
cd /home/stock-map
git add -A frontend
git commit -m "refactor: move frontend para estrutura estatica e remove jinja do html"
```

---

### Task 15: Frontend — reescrita do `app.js` para o novo contrato da API

**Files:**
- Modify: `frontend/js/app.js` (reescrita das partes listadas)

**Interfaces:**
- Consumes: as 26 rotas dos controllers das Tasks 8 a 13, e os `id` da Task 14.
- Produces: nada consumido por outra tarefa.

Três mudanças estruturais atravessam o arquivo inteiro: a base da API deixa de ser relativa fixa, o envelope `{ok, data}` some, e todos os nomes de campo viram português.

- [ ] **Step 1: Substituir o topo do arquivo — `state`, `titles` e a base da API**

Trocar o bloco `const state = {...}` e `const titles = {...}` (linhas 1 a 21 do arquivo atual) por:

```javascript
const API_URL =
  location.port === "5500" || location.protocol === "file:"
    ? "http://127.0.0.1:5000"
    : "";

const state = {
  fornecedores: [],
  lojistas: [],
  produtos: [],
  pedidos: [],
  alertas: [],
  relatorio: null,
  rotas: [],
  movimentacoes: [],
  itensPedido: [],
  filtrosPedidos: {},
  filtrosMovimentacoes: {},
  periodoRelatorio: {},
};

const titles = {
  painel: "Painel",
  fornecedores: "Fornecedores",
  lojistas: "Lojistas",
  produtos: "Produtos",
  pedidos: "Pedidos",
  alertas: "Alertas",
  relatorios: "Relatorios",
  rotas: "Rotas",
  movimentacoes: "Movimentacoes",
};
```

- [ ] **Step 2: Substituir o helper `api()`**

A função atual (linha 46) exige `body.ok` e devolve `body.data`. Substituir inteira por:

```javascript
async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const corpo = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(corpo.erro || "Falha na requisicao.");
  }

  return corpo;
}
```

- [ ] **Step 3: Substituir `statusLabel` e `stockLabel` pelos rótulos em português**

```javascript
function statusLabel(status) {
  const rotulos = {
    pendente: "Pendente",
    confirmado: "Confirmado",
    despachado: "Despachado",
    entregue: "Entregue",
    cancelado: "Cancelado",
  };
  return rotulos[status] || status;
}

function stockLabel(status) {
  const rotulos = {
    disponivel: "Disponivel",
    baixo: "Estoque baixo",
    indisponivel: "Indisponivel",
  };
  return rotulos[status] || status;
}
```

- [ ] **Step 4: Substituir `loadAll` pelas rotas e chaves novas**

```javascript
async function loadAll(silent = false) {
  try {
    const parametrosPedidos = new URLSearchParams(state.filtrosPedidos).toString();
    const parametrosMovimentacoes = new URLSearchParams(
      state.filtrosMovimentacoes
    ).toString();
    const parametrosRelatorio = new URLSearchParams(state.periodoRelatorio).toString();

    const [
      fornecedores,
      lojistas,
      produtos,
      pedidos,
      alertas,
      relatorio,
      rotas,
      movimentacoes,
    ] = await Promise.all([
      api("/fornecedores"),
      api("/lojistas"),
      api("/produtos"),
      api(`/pedidos${parametrosPedidos ? `?${parametrosPedidos}` : ""}`),
      api("/alertas"),
      api(`/relatorios${parametrosRelatorio ? `?${parametrosRelatorio}` : ""}`),
      api("/rotas"),
      api(`/movimentacoes${parametrosMovimentacoes ? `?${parametrosMovimentacoes}` : ""}`),
    ]);

    state.fornecedores = fornecedores;
    state.lojistas = lojistas;
    state.produtos = produtos;
    state.pedidos = pedidos;
    state.alertas = alertas;
    state.relatorio = relatorio;
    state.rotas = rotas;
    state.movimentacoes = movimentacoes;

    renderAll();
    if (!silent) {
      showToast("Dados atualizados.");
    }
  } catch (erro) {
    showToast(erro.message);
  }
}
```

- [ ] **Step 5: Renomear os campos em todas as funções de render**

Aplicar o mapa abaixo em `renderMetrics`, `renderAlerts`, `renderEntities`, `renderSelects`, `filteredProducts`, `renderProducts`, `renderOrderProductOptions`, `renderOrderDraft`, `renderOrders`, os quatro `render*Chart`, `renderBars`, `renderReports` e `renderRoutes`:

| Campo antigo | Campo novo |
|---|---|
| `state.suppliers` | `state.fornecedores` |
| `state.retailers` | `state.lojistas` |
| `state.products` | `state.produtos` |
| `state.orders` | `state.pedidos` |
| `state.alerts` | `state.alertas` |
| `state.routes` | `state.rotas` |
| `state.orderItems` | `state.itensPedido` |
| `state.reports.summary` | `state.relatorio.resumo` |
| `state.reports.top_products` | `state.relatorio.top_produtos` |
| `state.reports.supplier_performance` | `state.relatorio.desempenho_fornecedores` |
| `.name` | `.nome` |
| `.contact_name` | `.nome_contato` |
| `.phone` | `.telefone` |
| `.address` | `.endereco` |
| `.city` | `.cidade` |
| `.state` (do registro) | `.estado` |
| `.supplier_name` | `.fornecedor_nome` |
| `.retailer_name` | `.lojista_nome` |
| `.product_name` | `.produto_nome` |
| `.unit_price` | `.preco_unitario` |
| `.quantity` | `.quantidade` |
| `.min_stock` | `.estoque_minimo` |
| `.lead_time_days` | `.prazo_entrega_dias` |
| `.stock_status` | `.status_estoque` |
| `.total_amount` | `.valor_total` |
| `.item_count` | `.total_itens` |
| `.created_at` | `.criado_em` |
| `.demand` | `.demanda` |
| `.orders_count` | `.total_pedidos` |
| `.severity` | `.severidade` |
| `.stops` | `.paradas` |
| `.stop_count` | `.total_paradas` |
| `.stop_order` | `.ordem_parada` |
| `.distance_from_previous_km` | `.distancia_anterior_km` |
| `.total_distance_km` | `.distancia_total_km` |
| `.route_date` | `.data_rota` |

E as chaves do resumo, dentro de `renderMetrics`: `suppliers` → `fornecedores`, `retailers` → `lojistas`, `products` → `produtos`, `stock_units` → `unidades_estoque`, `unavailable_products` → `produtos_indisponiveis`, `low_stock_products` → `produtos_estoque_baixo`, `open_orders` → `pedidos_abertos`, `orders_30_days` → `pedidos_periodo`, `revenue_30_days` → `faturamento_periodo`.

Os valores de status também mudam: `pending`/`confirmed`/`dispatched`/`delivered`/`cancelled` viram `pendente`/`confirmado`/`despachado`/`entregue`/`cancelado`, e `available`/`low`/`unavailable` viram `disponivel`/`baixo`/`indisponivel`. Isso afeta `renderOrderStatusChart`, `renderStockStatusChart` e os `<select>` de status gerados em `renderOrders`.

E os seletores renomeados na Task 14 — `qs("#supplier-list")` vira `qs("#lista-fornecedores")` e assim por diante, seguindo a tabela do Step 5 daquela tarefa.

- [ ] **Step 6: Substituir os endpoints em `bindForms`, `bindOrderBuilder` e `bindTableActions`**

| Chamada antiga | Chamada nova |
|---|---|
| `api("/api/suppliers", ...)` | `api("/fornecedores", ...)` |
| `api("/api/retailers", ...)` | `api("/lojistas", ...)` |
| `api("/api/products", ...)` | `api("/produtos", ...)` |
| `api("/api/orders", ...)` | `api("/pedidos", ...)` |
| `api("/api/routes", ...)` | `api("/rotas", ...)` |
| `api(\`/api/products/${id}/stock\`, ...)` | `api(\`/produtos/${id}/estoque\`, ...)` |
| `api(\`/api/orders/${id}/status\`, ...)` | `api(\`/pedidos/${id}/status\`, ...)` |

No corpo enviado ao ajustar estoque, `{ quantity, reason }` vira `{ quantidade, motivo }`. No pedido, `items` vira `itens` e cada item passa a ser `{ produto_id, quantidade }`.

Como a API não devolve mais `message`, o `submitJson` deve mostrar um texto próprio:

```javascript
async function submitJson(form, path, mensagemSucesso, afterSubmit) {
  try {
    await api(path, {
      method: "POST",
      body: JSON.stringify(formData(form)),
    });
    form.reset();
    showToast(mensagemSucesso);
    if (afterSubmit) {
      afterSubmit();
    }
    await loadAll(true);
  } catch (erro) {
    showToast(erro.message);
  }
}
```

Cada chamada em `bindForms` passa a informar a mensagem: `"Fornecedor cadastrado."`, `"Lojista cadastrado."`, `"Produto cadastrado."`, `"Rota gerada."`.

- [ ] **Step 7: Acrescentar a renderização das movimentações**

```javascript
function renderMovimentacoes() {
  const corpo = qs("#tabela-movimentacoes");
  qs("#contador-movimentacoes").textContent = state.movimentacoes.length;

  if (!state.movimentacoes.length) {
    corpo.innerHTML = empty("Nenhuma movimentacao no periodo.");
    return;
  }

  corpo.innerHTML = state.movimentacoes
    .map((movimentacao) => {
      const variacao = movimentacao.variacao_quantidade;
      const sinal = variacao > 0 ? `+${variacao}` : `${variacao}`;
      return `
        <tr>
          <td>${new Date(movimentacao.criado_em).toLocaleString("pt-BR")}</td>
          <td>${movimentacao.produto_nome} <small>${movimentacao.sku}</small></td>
          <td>${movimentacao.fornecedor_nome}</td>
          <td>${movimentacao.tipo_movimentacao}</td>
          <td>${sinal}</td>
          <td>${movimentacao.motivo || "-"}</td>
        </tr>
      `;
    })
    .join("");
}
```

Chamar `renderMovimentacoes()` dentro de `renderAll()`.

- [ ] **Step 8: Acrescentar o bind dos filtros novos**

```javascript
function bindFiltrosPedidos() {
  const form = qs("#filtros-pedidos");

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const dados = formData(form);
    state.filtrosPedidos = Object.fromEntries(
      Object.entries(dados).filter(([, valor]) => valor !== "")
    );
    await loadAll(true);
  });

  qs("#limpar-filtros-pedidos").addEventListener("click", async () => {
    form.reset();
    state.filtrosPedidos = {};
    await loadAll(true);
  });
}

function bindFiltrosMovimentacoes() {
  const form = qs("#filtros-movimentacoes");

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const dados = formData(form);
    state.filtrosMovimentacoes = Object.fromEntries(
      Object.entries(dados).filter(([, valor]) => valor !== "")
    );
    await loadAll(true);
  });

  qs("#limpar-filtros-movimentacoes").addEventListener("click", async () => {
    form.reset();
    state.filtrosMovimentacoes = {};
    await loadAll(true);
  });
}

function bindFiltroRelatorio() {
  const form = qs("#filtros-relatorio");

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const dados = formData(form);
    state.periodoRelatorio = Object.fromEntries(
      Object.entries(dados).filter(([, valor]) => valor !== "")
    );
    await loadAll(true);
  });
}
```

Chamar as três na inicialização, junto de `bindNavigation()` e `bindForms()`.

- [ ] **Step 9: Popular os selects dos filtros e mostrar o período aplicado**

Dentro de `renderSelects()`, acrescentar:

```javascript
  setSelectOptions(qs("#filtro-pedido-lojista"), state.lojistas, "Todos os lojistas");
  setSelectOptions(qs("#filtro-movimentacao-produto"), state.produtos, "Todos os produtos");
  setSelectOptions(
    qs("#filtro-movimentacao-fornecedor"),
    state.fornecedores,
    "Todos os fornecedores"
  );
```

E dentro de `renderReports()`, no início:

```javascript
  const periodo = state.relatorio?.periodo;
  if (periodo) {
    qs("#periodo-relatorio").textContent =
      `${periodo.data_inicio} ate ${periodo.data_fim}`;
  }
```

`setSelectOptions` já usa `item.nome` depois do Step 5, então os três selects saem prontos.

- [ ] **Step 10: Verificar o front no navegador**

Subir a API na 5000 e o front na 5500:
```bash
cd /home/stock-map/backend && \
  /home/stock-map/.venv/bin/python -m flask --app app_novo run --port 5000 &
cd /home/stock-map/frontend && /home/stock-map/.venv/bin/python -m http.server 5500 &
```

Abrir `http://127.0.0.1:5500` e percorrer as nove telas. Conferir:
- Painel carrega as métricas e os quatro gráficos sem erro no console.
- Fornecedores, Lojistas e Produtos listam os registros do seed.
- Cadastrar um fornecedor pelo formulário mostra o toast `Fornecedor cadastrado.` e ele aparece na lista.
- Em Pedidos, filtrar por status `confirmado` reduz a lista; `Limpar` traz tudo de volta.
- Em Relatórios, aplicar `2020-01-01` a `2030-12-31` muda o texto do pill de período.
- Movimentações lista o histórico e o filtro por produto funciona.
- Rotas mostra a rota criada na Task 13 com as duas paradas.
- Console do navegador sem erro de CORS e sem `undefined` na tela.

- [ ] **Step 11: Commit**

```bash
cd /home/stock-map
git add frontend/js/app.js
git commit -m "refactor: adapta o frontend ao novo contrato da API em portugues"
```

---

### Task 16: Remoção do código antigo e promoção do `app.py`

**Files:**
- Delete: `backend/database/connection.py`, `backend/database/seed.sql`
- Delete: `backend/models/{supplier,retailer,product,order,stock_movement,route}_model.py`
- Delete: `backend/repositories/{product,order,alert,report,route}_repository.py`
- Delete: `backend/services/{supplier,retailer,product,order,alert,report,route}_service.py`, `backend/services/validation.py`
- Delete: `backend/controllers/{supplier,retailer,product,order,alert,report,route,web}_controller.py`, `backend/controllers/helpers.py`
- Modify: `backend/controllers/__init__.py` (esvaziar)
- Rename: `backend/app_novo.py` → `backend/app.py`

**Interfaces:**
- Consumes: tudo das Tasks 1 a 13.
- Produces: `backend/app.py` com `app = create_app()` no nível do módulo, mantendo `app:app` funcionando para o gunicorn.

O serviço em produção ainda está rodando o processo antigo já carregado em memória; ele só passa a usar o código novo no restart da Task 19.

- [ ] **Step 1: Remover os arquivos antigos**

```bash
cd /home/stock-map/backend
git rm database/connection.py database/seed.sql
git rm models/supplier_model.py models/retailer_model.py models/product_model.py \
       models/order_model.py models/stock_movement_model.py models/route_model.py
git rm repositories/product_repository.py repositories/order_repository.py \
       repositories/alert_repository.py repositories/report_repository.py \
       repositories/route_repository.py
git rm services/supplier_service.py services/retailer_service.py services/product_service.py \
       services/order_service.py services/alert_service.py services/report_service.py \
       services/route_service.py services/validation.py
git rm controllers/supplier_controller.py controllers/retailer_controller.py \
       controllers/product_controller.py controllers/order_controller.py \
       controllers/alert_controller.py controllers/report_controller.py \
       controllers/route_controller.py controllers/web_controller.py controllers/helpers.py
```

**Atenção:** `controllers/alert_controller.py`, `controllers/product_controller.py`, `controllers/order_controller.py`, `controllers/report_controller.py` e `controllers/route_controller.py` são os arquivos **antigos**, em inglês. Os novos criados nas Tasks 8 a 13 chamam-se `alerta_controller.py`, `produto_controller.py`, `pedido_controller.py`, `relatorio_controller.py` e `rota_controller.py`. Conferir antes de rodar que os arquivos em português continuam presentes.

- [ ] **Step 2: Esvaziar `backend/controllers/__init__.py`**

O arquivo passa a ser vazio (zero bytes), como na referência:
```bash
cd /home/stock-map/backend && : > controllers/__init__.py
```

- [ ] **Step 3: Promover `app_novo.py` a `app.py`**

```bash
cd /home/stock-map/backend
git rm app.py
git mv app_novo.py app.py
```

- [ ] **Step 4: Limpar os `__pycache__` órfãos**

```bash
find /home/stock-map/backend -name "__pycache__" -type d -exec rm -rf {} +
```

- [ ] **Step 5: Verificar que sobrou só o código novo**

Run:
```bash
cd /home/stock-map/backend
ls models repositories services controllers
grep -rn "mysql.connector\|from database.connection\|render_template\|url_for" \
  --include="*.py" . || echo "nenhuma referencia ao codigo antigo"
grep -rln "CALL sp_" --include="*.py" .
```
Expected:
- `models/` com `database.py` e os 6 arquivos em português
- `repositories/` com `conversor.py` e os 6 em português
- `services/` com os 25 arquivos
- `controllers/` com os 8 em português e o `__init__.py` vazio
- `nenhuma referencia ao codigo antigo`
- os `CALL sp_` aparecem **somente** em arquivos dentro de `./repositories/`

- [ ] **Step 6: Verificar que a API sobe com o nome definitivo**

Run:
```bash
cd /home/stock-map/backend && \
/home/stock-map/.venv/bin/python -m flask --app app run --port 5001 &
sleep 3
curl -s http://127.0.0.1:5001/ | head -c 200; echo
curl -s -o /dev/null -w "fornecedores %{http_code}\n" http://127.0.0.1:5001/fornecedores
curl -s -o /dev/null -w "produtos %{http_code}\n" http://127.0.0.1:5001/produtos
curl -s -o /dev/null -w "pedidos %{http_code}\n" http://127.0.0.1:5001/pedidos
curl -s -o /dev/null -w "alertas %{http_code}\n" http://127.0.0.1:5001/alertas
curl -s -o /dev/null -w "relatorios %{http_code}\n" http://127.0.0.1:5001/relatorios
curl -s -o /dev/null -w "rotas %{http_code}\n" http://127.0.0.1:5001/rotas
curl -s -o /dev/null -w "movimentacoes %{http_code}\n" http://127.0.0.1:5001/movimentacoes
curl -s -o /dev/null -w "lojistas %{http_code}\n" http://127.0.0.1:5001/lojistas
```
Expected: a rota `/` devolve o JSON informativo e as 8 listagens respondem `200`.

- [ ] **Step 7: Confirmar que produção ainda não caiu**

Run: `curl -s -o /dev/null -w "%{http_code}\n" https://stockmap.easytechnl.com.br/api/health`
Expected: `200` — o processo antigo segue em memória.

- [ ] **Step 8: Commit**

```bash
cd /home/stock-map
git add -A backend
git commit -m "refactor: remove codigo antigo com sql cru e promove o novo app.py"
```

---

### Task 17: Script de smoke test

**Files:**
- Create: `backend/scripts/smoke_test.sh`

**Interfaces:**
- Consumes: a API da Task 16 rodando em `$BASE_URL` (padrão `http://127.0.0.1:5001`).
- Produces: nada consumido por outra tarefa. Saída legível e código de retorno diferente de zero em caso de falha.

- [ ] **Step 1: Criar `backend/scripts/smoke_test.sh`**

```bash
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

# Ciclo de escrita: cria fornecedor, rejeita duplicata, remove.
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
```

- [ ] **Step 2: Tornar o script executável**

```bash
chmod +x /home/stock-map/backend/scripts/smoke_test.sh
```

- [ ] **Step 3: Rodar o smoke test**

Com a API da Task 16 rodando na 5001:
```bash
BASE_URL=http://127.0.0.1:5001 bash /home/stock-map/backend/scripts/smoke_test.sh
```
Expected: todas as linhas começando com `ok`, e a última linha `Todos os testes passaram.` com código de retorno `0`.

Se alguma linha vier `FALHA`, corrigir o controller ou service correspondente antes de seguir — não prosseguir para o cutover com o smoke test vermelho.

- [ ] **Step 4: Commit**

```bash
cd /home/stock-map
git add backend/scripts/smoke_test.sh
git commit -m "chore: adiciona script de smoke test das rotas da API"
```

---

### Task 18: README

**Files:**
- Modify: `README.md` (reescrita completa)

**Interfaces:**
- Consumes: tudo implementado nas Tasks 1 a 17.
- Produces: a documentação exigida pela atividade — funcionalidades, procedures, rotas, models, repositories e instruções de execução.

- [ ] **Step 1: Reescrever o `README.md` da raiz**

````markdown
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
````

- [ ] **Step 2: Conferir que o README bate com o código**

Run:
```bash
cd /home/stock-map
grep -c "sp_" README.md
grep -o "sp_[a-z_]*" backend/database/create_database.sql | sort -u | wc -l
ls backend/services/*.py | wc -l
ls backend/controllers/*_controller.py | wc -l
```
Expected: as 12 procedures citadas no README correspondem às 12 do script; `25` services; `8` controllers.

- [ ] **Step 3: Commit**

```bash
cd /home/stock-map
git add README.md
git commit -m "docs: reescreve README com arquitetura, procedures e rotas"
```

---

### Task 19: Cutover em produção

**Files:**
- Modify: `/etc/nginx/sites-enabled/stockmap.easytechnl.com.br`
- Modify: `backend/.env` (remover as variáveis `DB_*`)

**Interfaces:**
- Consumes: o código das Tasks 1 a 18.
- Produces: `https://stockmap.easytechnl.com.br` servindo o frontend novo com a API nova.

Esta é a única tarefa que causa indisponibilidade. Executar com o smoke test da Task 17 verde.

> **Aviso:** o Step 6 remove permanentemente as 8 tabelas antigas em inglês e os dados que elas contêm. Fazer o dump do Step 1 antes, e só executar o drop depois que os Steps 2 a 5 confirmarem que o site novo está no ar.

- [ ] **Step 1: Fazer dump do banco antes de qualquer alteração**

```bash
cd /home/stock-map/backend && set -a && . ./.env && set +a && \
mysqldump -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" \
  > /root/backup-stock-map-$(date +%Y%m%d-%H%M).sql && \
ls -lh /root/backup-stock-map-*.sql
```
Expected: arquivo criado, tamanho maior que zero.

- [ ] **Step 2: Conferir que o nginx consegue ler a pasta do frontend**

O nginx roda como `www-data` e precisa de permissão de travessia até `/home/stock-map/frontend`.

Run:
```bash
sudo -u www-data test -r /home/stock-map/frontend/index.html && echo "leitura ok" || echo "sem permissao"
```
Expected: `leitura ok`. Se vier `sem permissao`:
```bash
chmod o+x /home/stock-map /home/stock-map/frontend
chmod -R o+r /home/stock-map/frontend
```
e repetir a verificação.

- [ ] **Step 3: Reescrever o server block do nginx**

Substituir o conteúdo de `/etc/nginx/sites-enabled/stockmap.easytechnl.com.br` por:

```nginx
server {
    server_name stockmap.easytechnl.com.br;

    root /home/stock-map/frontend;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~ ^/(fornecedores|lojistas|produtos|pedidos|alertas|relatorios|rotas|movimentacoes)(/|$) {
        proxy_pass http://127.0.0.1:5000;

        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/stockmap.easytechnl.com.br/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/stockmap.easytechnl.com.br/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    if ($host = stockmap.easytechnl.com.br) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name stockmap.easytechnl.com.br;
    return 404; # managed by Certbot
}
```

- [ ] **Step 4: Reiniciar o serviço e recarregar o nginx**

```bash
sudo systemctl restart stockmap.service
sleep 3
sudo systemctl is-active stockmap.service
sudo nginx -t && sudo systemctl reload nginx
```
Expected: `active`, e `nginx: configuration file /etc/nginx/nginx.conf test is successful`.

Se o serviço não subir:
```bash
sudo journalctl -u stockmap.service -n 40 --no-pager
```

- [ ] **Step 5: Validar o domínio publicado**

```bash
curl -s -o /dev/null -w "index %{http_code}\n" https://stockmap.easytechnl.com.br/
curl -s -o /dev/null -w "css %{http_code}\n" https://stockmap.easytechnl.com.br/css/style.css
curl -s -o /dev/null -w "js %{http_code}\n" https://stockmap.easytechnl.com.br/js/app.js
curl -s https://stockmap.easytechnl.com.br/fornecedores | head -c 200; echo
BASE_URL=https://stockmap.easytechnl.com.br bash /home/stock-map/backend/scripts/smoke_test.sh
```
Expected: `200` nos três estáticos, o JSON dos fornecedores, e o smoke test com `Todos os testes passaram.`

Abrir o site no navegador e percorrer as nove telas, conferindo que não há erro no console.

- [ ] **Step 6: Derrubar as tabelas antigas**

Só executar com os Steps 4 e 5 confirmados. A ordem respeita as chaves estrangeiras.

```bash
cd /home/stock-map/backend && set -a && . ./.env && set +a && \
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "
DROP TABLE IF EXISTS route_stops;
DROP TABLE IF EXISTS delivery_routes;
DROP TABLE IF EXISTS stock_movements;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS retailers;
DROP TABLE IF EXISTS suppliers;
SHOW TABLES;"
```
Expected: restam exatamente as 8 tabelas em português.

- [ ] **Step 7: Remover as variáveis `DB_*` do `.env`**

Apagar as linhas `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` e `DB_NAME`, deixando apenas `DATABASE_URL`, `SECRET_KEY` e `FLASK_DEBUG`. Nada mais lê as variáveis antigas.

```bash
sudo systemctl restart stockmap.service
sleep 3
BASE_URL=https://stockmap.easytechnl.com.br bash /home/stock-map/backend/scripts/smoke_test.sh
```
Expected: `Todos os testes passaram.`

- [ ] **Step 8: Desinstalar o driver antigo**

```bash
/home/stock-map/.venv/bin/pip uninstall -y mysql-connector-python
sudo systemctl restart stockmap.service
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" https://stockmap.easytechnl.com.br/fornecedores
```
Expected: `200`.

- [ ] **Step 9: Commit e push**

```bash
cd /home/stock-map
git status --porcelain
git push origin main
```
Expected: working tree limpo (o `.env` está no `.gitignore`) e o push concluído.

---

## Self-Review

**Cobertura do spec**

| Requisito do spec | Tarefa |
|---|---|
| Models como classes `db.Model` com CRUD | 2, 3, 4, 5 |
| `models/database.py` com `db` compartilhado | 1 |
| 8 tabelas renomeadas com colunas em português | 2, 3, 4, 5, 6 |
| 12 procedures em `create_database.sql` | 6 |
| Seed em português | 6 |
| 6 repositories chamando `CALL sp_...` | 7 |
| 25 services, um caso de uso por arquivo | 8, 9, 10, 11, 12, 13 |
| 8 controllers sem `url_prefix`, sem envelope | 8, 9, 10, 11, 12, 13 |
| Transações em pedido, status e rota | 11, 13 |
| Regras de negócio preservadas | 10, 11, 13 |
| `app.py` com CORS, `create_all`, rota informativa | 1, 16 |
| `.env` com `DATABASE_URL`, requirements novos | 1 |
| Frontend sem Jinja, estrutura estática | 14 |
| `API_URL` resolvido em runtime, sem envelope | 15 |
| Filtros de pedidos, período de relatório, tela de movimentações | 14, 15 |
| Remoção do código antigo | 16 |
| Verificação por smoke test | 17 |
| README com funcionalidades, procedures, rotas, models, repositories | 18 |
| nginx servindo estático e fazendo proxy | 19 |
| Convivência das tabelas até o cutover | 1, 5, 16, 19 |

Nenhum requisito do spec ficou sem tarefa.

**Consistência de nomes**

- `MovimentacaoRepository` é o nome da classe em `movimentacao_repository.py`, usado igual na Task 7 (definição), Task 12 (consumo) e Task 18 (README).
- `Produto.buscar_para_atualizacao` é definido na Task 3 e consumido nas Tasks 10, 11 e 13 com a mesma assinatura.
- `Pedido.STATUS_VALIDOS` é definido na Task 4 e consumido nas Tasks 11 e 15.
- Os `id` do HTML renomeados na Task 14 são exatamente os consultados na Task 15.
- Os nomes de procedure são idênticos entre a Task 6 (criação), a Task 7 (chamada) e a Task 18 (documentação).
- `executar()` é o nome do método público em todos os 25 services.

**Pontos de atenção para quem executar**

1. Na Task 16, cinco controllers antigos têm nome parecido com os novos (`alert_controller.py` vs `alerta_controller.py`). Conferir a lista antes de rodar o `git rm`.
2. A Task 19 é a única destrutiva. O dump do Step 1 é obrigatório.
3. Os números esperados nas verificações das Tasks 10 a 13 dependem dos passos anteriores terem rodado na ordem. Executando fora de ordem, recriar o banco com `create_database.sql` antes.
