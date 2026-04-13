# Gustavo Kley
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from services.AuditoriaService import AuditoriaService
from infra.rate_limit import limiter, get_rate_limit
from sqlalchemy.orm import Session
from typing import List, Optional

# Domain Schemas
from domain.schemas.ClienteSchema import (
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse
)
from domain.schemas.AuthSchema import FuncionarioAuth

# Infra
from infra.orm.ClienteModel import ClienteDB
from infra.database import get_db
from infra.dependencies import get_current_active_user, require_group

router = APIRouter()


@router.get("/cliente/", response_model=List[ClienteResponse], tags=["Cliente"], dependencies=[Depends(get_current_active_user)], status_code=status.HTTP_200_OK,
 summary="Listar todos os clientes - protegida por JWT e grupo 1")
@limiter.limit(get_rate_limit("moderate"))
async def get_cliente(
    request: Request,
    skip: int = Query(0, ge=0, description="Número de registros para pular"), # ge = maior ou igual
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"), # ge = maior ou igual, le = menor ou igual
    id: Optional[int] = Query(None, description="Filtrar por ID"),
    nome: Optional[str] = Query(None, description="Filtrar por nome"),
    cpf: Optional[str] = Query(None, description="Filtrar por CPF"),
    telefone: Optional[str] = Query(None, description="Filtrar por telefone"),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(ClienteDB)

    # Aplicar filtros
        if id is not None:
            query = query.filter(ClienteDB.id == id)
        if nome is not None:
            query = query.filter(ClienteDB.nome.ilike(f"%{nome}%")) # ilike = case insensitive
        if cpf is not None:
            query = query.filter(ClienteDB.cpf == cpf)
        if telefone is not None:
            query = query.filter(ClienteDB.telefone.ilike(f"%{telefone}%"))
            
    # Aplicar paginação
        clientes = query.offset(skip).limit(limit).all()

        return clientes
    except RateLimitExceeded:
        # Propagar exceção original para o handler personalizado
        raise
    except Exception as e:
        # Apenas erros reais da aplicação (não rate limit)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao buscar clientes: {str(e)}")


@router.get(
    "/cliente/{id}",
    response_model=ClienteResponse,
    tags=["Cliente"],
    status_code=status.HTTP_200_OK
)
async def get_cliente_by_id(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    """Retorna um Cliente específico pelo ID"""
    try:
        cliente = db.query(ClienteDB).filter(ClienteDB.id == id).first()

        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        return cliente
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar Cliente: {str(e)}"
        )


@router.post("/cliente/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED, tags=["Cliente"])
async def post_cliente(
    request: Request,
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Cria um novo Cliente"""
    try:
        # Verifica se já existe Cliente com este CPF
        existing_cliente = (
            db.query(ClienteDB)
            .filter(ClienteDB.cpf == cliente_data.cpf)
            .first()
        )

        if existing_cliente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um Cliente com este CPF"
            )

        # Cria o novo Cliente
        novo_cliente = ClienteDB(
            id=None,  # Será auto-incrementado
            nome=cliente_data.nome,
            cpf=cliente_data.cpf,
            telefone=cliente_data.telefone
        )

        db.add(novo_cliente)
        db.commit()
        db.refresh(novo_cliente)

        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="CLIENTE",
            recurso_id=novo_cliente.id,
            dados_antigos=None,
            dados_novos=novo_cliente, # Objeto SQLAlchemy com dados novos
            request=request # Request completo para capturar IP e user agent
        )

        return novo_cliente

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar Cliente: {str(e)}"
        )


@router.put("/cliente/{id}", response_model=ClienteResponse, tags=["Cliente"], status_code=status.HTTP_200_OK)
async def put_cliente(
    request: Request,
    id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Atualiza um Cliente existente"""
    try:
        cliente = db.query(ClienteDB).filter(ClienteDB.id == id).first()

        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        # Verifica se está tentando atualizar para um CPF que já existe
        if cliente_data.cpf and cliente_data.cpf != cliente.cpf:
            existing_cliente = (
                db.query(ClienteDB)
                .filter(ClienteDB.cpf == cliente_data.cpf)
                .first()
            )
            if existing_cliente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Já existe um Cliente com este CPF"
                )

        # Atualiza apenas os campos fornecidos
        update_data = cliente_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(cliente, field, value)

        db.commit()
        db.refresh(cliente)

        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="CLIENTE",
            recurso_id=cliente.id,
            dados_antigos=cliente, # Objeto SQLAlchemy com dados antigos
            dados_novos=cliente, # Objeto SQLAlchemy com dados novos
            request=request # Request completo para capturar IP e user agent
        )

        return cliente

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar Cliente: {str(e)}"
        )


@router.delete(
    "/cliente/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Cliente"],
    summary="Remover Cliente"
)
async def delete_cliente(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Remove um Cliente"""
    try:
        cliente = db.query(ClienteDB).filter(ClienteDB.id == id).first()

        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        db.delete(cliente)
        db.commit()

        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="CLIENTE",
            recurso_id=cliente.id,
            dados_antigos=cliente,
            dados_novos=None,
            request=request
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar Cliente: {str(e)}"
        )