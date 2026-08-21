import os
from pathlib import Path
from dotenv import load_dotenv

# Define o caminho absoluto para o arquivo .env localizado na pasta atual do app.py
env_path = Path(__file__).resolve().parent / '.env'

from flask import Flask, jsonify
from flask_cors import CORS

from controllers.fornecedor_controller import fornecedor_controller
from controllers.lojista_controller import lojista_controller
from controllers.produto_controller import produto_controller
from controllers.pedido_controller import pedido_controller
from controllers.alerta_controller import alerta_controller
from controllers.relatorio_controller import relatorio_controller
from controllers.movimentacao_controller import movimentacao_controller
from controllers.rota_controller import rota_controller
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
    # Carrega explicitamente o arquivo .env da mesma pasta do script
    load_dotenv(dotenv_path=env_path, override=True)

    app = Flask(__name__)
    CORS(app)

    db_url = os.getenv("DATABASE_URL")

    # Diagnóstico caso a variável continue sem ser lida
    if not db_url:
        raise ValueError(
            f"DATABASE_URL não foi encontrada. Verifique se o arquivo .env existe em: {env_path}"
        )

    # Troque isto:
# app.config["SQLALCHEMY_DATABASE_URI"] = db_url

# Por isto (usando suas credenciais do MySQL):
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:31200272Miguel@127.0.0.1:3306/stock_map"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

    db.init_app(app)

    app.register_blueprint(fornecedor_controller)
    app.register_blueprint(lojista_controller)
    app.register_blueprint(produto_controller)
    app.register_blueprint(pedido_controller)
    app.register_blueprint(alerta_controller)
    app.register_blueprint(relatorio_controller)
    app.register_blueprint(movimentacao_controller)
    app.register_blueprint(rota_controller)

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