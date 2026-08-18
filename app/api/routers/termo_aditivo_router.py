# app/api/routers/termo_aditivo_router.py
import asyncpg
from fastapi import APIRouter, Depends, status, UploadFile, File
from typing import List

from app.core.database import get_connection
from app.api.dependencies import get_current_user
from app.api.permissions import admin_required, require_admin_or_manager
from app.schemas.usuario_schema import Usuario
from app.schemas.termo_aditivo_schema import TermoAditivo, TermoAditivoCreate, TermoAditivoUpdate, TermoAditivoList
from app.repositories.termo_aditivo_repo import TermoAditivoRepository
from app.repositories.contrato_repo import ContratoRepository
from app.services.termo_aditivo_service import TermoAditivoService

router = APIRouter(
    prefix="/contratos/{contrato_id}/aditivos",
    tags=["Termos Aditivos"],
)


def get_service(conn: asyncpg.Connection = Depends(get_connection)) -> TermoAditivoService:
    return TermoAditivoService(
        repo=TermoAditivoRepository(conn),
        contrato_repo=ContratoRepository(conn),
    )


@router.get("/", response_model=TermoAditivoList, summary="Listar termos aditivos do contrato")
async def listar_aditivos(
    contrato_id: int,
    service: TermoAditivoService = Depends(get_service),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista todos os termos aditivos de um contrato. Acessível por qualquer usuário autenticado."""
    itens = await service.listar_por_contrato(contrato_id)
    return TermoAditivoList(data=itens, total=len(itens), contrato_id=contrato_id)


@router.post("/", response_model=TermoAditivo, status_code=status.HTTP_201_CREATED, summary="Criar termo aditivo")
async def criar_aditivo(
    contrato_id: int,
    dados: TermoAditivoCreate,
    service: TermoAditivoService = Depends(get_service),
    current_user: Usuario = Depends(require_admin_or_manager),
):
    """Cria um novo termo aditivo. O número sequencial é atribuído automaticamente. Requer Administrador ou Gestor."""
    return await service.criar(contrato_id, dados)


@router.get("/{aditivo_id}", response_model=TermoAditivo, summary="Buscar termo aditivo por ID")
async def buscar_aditivo(
    contrato_id: int,
    aditivo_id: int,
    service: TermoAditivoService = Depends(get_service),
    current_user: Usuario = Depends(get_current_user),
):
    return await service.buscar_por_id(contrato_id, aditivo_id)


@router.patch("/{aditivo_id}", response_model=TermoAditivo, summary="Atualizar termo aditivo")
async def atualizar_aditivo(
    contrato_id: int,
    aditivo_id: int,
    dados: TermoAditivoUpdate,
    service: TermoAditivoService = Depends(get_service),
    current_user: Usuario = Depends(require_admin_or_manager),
):
    """Atualiza campos de um termo aditivo. Requer Administrador ou Gestor."""
    return await service.atualizar(contrato_id, aditivo_id, dados)


@router.delete("/{aditivo_id}", status_code=status.HTTP_200_OK, summary="Inativar termo aditivo")
async def excluir_aditivo(
    contrato_id: int,
    aditivo_id: int,
    service: TermoAditivoService = Depends(get_service),
    current_user: Usuario = Depends(require_admin_or_manager),
):
    """Exclusão lógica (soft delete) — o registro continua existindo e visível na
    lista, marcado como inativo. Requer Administrador ou Gestor."""
    return await service.excluir(contrato_id, aditivo_id)


@router.delete("/{aditivo_id}/permanente", status_code=status.HTTP_200_OK, summary="Excluir termo aditivo definitivamente")
async def excluir_aditivo_definitivamente(
    contrato_id: int,
    aditivo_id: int,
    service: TermoAditivoService = Depends(get_service),
    current_user: Usuario = Depends(admin_required),
):
    """Exclusão definitiva — remove o registro do banco de dados. Ação irreversível,
    requer Administrador."""
    return await service.excluir_definitivamente(contrato_id, aditivo_id)


@router.post("/{aditivo_id}/arquivo", response_model=TermoAditivo, summary="Fazer upload de arquivo do aditivo")
async def upload_arquivo_aditivo(
    contrato_id: int,
    aditivo_id: int,
    arquivo: UploadFile = File(...),
    service: TermoAditivoService = Depends(get_service),
    current_user: Usuario = Depends(require_admin_or_manager),
):
    """Faz upload e vincula um arquivo (PDF, DOC...) ao termo aditivo. Requer Administrador ou Gestor."""
    return await service.upload_arquivo(contrato_id, aditivo_id, arquivo)
