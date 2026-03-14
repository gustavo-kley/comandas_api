from pydantic import BaseModel, ConfigDict
from typing import Optional

class ClienteCreate(BaseModel):
    nome: str
    cpf: str
    telefone: str

class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = None

class Cliente(BaseModel):
    """Schema para POST/PUT - id opcional para criação"""
    id_cliente: Optional[int] = None
    nome: str
    cpf: str
    telefone: str


class ClienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    cpf: str
    telefone: str