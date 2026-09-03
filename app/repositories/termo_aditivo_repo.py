# app/repositories/termo_aditivo_repo.py
import asyncpg
import logging
from typing import List, Dict, Optional, Tuple
from app.schemas.termo_aditivo_schema import TermoAditivoCreate, TermoAditivoUpdate

logger = logging.getLogger(__name__)


class TermoAditivoRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_proximo_numero(self, contrato_id: int) -> int:
        """Retorna o próximo número sequencial de aditivo para o contrato.
        Considera TODOS os registros (inclusive excluídos) para não reutilizar números."""
        result = await self.conn.fetchval(
            "SELECT COALESCE(MAX(numero_aditivo), 0) + 1 FROM termo_aditivo WHERE contrato_id = $1",
            contrato_id
        )
        return result

    async def count_ativos(self, contrato_id: int) -> int:
        """Conta termos aditivos ativos (não excluídos) do contrato."""
        return await self.conn.fetchval(
            "SELECT COUNT(*) FROM termo_aditivo WHERE contrato_id = $1 AND ativo = TRUE",
            contrato_id
        )

    async def create(self, contrato_id: int, dados: TermoAditivoCreate) -> Dict:
        numero = dados.numero_aditivo or await self.get_proximo_numero(contrato_id)
        query = """
            INSERT INTO termo_aditivo (
                contrato_id, numero_aditivo, tipo_id, objeto,
                data_assinatura, data_publicacao, data_inicio, nova_data_fim,
                valor_acrescimo, valor_supressao, pae, observacoes, ativo, status, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8::date, $9, $10, $11, $12, TRUE,
                CASE WHEN $8::date IS NOT NULL AND $8::date < CURRENT_DATE THEN 'Vencido' ELSE 'Ativo' END,
                NOW(), NOW()
            )
            RETURNING id
        """
        new_id = await self.conn.fetchval(
            query,
            contrato_id, numero, dados.tipo_id, dados.objeto,
            dados.data_assinatura, dados.data_publicacao, dados.data_inicio, dados.nova_data_fim,
            dados.valor_acrescimo, dados.valor_supressao, dados.pae, dados.observacoes
        )
        await self._recalcular_status_contrato(contrato_id)
        return await self.get_by_id(new_id)

    async def _recalcular_status_contrato(self, contrato_id: int) -> None:
        """
        Recalcula o `status` (Ativo/Vencido/Inativo) dos termos aditivos `ativo = TRUE` do contrato,
        aplicando a REGRA DE INATIVAÇÃO SELETIVA POR NATUREZA:

        1. 'Vencido': Se nova_data_fim < CURRENT_DATE.
        2. 'Inativo' por sobreposição de mesma natureza:
           - Termos que afetam PRAZO (tipo_id in 1, 3): inativados se houver termo posterior de Prazo/Misto ativo.
           - Termos que afetam VALOR (tipo_id in 2, 3): inativados se houver termo posterior de Valor/Misto ativo.
        3. 'Ativo':
           - Termos de OUTROS (tipo_id = 4) NUNCA são inativados por outros aditivos (coexistem).
           - Termos de naturezas distintas (ex: Prazo e Valor) coexistem ambos como 'Ativo'.
        """
        await self.conn.execute(
            """
            WITH calculado AS (
                SELECT 
                    id, 
                    numero_aditivo, 
                    tipo_id,
                    nova_data_fim,
                    MAX(numero_aditivo) FILTER (WHERE tipo_id IN (1, 3)) OVER () AS max_num_prazo,
                    MAX(numero_aditivo) FILTER (WHERE tipo_id IN (2, 3)) OVER () AS max_num_valor
                FROM termo_aditivo
                WHERE contrato_id = $1 AND ativo = TRUE
            ),
            classificado AS (
                SELECT id,
                    CASE
                        WHEN nova_data_fim IS NOT NULL AND nova_data_fim < CURRENT_DATE THEN 'Vencido'
                        -- Se afeta Prazo e não é o mais recente de Prazo -> Inativo
                        WHEN tipo_id = 1 AND max_num_prazo IS NOT NULL AND numero_aditivo < max_num_prazo THEN 'Inativo'
                        -- Se afeta Valor e não é o mais recente de Valor -> Inativo
                        WHEN tipo_id = 2 AND max_num_valor IS NOT NULL AND numero_aditivo < max_num_valor THEN 'Inativo'
                        -- Se é Misto e foi superado em Prazo ou em Valor -> Inativo
                        WHEN tipo_id = 3 AND (
                            (max_num_prazo IS NOT NULL AND numero_aditivo < max_num_prazo) OR
                            (max_num_valor IS NOT NULL AND numero_aditivo < max_num_valor)
                        ) THEN 'Inativo'
                        -- Outros (4) ou aditivo mais recente de sua respectiva natureza -> Ativo
                        ELSE 'Ativo'
                    END AS novo_status
                FROM calculado
            )
            UPDATE termo_aditivo t
            SET status = c.novo_status, updated_at = NOW()
            FROM classificado c
            WHERE t.id = c.id
              AND t.status IS DISTINCT FROM c.novo_status
            """,
            contrato_id
        )

    async def sincronizar_status_todos_aditivos(self) -> List[int]:
        """
        Rotina diária executada pelo Robô/Scheduler para todos os contratos ativos do sistema.
        Aplica a regra de convivência e inativação seletiva por natureza.
        """
        rows = await self.conn.fetch(
            """
            WITH calculado AS (
                SELECT 
                    id, 
                    contrato_id,
                    numero_aditivo, 
                    tipo_id,
                    nova_data_fim,
                    ativo,
                    MAX(numero_aditivo) FILTER (WHERE ativo AND tipo_id IN (1, 3)) OVER (PARTITION BY contrato_id) AS max_num_prazo,
                    MAX(numero_aditivo) FILTER (WHERE ativo AND tipo_id IN (2, 3)) OVER (PARTITION BY contrato_id) AS max_num_valor
                FROM termo_aditivo
            ),
            status_final AS (
                SELECT id,
                    CASE
                        WHEN ativo = FALSE THEN 'Inativo'
                        WHEN nova_data_fim IS NOT NULL AND nova_data_fim < CURRENT_DATE THEN 'Vencido'
                        WHEN tipo_id = 1 AND max_num_prazo IS NOT NULL AND numero_aditivo < max_num_prazo THEN 'Inativo'
                        WHEN tipo_id = 2 AND max_num_valor IS NOT NULL AND numero_aditivo < max_num_valor THEN 'Inativo'
                        WHEN tipo_id = 3 AND (
                            (max_num_prazo IS NOT NULL AND numero_aditivo < max_num_prazo) OR
                            (max_num_valor IS NOT NULL AND numero_aditivo < max_num_valor)
                        ) THEN 'Inativo'
                        ELSE 'Ativo'
                    END AS status_calculado
                FROM calculado
            )
            UPDATE termo_aditivo t
            SET status = s.status_calculado, updated_at = NOW()
            FROM status_final s
            WHERE t.id = s.id AND t.status IS DISTINCT FROM s.status_calculado
            RETURNING t.id
            """
        )
        return [r["id"] for r in rows]

    async def get_by_id(self, aditivo_id: int) -> Optional[Dict]:
        query = """
            SELECT 
                ta.*,
                tta.nome AS tipo_nome,
                tta.descricao AS tipo_descricao,
                arq.nome_arquivo AS arquivo_nome
            FROM termo_aditivo ta
            JOIN tipo_termo_aditivo tta ON ta.tipo_id = tta.id
            LEFT JOIN arquivo arq ON ta.arquivo_id = arq.id
            WHERE ta.id = $1 AND ta.ativo = TRUE
        """
        row = await self.conn.fetchrow(query, aditivo_id)
        return dict(row) if row else None

    async def get_by_contrato(self, contrato_id: int) -> List[Dict]:
        query = """
            SELECT 
                ta.*,
                tta.nome AS tipo_nome,
                tta.descricao AS tipo_descricao,
                arq.nome_arquivo AS arquivo_nome
            FROM termo_aditivo ta
            JOIN tipo_termo_aditivo tta ON ta.tipo_id = tta.id
            LEFT JOIN arquivo arq ON ta.arquivo_id = arq.id
            WHERE ta.contrato_id = $1
            ORDER BY ta.numero_aditivo ASC
        """
        rows = await self.conn.fetch(query, contrato_id)
        return [dict(r) for r in rows]

    async def update(self, aditivo_id: int, dados: TermoAditivoUpdate) -> Optional[Dict]:
        fields = dados.model_dump(exclude_unset=True)
        if not fields:
            return await self.get_by_id(aditivo_id)

        set_parts = [f"{k} = ${i+2}" for i, k in enumerate(fields.keys())]
        set_parts.append("updated_at = NOW()")
        values = list(fields.values())

        contrato_id = await self.conn.fetchval(
            "SELECT contrato_id FROM termo_aditivo WHERE id = $1", aditivo_id
        )

        query = f"UPDATE termo_aditivo SET {', '.join(set_parts)} WHERE id = $1 AND ativo = TRUE"
        await self.conn.execute(query, aditivo_id, *values)
        if contrato_id is not None:
            await self._recalcular_status_contrato(contrato_id)
        return await self.get_by_id(aditivo_id)

    async def delete(self, aditivo_id: int, contrato_id: int) -> bool:
        """Exclusão lógica (inativar)"""
        result = await self.conn.execute(
            """
            UPDATE termo_aditivo
            SET ativo = FALSE, status = 'Inativo', updated_at = NOW()
            WHERE id = $1 AND contrato_id = $2
            """,
            aditivo_id, contrato_id
        )
        await self._recalcular_status_contrato(contrato_id)
        return result == "UPDATE 1"

    async def hard_delete(self, aditivo_id: int, contrato_id: int) -> bool:
        """Exclusão definitiva"""
        async with self.conn.transaction():
            await self.conn.execute(
                "UPDATE termo_aditivo SET arquivo_id = NULL WHERE id = $1", aditivo_id
            )
            await self.conn.execute(
                "DELETE FROM arquivo WHERE termo_aditivo_id = $1", aditivo_id
            )
            result = await self.conn.execute(
                "DELETE FROM termo_aditivo WHERE id = $1 AND contrato_id = $2",
                aditivo_id, contrato_id
            )
        await self._recalcular_status_contrato(contrato_id)
        return result == "DELETE 1"

    async def vincular_arquivo(self, aditivo_id: int, arquivo_id: int) -> Optional[Dict]:
        await self.conn.execute(
            "UPDATE termo_aditivo SET arquivo_id = $1, updated_at = NOW() WHERE id = $2 AND ativo = TRUE",
            arquivo_id, aditivo_id
        )
        return await self.get_by_id(aditivo_id)

    async def get_aditivo_vigencia_recente(self, contrato_id: int) -> Optional[Dict]:
        """Retorna o aditivo de vigência (Prazo ou Misto) mais recente ativo."""
        query = """
            SELECT * FROM termo_aditivo
            WHERE contrato_id = $1 
              AND tipo_id IN (1, 3) 
              AND ativo = TRUE
              AND status = 'Ativo'
              AND nova_data_fim IS NOT NULL
            ORDER BY numero_aditivo DESC
            LIMIT 1
        """
        row = await self.conn.fetchrow(query, contrato_id)
        return dict(row) if row else None

    async def get_totais_valores_aditivos_ativos(self, contrato_id: int) -> Dict[str, float]:
        """Calcula soma de acréscimos e supressões de aditivos de valor/misto ativos."""
        query = """
            SELECT 
                COALESCE(SUM(valor_acrescimo), 0.0) as total_acrescimo,
                COALESCE(SUM(valor_supressao), 0.0) as total_supressao
            FROM termo_aditivo
            WHERE contrato_id = $1 
              AND tipo_id IN (2, 3) 
              AND ativo = TRUE
              AND status = 'Ativo'
        """
        row = await self.conn.fetchrow(query, contrato_id)
        return {
            'total_acrescimo': float(row['total_acrescimo']),
            'total_supressao': float(row['total_supressao'])
        }

    async def get_relatorio_aditivos(
        self,
        filters: Optional[Dict] = None,
        limit: int = 15,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        where_clauses = []
        params: list = []
        idx = 1

        if filters:
            if filters.get('nr_contrato'):
                where_clauses.append(f"c.nr_contrato ILIKE ${idx}")
                params.append(f"%{filters['nr_contrato']}%")
                idx += 1
            if filters.get('tipo_id'):
                where_clauses.append(f"ta.tipo_id = ${idx}")
                params.append(filters['tipo_id'])
                idx += 1
            elif filters.get('tipo'):
                # Compatibilidade com busca por nome de tipo
                where_clauses.append(f"tta.nome ILIKE ${idx}")
                params.append(f"%{filters['tipo']}%")
                idx += 1
            status_calc = filters.get('status_calc')
            if status_calc in ('Ativo', 'Vencido', 'Inativo'):
                where_clauses.append(f"ta.status = ${idx}")
                params.append(status_calc)
                idx += 1

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        count_query = f"""
            SELECT COUNT(*) FROM termo_aditivo ta
            JOIN contrato c ON ta.contrato_id = c.id
            JOIN tipo_termo_aditivo tta ON ta.tipo_id = tta.id
            {where_sql}
        """
        total = await self.conn.fetchval(count_query, *params)

        data_query = f"""
            SELECT
                ta.id, ta.contrato_id, ta.numero_aditivo, ta.tipo_id, ta.objeto,
                tta.nome AS tipo_nome, tta.descricao AS tipo_descricao,
                ta.data_assinatura, ta.data_publicacao, ta.data_inicio, ta.nova_data_fim,
                ta.valor_acrescimo, ta.valor_supressao, ta.pae, ta.ativo,
                ta.arquivo_id,
                arq.nome_arquivo AS arquivo_nome,
                c.nr_contrato, c.objeto AS contrato_objeto,
                ct.nome AS contratado_nome,
                ta.status AS status_calc
            FROM termo_aditivo ta
            JOIN contrato c ON ta.contrato_id = c.id
            JOIN tipo_termo_aditivo tta ON ta.tipo_id = tta.id
            LEFT JOIN contratado ct ON c.contratado_id = ct.id
            LEFT JOIN arquivo arq ON ta.arquivo_id = arq.id
            {where_sql}
            ORDER BY ta.data_assinatura DESC, ta.numero_aditivo DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        rows = await self.conn.fetch(data_query, *params, limit, offset)
        return [dict(r) for r in rows], total if total else 0
