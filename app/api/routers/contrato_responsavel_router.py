# app/api/routers/contrato_responsavel_router.py
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from typing import Optional

from app.core.database import get_connection
from app.schemas.usuario_schema import Usuario
from app.api.dependencies import get_current_user
from app.api.permissions import admin_required

from app.repositories.contrato_responsavel_repo import ContratoResponsavelRepository
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.usuario_repo import UsuarioRepository

from app.services.contrato_responsavel_service import ContratoResponsavelService
from app.schemas.contrato_responsavel_schema import (
    ContratoResponsavelCreate, ContratoResponsavelUpdate,
    ContratoResponsavel, ContratoResponsavelList,
    RelatorioResponsaveisPaginated,
)

router = APIRouter(
    prefix="/contratos",
    tags=["Responsaveis do Contrato"],
)


def get_responsavel_service(
    conn: asyncpg.Connection = Depends(get_connection),
) -> ContratoResponsavelService:
    return ContratoResponsavelService(
        responsavel_repo=ContratoResponsavelRepository(conn),
        contrato_repo=ContratoRepository(conn),
        usuario_repo=UsuarioRepository(conn),
    )


# --- CRUD de responsáveis por contrato ---

@router.get(
    "/{contrato_id}/responsaveis",
    response_model=ContratoResponsavelList,
    summary="Listar responsáveis do contrato",
)
async def listar_responsaveis(
    contrato_id: int,
    tipo: Optional[str] = Query(None, description="Filtrar por tipo: fiscal, gestor, fiscal_substituto"),
    apenas_atuais: bool = Query(False, description="Mostrar apenas responsáveis atuais (sem data_fim)"),
    service: ContratoResponsavelService = Depends(get_responsavel_service),
    current_user: Usuario = Depends(get_current_user),
):
    return await service.listar_responsaveis(contrato_id, tipo=tipo, apenas_atuais=apenas_atuais)


@router.post(
    "/{contrato_id}/responsaveis",
    response_model=ContratoResponsavel,
    status_code=status.HTTP_201_CREATED,
    summary="Designar novo responsável",
)
async def designar_responsavel(
    contrato_id: int,
    dados: ContratoResponsavelCreate,
    service: ContratoResponsavelService = Depends(get_responsavel_service),
    admin_user: Usuario = Depends(admin_required),
):
    return await service.designar_responsavel(contrato_id, dados, admin_user)


@router.patch(
    "/{contrato_id}/responsaveis/{responsavel_id}",
    response_model=ContratoResponsavel,
    summary="Atualizar registro de responsável",
)
async def atualizar_responsavel(
    contrato_id: int,
    responsavel_id: int,
    dados: ContratoResponsavelUpdate,
    service: ContratoResponsavelService = Depends(get_responsavel_service),
    admin_user: Usuario = Depends(admin_required),
):
    return await service.atualizar_responsavel(contrato_id, responsavel_id, dados)


@router.delete(
    "/{contrato_id}/responsaveis/{responsavel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover registro de responsável",
)
async def remover_responsavel(
    contrato_id: int,
    responsavel_id: int,
    service: ContratoResponsavelService = Depends(get_responsavel_service),
    admin_user: Usuario = Depends(admin_required),
):
    await service.remover_responsavel(contrato_id, responsavel_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Relatório de contratos com seus responsáveis ---

@router.get(
    "/relatorio/responsaveis",
    response_model=RelatorioResponsaveisPaginated,
    summary="Relatório de contratos com fiscais e gestores atuais",
)
async def relatorio_responsaveis(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    nr_contrato: Optional[str] = Query(None, description="Filtrar por número do contrato"),
    objeto: Optional[str] = Query(None, description="Filtrar por objeto"),
    status_id: Optional[int] = Query(None, description="Filtrar por status"),
    gestor_nome: Optional[str] = Query(None, description="Filtrar por nome do gestor"),
    fiscal_nome: Optional[str] = Query(None, description="Filtrar por nome do fiscal"),
    service: ContratoResponsavelService = Depends(get_responsavel_service),
    current_user: Usuario = Depends(get_current_user),
):
    filters = {
        k: v for k, v in {
            'nr_contrato': nr_contrato,
            'objeto': objeto,
            'status_id': status_id,
            'gestor_nome': gestor_nome,
            'fiscal_nome': fiscal_nome,
        }.items() if v is not None
    }
    return await service.relatorio_responsaveis(page, per_page, filters or None)
