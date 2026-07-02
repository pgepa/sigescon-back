# app/api/routers/arquivo_router.py
import asyncpg
import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.services.file_service import FileService
from app.core.database import get_connection
from app.schemas.usuario_schema import Usuario
from app.api.dependencies import get_current_user
from app.api.permissions import PermissionChecker
from app.repositories.arquivo_repo import ArquivoRepository
from app.repositories.relatorio_repo import RelatorioRepository

router = APIRouter(
    prefix="/arquivos",
    tags=["Arquivos"]
)

@router.get("/{arquivo_id}/download")
async def download_arquivo(
    arquivo_id: int,
    conn: asyncpg.Connection = Depends(get_connection),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Fornece um arquivo para download.

    Verifica se o usuário logado tem permissão para acessar o contrato
    ao qual o arquivo pertence (seja como admin, gestor ou fiscal).
    """
    arquivo_repo = ArquivoRepository(conn)
    arquivo = await arquivo_repo.find_arquivo_by_id(arquivo_id)

    if not arquivo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado no banco de dados.")

    # Verificação de permissão
    contrato_id = arquivo.get('contrato_id')
    checker = PermissionChecker(conn)
    if not await checker.can_access_contract(current_user, contrato_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para acessar este arquivo.")

    # Verificação de existência física
    path_completo = FileService.resolve_path(arquivo.get('path_armazenamento', ''))
    if not os.path.exists(path_completo):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo físico não encontrado no servidor.")

    nome_original = arquivo.get('nome_arquivo')
    
    return FileResponse(
        path=path_completo,
        filename=nome_original,
        media_type=arquivo.get('tipo_arquivo'),
        content_disposition_type="attachment"
    )


@router.get("/portaria/contrato/{contrato_id}")
async def list_arquivos_portaria(
    contrato_id: int,
    conn: asyncpg.Connection = Depends(get_connection),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos os arquivos de portaria de designação de um contrato.
    """
    checker = PermissionChecker(conn)
    if not await checker.can_access_contract(current_user, contrato_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este contrato"
        )

    query = """
        SELECT id, nome_arquivo, tipo_mime AS tipo_arquivo,
               tamanho_bytes, contrato_id, created_at::text AS created_at
        FROM arquivo
        WHERE contrato_id = $1 AND tipo_vinculo = 'portaria' AND ativo = TRUE
        ORDER BY created_at DESC
    """
    rows = await conn.fetch(query, contrato_id)
    arquivos = [dict(r) for r in rows]

    return {
        "arquivos_portaria": arquivos,
        "total_arquivos": len(arquivos),
        "contrato_id": contrato_id
    }


@router.get("/relatorios/contrato/{contrato_id}")
async def list_arquivos_relatorios(
    contrato_id: int,
    conn: asyncpg.Connection = Depends(get_connection),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos os arquivos de relatórios de um contrato específico.

    Retorna somente arquivos que foram enviados como relatórios fiscais,
    separados dos arquivos contratuais.
    """
    # Verificação de permissão
    checker = PermissionChecker(conn)
    if not await checker.can_access_contract(current_user, contrato_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este contrato"
        )

    relatorio_repo = RelatorioRepository(conn)
    arquivo_repo = ArquivoRepository(conn)

    # Busca todos os relatórios do contrato
    relatorios = await relatorio_repo.get_relatorios_by_contrato_id(contrato_id)

    # Extrai os IDs dos arquivos dos relatórios
    arquivo_ids = [r['arquivo_id'] for r in relatorios if r.get('arquivo_id')]

    # Busca os detalhes dos arquivos
    arquivos_relatorios = []
    for arquivo_id in arquivo_ids:
        arquivo = await arquivo_repo.find_arquivo_by_id(arquivo_id)
        if arquivo:
            # Encontra o relatório correspondente para dados adicionais
            relatorio = next((r for r in relatorios if r['arquivo_id'] == arquivo_id), None)

            arquivo_info = {
                "id": arquivo['id'],
                "nome_arquivo": arquivo['nome_arquivo'],
                "tipo_arquivo": arquivo['tipo_arquivo'],
                "tamanho_bytes": arquivo['tamanho_bytes'],
                "created_at": arquivo['created_at'],
                "relatorio_id": relatorio['id'] if relatorio else None,
                "status_relatorio": relatorio['status_relatorio'] if relatorio else None,
                "enviado_por": relatorio['enviado_por'] if relatorio else None,
                "data_envio": relatorio['created_at'] if relatorio else None
            }
            arquivos_relatorios.append(arquivo_info)

    # Ordena por data de criação (mais recentes primeiro)
    arquivos_relatorios.sort(key=lambda x: x['created_at'], reverse=True)

    return {
        "arquivos_relatorios": arquivos_relatorios,
        "total_arquivos": len(arquivos_relatorios),
        "contrato_id": contrato_id
    }