from pydantic import BaseModel, ConfigDict
from typing import Optional

class FuncionarioCreate(BaseModel):
    nome: str
    matricula: str
    cpf: str
    telefone: str
    grupo: int
    senha: str

class FuncionarioUpdate(BaseModel):
    nome: Optional[str] = None
    matricula: Optional[str] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    grupo: Optional[int] = None
    senha: Optional[str] = None

class Funcionario(BaseModel):
    """Schema para POST/PUT - id opcional para criação"""
    id_funcionario: Optional[int] = None
    nome: str
    matricula: str
    cpf: str
    telefone: str
    grupo: int
    senha: str


class FuncionarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    matricula: str
    cpf: str
    telefone: str
    grupo: int