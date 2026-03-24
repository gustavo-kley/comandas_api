# Gustavo Kley
from pydantic import BaseModel

class Produto(BaseModel):
    id_produto: int = None
    nome: str
    descricao: str
    preco: float
    quantidade: int
    categoria: str
    foto: bytes
    disponivel: bool
    estoque: int
    fornecedor: str