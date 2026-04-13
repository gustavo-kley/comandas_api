# Gustavo Kley
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from services.AuditoriaService import AuditoriaService
from infra.rate_limit import limiter, get_rate_limit
from slowapi.errors import RateLimitExceeded

from sqlalchemy.orm import Session
from typing import List, Optional

from domain.schemas.ProdutoSchema import (
    ProdutoCreate,
    ProdutoUpdate,
    ProdutoResponse,
)
from domain.schemas.AuthSchema import FuncionarioAuth

from infra.orm.ProdutoModel import ProdutoDB
from infra.database import get_db
from infra.dependencies import get_current_active_user, require_group

router = APIRouter()


@router.get("/produto/", response_model=List[ProdutoResponse], tags=["Produto"], dependencies=[Depends(get_current_active_user)], status_code=status.HTTP_200_OK,
 summary="Listar todos os produtos - protegida por JWT e grupo 1")
@limiter.limit(get_rate_limit("moderate"))
async def get_produto(
    request: Request,
    skip: int = Query(0, ge=0, description="Número de registros para pular"), # ge = maior ou igual
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"), # ge = maior ou igual, le = menor ou igual
    id: Optional[int] = Query(None, description="Filtrar por ID"),
    nome: Optional[str] = Query(None, description="Filtrar por nome"),
    descricao: Optional[str] = Query(None, description="Filtrar por descrição"),
    valor: Optional[float] = Query(ge = 0, le=1000, description="Filtrar por valor"), # ge = maior ou igual, le = menor ou igual
    db: Session = Depends(get_db)
):
    try:
        query = db.query(ProdutoDB)
        
        if id:
            query = query.filter(ProdutoDB.id == id)
        if nome:
            query = query.filter(ProdutoDB.nome.ilike(f"%{nome}%"))
        if descricao:
            query = query.filter(ProdutoDB.descricao.ilike(f"%{descricao}%"))
        if valor:
            query = query.filter(ProdutoDB.valor_unitario == valor)
        
        produtos = query.offset(skip).limit(limit).all()
        return produtos
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar produtos: {str(e)}",
        )


@router.get("/produto/{id}", response_model=ProdutoResponse, tags=["Produto"], status_code=status.HTTP_200_OK)
async def get_produto( request: Request, id: int, db: Session = Depends(get_db), current_user: FuncionarioAuth = Depends(get_current_active_user)):
    """Retorna um produto específico pelo ID"""
    try:
        produto = db.query(ProdutoDB).filter(ProdutoDB.id == id).first()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado",
            )

        return produto
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar produto: {str(e)}",
        )


@router.post("/produto/", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED, tags=["Produto"])
async def post_produto(request: Request, produto_data: ProdutoCreate, db: Session = Depends(get_db), current_user: FuncionarioAuth = Depends(require_group([1]))):
    """Cria um novo produto"""
    try:
        novo_produto = ProdutoDB(
            id=None,  # Será auto-incrementado
            nome=produto_data.nome,
            descricao=produto_data.descricao,
            foto=produto_data.foto,
            valor_unitario=produto_data.valor_unitario,
        )

        db.add(novo_produto)
        db.commit()
        db.refresh(novo_produto)
        
        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="PRODUTO",
            recurso_id=novo_produto.id,
            dados_antigos=None,
            dados_novos=novo_produto, # Objeto SQLAlchemy com dados novos
            request=request # Request completo para capturar IP e user agent
        )
        
        return novo_produto
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar produto: {str(e)}",
        )


@router.put("/produto/{id}", response_model=ProdutoResponse, tags=["Produto"], status_code=status.HTTP_200_OK)
async def put_produto(request: Request, id: int, produto_data: ProdutoUpdate, db: Session = Depends(get_db),current_user: FuncionarioAuth = Depends(require_group([1]))):
    """Atualiza um produto existente"""
    try:
        produto = db.query(ProdutoDB).filter(ProdutoDB.id == id).first()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado",
            )

        update_data = produto_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(produto, field, value)

        db.commit()
        db.refresh(produto)

        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="PRODUTO",
            recurso_id=produto.id,
            dados_antigos=produto, # Objeto SQLAlchemy com dados antigos
            dados_novos=produto, # Objeto SQLAlchemy com dados novos
            request=request # Request completo para capturar IP e user agent
        )

        return produto
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar produto: {str(e)}",
        )


@router.delete( "/produto/{id}",status_code=status.HTTP_204_NO_CONTENT, tags=["Produto"], summary="Remover produto")
async def delete_produto(request: Request, id: int, db: Session = Depends(get_db), current_user: FuncionarioAuth = Depends(require_group([1]))):
    """Remove um produto"""
    try:
        produto = db.query(ProdutoDB).filter(ProdutoDB.id == id).first()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado",
            )

        db.delete(produto)
        db.commit()

        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="PRODUTO",
            recurso_id=produto.id,
            dados_antigos=produto,
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
            detail=f"Erro ao deletar produto: {str(e)}",
        )