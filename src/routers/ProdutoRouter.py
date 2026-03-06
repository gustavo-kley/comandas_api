# Gustavo Kley
from fastapi import APIRouter
from domain.entities.Produto import Produto

router = APIRouter()

# Criar as rotas/endpoints: GET, POST, PUT, DELETE
@router.get("/produto/", tags=["Produto"], status_code=200)
def get_funcionario():
    return {"msg": "produto get todos executado"}


@router.get("/produto/{id}", tags=["Produto"], status_code=200)
def get_funcionario(id: int):
    return {"msg": "produto get um executado", "id": id}


@router.post("/produto/", tags=["Produto"], status_code=201)
def post_produto(produto: Produto):
    return produto


@router.put("/produto/{id}", tags=["Produto"], status_code=200)
def put_produto(id: int, produto: Produto):
    produto.id_produto = id
    return produto


@router.delete("/produto/{id}", tags=["Produto"], status_code=200)
def delete_produto(id: int):
    return {"msg": "produto delete executado", "id": id}