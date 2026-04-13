from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime


from domain.schemas.AuditoriaSchema import AuditoriaResponse
from domain.schemas.AuthSchema import FuncionarioAuth
from infra.orm.AuditoriaModel import AuditoriaDB
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.database import get_db
from infra.database import get_async_db
from infra.dependencies import require_group, get_current_active_user
from infra.rate_limit import limiter, get_rate_limit

router = APIRouter()

# Lista todas as comandas com paginação e filtro opcional por status {0 - aberta, 1 - fechada, 2 - cancelada}
@router.get("/auditoria/", response_model=List[AuditoriaResponse], tags=["Auditoria"], summary="Listar todas as auditorias - opção de filtro e paginação - protegida por JWT")
@limiter.limit("moderate")
async def get_auditorias(
    request: Request,
    skip: int = Query(0, ge=0, description="Número de registros para pular"),  # ge = maior ou igual
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),  # ge = maior ou igual, le = menor ou igual
    id: Optional[int] = Query(None, description="Filtrar por ID"),
    funcionario_id: Optional[int] = Query(None, description="Filtrar por funcionário"),
    acao: Optional[str] = Query(None, description="Filtrar por ação"),
    recurso: Optional[str] = Query(None, description="Filtrar por recurso"),
    recurso_id: Optional[int] = Query(None, description="Filtrar por ID do recurso"),
    ip_address: Optional[str] = Query(None, description="Filtrar por IP"),
    user_agent: Optional[str] = Query(None, description="Filtrar por user agent"),
    data_hora: Optional[datetime] = Query(None, description="Filtrar por data e hora"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    data_inicio: Optional[datetime] = Query(None, description="Filtrar por data inicial"),
    data_fim: Optional[datetime] = Query(None, description="Filtrar por data final"),
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        # busca a comanda, funcionário e cliente com joins
        query = (
            select(AuditoriaDB, FuncionarioDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == AuditoriaDB.funcionario_id)
        )

        # Aplicar filtros
        conditions = []

        if id is not None:
            conditions.append(  AuditoriaDB.id == id)

        if acao is not None:
            conditions.append(AuditoriaDB.acao == acao)

        if recurso is not None:
            conditions.append(AuditoriaDB.recurso == recurso)

        if recurso_id is not None:
            conditions.append(AuditoriaDB.recurso_id == recurso_id)

        if ip_address is not None:
            conditions.append(AuditoriaDB.ip_address == ip_address)

        if user_agent is not None:
            conditions.append(AuditoriaDB.user_agent == user_agent)

        if data_hora is not None:
            conditions.append(AuditoriaDB.data_hora == data_hora)

        if funcionario_id is not None:
            conditions.append(AuditoriaDB.funcionario_id == funcionario_id)

        if cliente_id is not None:
            conditions.append(AuditoriaDB.cliente_id == cliente_id)

        if data_inicio is not None:
            conditions.append(AuditoriaDB.data_hora >= data_inicio)

        if data_fim is not None:
            conditions.append(AuditoriaDB.data_hora <= data_fim)

        if status is not None:
            conditions.append(ComandaDB.status == status)

        if funcionario_id is not None:
            conditions.append(ComandaDB.funcionario_id == funcionario_id)

        if cliente_id is not None:
            conditions.append(ComandaDB.cliente_id == cliente_id)

        if data_inicio is not None:
            conditions.append(ComandaDB.data_hora >= data_inicio)

        if data_fim is not None:
            conditions.append(ComandaDB.data_hora <= data_fim)

        # Aplicar condições à query
        if conditions:
            query = query.where(*conditions)

        # executar query com paginação
        result = await db.execute(query.offset(skip).limit(limit))
        results = result.all()

        # Construir lista de responses manualmente
        comandas_response = []

        for comanda, funcionario, cliente in results:
            comanda_response = ComandaResponse(
                id=comanda.id,
                comanda=comanda.comanda,
                data_hora=comanda.data_hora,
                status=comanda.status,
                cliente_id=comanda.cliente_id,
                funcionario_id=comanda.funcionario_id,
                funcionario=FuncionarioResponse(
                    id=funcionario.id,
                    nome=funcionario.nome,
                    matricula=funcionario.matricula,
                    cpf=funcionario.cpf,
                    telefone=funcionario.telefone,
                    grupo=funcionario.grupo
                ) if funcionario else None,
                cliente=ClienteResponse(
                    id=cliente.id,
                    nome=cliente.nome,
                    cpf=cliente.cpf,
                    telefone=cliente.telefone
                ) if cliente else None
            )
            comandas_response.append(comanda_response)

        return comandas_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar comandas: {str(e)}"
        )



@router.get(
    "/auditoria/acoes",
    tags=["Auditoria"],
    summary="Listar tipos de ações disponíveis para filtro - protegida por JWT e grupo 1"
)
@limiter.limit(get_rate_limit("light"))
async def listar_acoes_disponiveis(
    request: Request,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """
    Lista os tipos de ações e recursos disponíveis para filtro.
    Retorna apenas ações e recursos que possuem registros de auditoria.
    """
    try:
        # Buscar ações e recursos distintos no banco de dados
        acoes_db = db.query(AuditoriaDB.acao).distinct().all()
        recursos_db = db.query(AuditoriaDB.recurso).distinct().all()

        # Montar response com dados reais do banco
        return {
            "acoes": [
                {"codigo": acao[0]}
                for acao in acoes_db
            ],
            "recursos": [
                {"codigo": recurso[0]}
                for recurso in recursos_db
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar ações e recursos: {str(e)}"
        )