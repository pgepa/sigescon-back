# app/repositories/tipo_termo_aditivo_repo.py
import asyncpg
from typing import List, Optional, Dict


class TipoTermoAditivoRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_all(self, apenas_ativos: bool = True) -> List[Dict]:
        query = "SELECT id, nome, descricao, ativo, created_at, updated_at FROM tipo_termo_aditivo"
        if apenas_ativos:
            query += " WHERE ativo = TRUE"
        query += " ORDER BY id"
        records = await self.conn.fetch(query)
        return [dict(r) for r in records]

    async def get_by_id(self, tipo_id: int) -> Optional[Dict]:
        query = "SELECT id, nome, descricao, ativo, created_at, updated_at FROM tipo_termo_aditivo WHERE id = $1"
        record = await self.conn.fetchrow(query, tipo_id)
        return dict(record) if record else None
