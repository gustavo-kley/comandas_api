# Gustavo Kley
from fastapi import APIRouter
from domain.entities.Funcionario import Funcionario

router = APIRouter()

# Criar as rotas/endpoints: GET, POST, PUT, DELETE
@router.get("/funcionario/", tags=["Funcionário"], status_code=200)
def get_funcionario():
    return {"msg": "funcionario get todos executado"}


@router.get("/funcionario/{id}", tags=["Funcionário"], status_code=200)
def get_funcionario(id: int):
    return {"msg": "funcionario get um executado", "id": id}


@router.post("/funcionario/", tags=["Funcionário"], status_code=201)
def post_funcionario(funcionario: Funcionario):
    return funcionario


@router.put("/funcionario/{id}", tags=["Funcionário"], status_code=200)
def put_funcionario(id: int, funcionario: Funcionario):
    funcionario.id_funcionario = id
    return funcionario


@router.delete("/funcionario/{id}", tags=["Funcionário"], status_code=200)
def delete_funcionario(id: int):
    return {"msg": "funcionario delete executado", "id": id}