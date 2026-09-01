# app/api/routers/relatorio_router.py
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from typing import List
from datetime import date

from app.core.database import get_connection
from app.schemas.usuario_schema import Usuario
from app.api.dependencies import get_current_user
from app.api.permissions import PermissionChecker

# Repositórios
from app.repositories.relatorio_repo import RelatorioRepository
from app.repositories.arquivo_repo import ArquivoRepository
from app.repositories.pendencia_repo import PendenciaRepository
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.status_relatorio_repo import StatusRelatorioRepository
from app.repositories.status_pendencia_repo import StatusPendenciaRepository
from app.repositories.usuario_repo import UsuarioRepository
from app.repositories.perfil_repo import PerfilRepository 

# Services
from app.services.relatorio_service import RelatorioService
from app.services.file_service import FileService

# Schemas
from app.schemas.relatorio_schema import Relatorio, RelatorioCreate

router = APIRouter(
    prefix="/contratos/{contrato_id}/relatorios",
    tags=["Relatórios Fiscais"]
)

# --- INJEÇÃO DE DEPENDÊNCIAS ---
def get_relatorio_service(conn: asyncpg.Connection = Depends(get_connection)) -> RelatorioService:
    return RelatorioService(
        relatorio_repo=RelatorioRepository(conn),
        arquivo_repo=ArquivoRepository(conn),
        pendencia_repo=PendenciaRepository(conn),
        contrato_repo=ContratoRepository(conn),
        status_relatorio_repo=StatusRelatorioRepository(conn),
        status_pendencia_repo=StatusPendenciaRepository(conn),
        usuario_repo=UsuarioRepository(conn),
        perfil_repo=PerfilRepository(conn), 
        file_service=FileService()
    )

# --- Endpoints (sem alteração) ---

@router.post("/", response_model=Relatorio, status_code=status.HTTP_201_CREATED)
async def submit_relatorio(
    contrato_id: int,
    arquivo: UploadFile = File(...),
    observacoes_fiscal: str | None = Form(None),
    pendencia_id: int = Form(...),
    service: RelatorioService = Depends(get_relatorio_service),
    current_user: Usuario = Depends(get_current_user)
):
    """Salva o relatório fiscal como Rascunho, respondendo a uma pendência.
    Pode ser chamado várias vezes para editar o rascunho (substitui o arquivo
    e as observações) até ser finalizado em /finalizar."""
    relatorio_data = RelatorioCreate(
        observacoes_fiscal=observacoes_fiscal,
        pendencia_id=pendencia_id,
        fiscal_usuario_id=current_user.id
    )
    return await service.submit_relatorio(contrato_id, relatorio_data, arquivo, current_user)


# Rota com barra final (original)
@router.get("/", response_model=List[Relatorio])
async def list_relatorios(
    contrato_id: int,
    service: RelatorioService = Depends(get_relatorio_service),
    current_user: Usuario = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_connection)
):
    checker = PermissionChecker(conn)
    if not await checker.can_access_contract(current_user, contrato_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este contrato"
        )
    """Lista todos os relatórios de um contrato específico."""
    return await service.get_relatorios_by_contrato_id(contrato_id)

# Rota sem barra final (para evitar redirects do frontend)
@router.get("", response_model=List[Relatorio])
async def list_relatorios_without_slash(
    contrato_id: int,
    service: RelatorioService = Depends(get_relatorio_service),
    current_user: Usuario = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_connection)
):
    checker = PermissionChecker(conn)
    if not await checker.can_access_contract(current_user, contrato_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este contrato"
        )
    """Lista todos os relatórios de um contrato específico."""
    return await service.get_relatorios_by_contrato_id(contrato_id)


@router.patch("/{relatorio_id}/finalizar", response_model=Relatorio)
async def finalizar_relatorio(
    request: Request,
    contrato_id: int,
    relatorio_id: int,
    service: RelatorioService = Depends(get_relatorio_service),
    current_user: Usuario = Depends(get_current_user)
):
    """Finaliza o relatório (Rascunho -> Salvo) e conclui a pendência vinculada.
    Sem aprovação de terceiros: só o fiscal titular do contrato (ou admin) pode
    finalizar, e só um relatório em Rascunho pode ser finalizado."""
    return await service.finalizar_relatorio(contrato_id, relatorio_id, current_user, request)