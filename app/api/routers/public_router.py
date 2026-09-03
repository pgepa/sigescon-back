# app/api/routers/public_router.py
# Endpoints públicos sem autenticação — usados pelo Relatório de Contratos
import os
import asyncpg
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from typing import Optional

from app.core.database import get_connection
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.status_repo import StatusRepository
from app.repositories.contratado_repo import ContratadoRepository
from app.repositories.modalidade_repo import ModalidadeRepository
from app.repositories.termo_aditivo_repo import TermoAditivoRepository
from app.services.file_service import FileService

router = APIRouter(
    prefix="/public",
    tags=["Público — Relatório de Contratos"],
)


# ── Contratos ─────────────────────────────────────────────────────────────────

@router.get("/contratos")
async def public_list_contratos(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    status_id: Optional[int] = Query(None),
    contratado_id: Optional[int] = Query(None),
    modalidade_id: Optional[int] = Query(None),
    nr_contrato: Optional[str] = Query(None),
    objeto: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Busca livre por nº contrato, objeto ou contratado"),
    data_inicio: Optional[date] = Query(None, description="Vigência inicia em ou após essa data"),
    data_fim: Optional[date] = Query(None, description="Vigência termina em ou antes dessa data"),
    conn: asyncpg.Connection = Depends(get_connection),
):
    repo = ContratoRepository(conn)
    filters = {k: v for k, v in {
        "status_id": status_id,
        "contratado_id": contratado_id,
        "modalidade_id": modalidade_id,
        "nr_contrato": nr_contrato,
        "objeto": objeto,
        "search": search,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    }.items() if v is not None}

    import math
    offset = (page - 1) * per_page
    # Sem filtro de data: mostra os contratos mais novos primeiro (uso normal de navegação).
    # Com filtro de Data Início/Fim: ordena a partir da data filtrada, para que os
    # resultados mais próximos do que foi buscado apareçam nas primeiras linhas.
    order_by = "c.data_inicio ASC" if (data_inicio or data_fim) else "c.data_inicio DESC"
    contratos, total = await repo.get_all_contratos(
        filters=filters, limit=per_page, offset=offset,
        order_by=order_by,
    )
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    return {
        "data": contratos,
        "total_items": total,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
    }


@router.get("/contratos/{contrato_id}")
async def public_get_contrato(
    contrato_id: int,
    conn: asyncpg.Connection = Depends(get_connection),
):
    repo = ContratoRepository(conn)
    contrato = await repo.find_contrato_by_id(contrato_id)
    if not contrato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    return contrato


@router.get("/contratos/{contrato_id}/arquivos")
async def public_get_arquivos(
    contrato_id: int,
    conn: asyncpg.Connection = Depends(get_connection),
):
    repo = ContratoRepository(conn)
    contrato = await repo.find_contrato_by_id(contrato_id)
    if not contrato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    arquivos = await repo.get_arquivos_contrato(contrato_id)
    return {"arquivos": arquivos, "total_arquivos": len(arquivos), "contrato_id": contrato_id}


@router.get("/contratos/{contrato_id}/aditivos")
async def public_get_aditivos(
    contrato_id: int,
    conn: asyncpg.Connection = Depends(get_connection),
):
    repo = TermoAditivoRepository(conn)
    aditivos = await repo.get_by_contrato(contrato_id)
    return {"data": aditivos}


# ── Download de arquivo ───────────────────────────────────────────────────────

@router.get("/arquivos/{arquivo_id}/download")
async def public_download_arquivo(
    arquivo_id: int,
    conn: asyncpg.Connection = Depends(get_connection),
):
    query = """
        SELECT id, nome_arquivo, caminho_arquivo AS path_armazenamento,
               tipo_mime AS tipo_arquivo, contrato_id
        FROM arquivo
        WHERE id = $1 AND ativo = TRUE
    """
    row = await conn.fetchrow(query, arquivo_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado")

    arquivo = dict(row)
    path = FileService.resolve_path(arquivo["path_armazenamento"])
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo físico não encontrado")

    return FileResponse(
        path=path,
        filename=arquivo["nome_arquivo"],
        media_type=arquivo["tipo_arquivo"] or "application/octet-stream",
        content_disposition_type="attachment",
    )


# ── Tabelas auxiliares ────────────────────────────────────────────────────────

@router.get("/status")
async def public_get_status(conn: asyncpg.Connection = Depends(get_connection)):
    repo = StatusRepository(conn)
    return await repo.get_all_status()


@router.get("/contratados")
async def public_get_contratados(
    conn: asyncpg.Connection = Depends(get_connection),
):
    repo = ContratadoRepository(conn)
    contratados = await repo.get_all_contratados()
    return {"data": contratados, "total": len(contratados)}


@router.get("/modalidades")
async def public_get_modalidades(
    conn: asyncpg.Connection = Depends(get_connection),
):
    repo = ModalidadeRepository(conn)
    return await repo.get_all_modalidades()
