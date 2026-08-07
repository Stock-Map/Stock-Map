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
