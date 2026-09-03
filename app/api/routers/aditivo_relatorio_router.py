# app/api/routers/aditivo_relatorio_router.py
# Relatório consolidado de termos aditivos de todos os contratos.
import math
import asyncpg
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.core.database import get_connection
from app.repositories.termo_aditivo_repo import TermoAditivoRepository
from app.api.dependencies import get_current_user
from app.schemas.usuario_schema import Usuario

router = APIRouter(
    prefix="/aditivos",
    tags=["Relatório de Termos Aditivos"],
)


@router.get("/relatorio", summary="Relatório de termos aditivos de todos os contratos")
async def relatorio_aditivos(
    page: int = Query(1, ge=1),
    per_page: int = Query(15, ge=1, le=100),
    nr_contrato: Optional[str] = Query(None, description="Filtrar por número do contrato"),
    tipo: Optional[str] = Query(None, description="Prazo, Valor ou Misto"),
    status_calc: Optional[str] = Query(None, description="Ativo, Vencido ou Inativo"),
    conn: asyncpg.Connection = Depends(get_connection),
    current_user: Usuario = Depends(get_current_user),
):
    repo = TermoAditivoRepository(conn)
    offset = (page - 1) * per_page
    filters = {k: v for k, v in {
        "nr_contrato": nr_contrato,
        "tipo": tipo,
        "status_calc": status_calc,
    }.items() if v is not None}

    itens, total = await repo.get_relatorio_aditivos(
        filters=filters or None, limit=per_page, offset=offset
    )
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    return {
        "data": itens,
        "total_items": total,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
    }
