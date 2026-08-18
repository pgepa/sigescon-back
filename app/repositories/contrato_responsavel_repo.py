# app/repositories/contrato_responsavel_repo.py
import asyncpg
import logging
from typing import List, Optional, Dict, Tuple
from datetime import date

logger = logging.getLogger(__name__)


class ContratoResponsavelRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create(self, contrato_id: int, usuario_id: int, tipo: str,
                     data_inicio: date, portaria: Optional[str],
                     criado_por_usuario_id: int) -> Dict:
        query = """
            INSERT INTO contrato_responsavel
                (contrato_id, usuario_id, tipo, data_inicio, portaria, criado_por_usuario_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """
        new_id = await self.conn.fetchval(
            query, contrato_id, usuario_id, tipo, data_inicio,
            portaria, criado_por_usuario_id
        )
        return await self.get_by_id(new_id)

    async def get_by_id(self, responsavel_id: int) -> Optional[Dict]:
        query = """
            SELECT
                cr.*,
                u.nome AS usuario_nome,
                c.nr_contrato AS contrato_nr,
                criador.nome AS criado_por_nome,
                cr.created_at::text AS created_at
            FROM contrato_responsavel cr
            JOIN usuario u ON cr.usuario_id = u.id
            JOIN contrato c ON cr.contrato_id = c.id
            LEFT JOIN usuario criador ON cr.criado_por_usuario_id = criador.id
            WHERE cr.id = $1 AND cr.ativo = TRUE
        """
        row = await self.conn.fetchrow(query, responsavel_id)
        return dict(row) if row else None

    async def get_by_contrato(self, contrato_id: int,
                              tipo: Optional[str] = None,
                              apenas_atuais: bool = False) -> List[Dict]:
        query = """
            SELECT
                cr.*,
                u.nome AS usuario_nome,
                c.nr_contrato AS contrato_nr,
                criador.nome AS criado_por_nome,
                cr.created_at::text AS created_at
            FROM contrato_responsavel cr
            JOIN usuario u ON cr.usuario_id = u.id
            JOIN contrato c ON cr.contrato_id = c.id
            LEFT JOIN usuario criador ON cr.criado_por_usuario_id = criador.id
            WHERE cr.contrato_id = $1 AND cr.ativo = TRUE
        """
        params: list = [contrato_id]
        idx = 2

        if tipo:
            query += f" AND cr.tipo = ${idx}"
            params.append(tipo)
            idx += 1

        if apenas_atuais:
            query += " AND cr.data_fim IS NULL"

        query += " ORDER BY cr.tipo, cr.data_inicio DESC"
        rows = await self.conn.fetch(query, *params)
        return [dict(r) for r in rows]

    async def get_atual(self, contrato_id: int, tipo: str) -> Optional[Dict]:
        query = """
            SELECT
                cr.*,
                u.nome AS usuario_nome,
                cr.created_at::text AS created_at
            FROM contrato_responsavel cr
            JOIN usuario u ON cr.usuario_id = u.id
            WHERE cr.contrato_id = $1
              AND cr.tipo = $2
              AND cr.data_fim IS NULL
              AND cr.ativo = TRUE
            ORDER BY cr.data_inicio DESC
            LIMIT 1
        """
        row = await self.conn.fetchrow(query, contrato_id, tipo)
        return dict(row) if row else None

    async def encerrar_atual(self, contrato_id: int, tipo: str,
                             data_fim: date) -> bool:
        query = """
            UPDATE contrato_responsavel
            SET data_fim = $3, updated_at = NOW()
            WHERE contrato_id = $1
              AND tipo = $2
              AND data_fim IS NULL
              AND ativo = TRUE
        """
        result = await self.conn.execute(query, contrato_id, tipo, data_fim)
        return result.endswith('1')

    async def update(self, responsavel_id: int,
                     data_fim: Optional[date] = None,
                     portaria: Optional[str] = None) -> Optional[Dict]:
        set_clauses = []
        params: list = []
        idx = 1

        if data_fim is not None:
            set_clauses.append(f"data_fim = ${idx}")
            params.append(data_fim)
            idx += 1

        if portaria is not None:
            set_clauses.append(f"portaria = ${idx}")
            params.append(portaria)
            idx += 1

        if not set_clauses:
            return await self.get_by_id(responsavel_id)

        set_clauses.append("updated_at = NOW()")
        params.append(responsavel_id)

        query = f"""
            UPDATE contrato_responsavel
            SET {', '.join(set_clauses)}
            WHERE id = ${idx} AND ativo = TRUE
            RETURNING id
        """
        updated_id = await self.conn.fetchval(query, *params)
        return await self.get_by_id(updated_id) if updated_id else None

    async def delete(self, responsavel_id: int) -> bool:
        query = """
            UPDATE contrato_responsavel
            SET ativo = FALSE, updated_at = NOW()
            WHERE id = $1 AND ativo = TRUE
        """
        result = await self.conn.execute(query, responsavel_id)
        return result.endswith('1')

    async def get_relatorio_responsaveis(
        self,
        filters: Optional[Dict] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        # Nota: a tabela contrato_responsavel (histórico de designações) não existe no
        # banco atual — os responsáveis atuais são lidos direto das colunas de contrato,
        # que é a fonte usada em todo o resto do sistema (dashboard, listagem etc.).
        base_query = """
            FROM contrato c
            LEFT JOIN status s ON c.status_id = s.id
            LEFT JOIN usuario gestor_atual ON c.gestor_id = gestor_atual.id
            LEFT JOIN usuario fiscal_atual ON c.fiscal_id = fiscal_atual.id
            LEFT JOIN usuario fiscal_sub_atual ON c.fiscal_substituto_id = fiscal_sub_atual.id
        """

        where_clauses = ["c.ativo = TRUE"]
        params: list = []
        idx = 1

        if filters:
            if filters.get('nr_contrato'):
                where_clauses.append(f"c.nr_contrato ILIKE ${idx}")
                params.append(f"%{filters['nr_contrato']}%")
                idx += 1
            if filters.get('objeto'):
                where_clauses.append(f"c.objeto ILIKE ${idx}")
                params.append(f"%{filters['objeto']}%")
                idx += 1
            if filters.get('status_id'):
                where_clauses.append(f"c.status_id = ${idx}")
                params.append(filters['status_id'])
                idx += 1
            if filters.get('gestor_nome'):
                where_clauses.append(f"gestor_atual.nome ILIKE ${idx}")
                params.append(f"%{filters['gestor_nome']}%")
                idx += 1
            if filters.get('fiscal_nome'):
                where_clauses.append(f"fiscal_atual.nome ILIKE ${idx}")
                params.append(f"%{filters['fiscal_nome']}%")
                idx += 1

        where_sql = " WHERE " + " AND ".join(where_clauses)

        count_query = f"SELECT COUNT(c.id) {base_query}{where_sql}"
        total = await self.conn.fetchval(count_query, *params)

        data_query = f"""
            SELECT
                c.id AS contrato_id,
                c.nr_contrato,
                c.objeto,
                c.data_inicio,
                c.data_fim,
                s.nome AS status_nome,
                gestor_atual.nome AS gestor_atual_nome,
                gestor_atual.id AS gestor_atual_id,
                fiscal_atual.nome AS fiscal_atual_nome,
                fiscal_atual.id AS fiscal_atual_id,
                fiscal_sub_atual.nome AS fiscal_substituto_atual_nome,
                fiscal_sub_atual.id AS fiscal_substituto_atual_id
            {base_query}{where_sql}
            ORDER BY c.nr_contrato ASC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        paginated_params = params + [limit, offset]
        rows = await self.conn.fetch(data_query, *paginated_params)
        return [dict(r) for r in rows], total if total else 0
