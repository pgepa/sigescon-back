# app/api/routers/tipo_termo_aditivo_router.py
import asyncpg
from fastapi import APIRouter, Depends
from typing import List

from app.core.database import get_connection
from app.api.dependencies import get_current_user
from app.schemas.usuario_schema import Usuario
from app.schemas.termo_aditivo_schema import TipoTermoAditivoResponse
from app.repositories.tipo_termo_aditivo_repo import TipoTermoAditivoRepository

router = APIRouter(
    prefix="/tipos-termo-aditivo",
    tags=["Tipos de Termo Aditivo"],
)


@router.get("", response_model=List[TipoTermoAditivoResponse], summary="Listar tipos de termo aditivo")
@router.get("/", response_model=List[TipoTermoAditivoResponse], include_in_schema=False)
async def listar_tipos(
    conn: asyncpg.Connection = Depends(get_connection),
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna todos os tipos de termos aditivos ativos (Prazo, Valor, Misto, Outros)."""
    repo = TipoTermoAditivoRepository(conn)
    tipos = await repo.get_all(apenas_ativos=True)
    return [TipoTermoAditivoResponse.model_validate(t) for t in tipos]
