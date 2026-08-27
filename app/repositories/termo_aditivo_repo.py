# app/repositories/termo_aditivo_repo.py
import asyncpg
from typing import List, Dict, Optional
from app.schemas.termo_aditivo_schema import TermoAditivoCreate, TermoAditivoUpdate


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
        numero = await self.get_proximo_numero(contrato_id)
        query = """
            INSERT INTO termo_aditivo (
                contrato_id, numero_aditivo, tipo, objeto,
                data_assinatura, data_publicacao, data_inicio, nova_data_fim,
                valor_acrescimo, valor_supressao, pae, observacoes, ativo, status
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, TRUE,
                CASE WHEN $8 IS NOT NULL AND $8 < CURRENT_DATE THEN 'Vencido' ELSE 'Ativo' END
            )
            RETURNING id
        """
        new_id = await self.conn.fetchval(
            query,
            contrato_id, numero, dados.tipo, dados.objeto,
            dados.data_assinatura, dados.data_publicacao, dados.data_inicio, dados.nova_data_fim,
            dados.valor_acrescimo, dados.valor_supressao, dados.pae, dados.observacoes
        )
        await self._recalcular_status_contrato(contrato_id)
        return await self.get_by_id(new_id)

    async def _recalcular_status_contrato(self, contrato_id: int) -> None:
        """Recalcula o `status` (Ativo/Vencido/Inativo) de TODOS os termos aditivos
        `ativo = TRUE` do contrato, aplicando as duas regras, nessa ordem de
        prioridade:

        1. Já venceu (nova_data_fim < hoje) -> 'Vencido', sempre, não importa
           se foi ou não substituído por um aditivo mais novo depois.
        2. Não é o de maior número entre os ainda ativos (foi substituído por um
           aditivo mais recente, de qualquer tipo) -> 'Inativo'.
        3. Nenhum dos dois -> 'Ativo' (é o instrumento vigente do contrato).

        Importante: isso NUNCA toca a coluna `ativo` — só `status` (cosmético).
        `ativo` continua servendo só pra soft-delete (Inativar/Excluir) e é o que
        ContratoRepository.sincronizar_vigencia_contrato usa pra achar a data que
        governa o contrato; um aditivo de Prazo/Misto superado apenas por um
        aditivo de Valor/Outros mais novo continua `ativo = TRUE` e continua
        sendo a fonte da vigência do contrato, mesmo aparecendo como 'Inativo'
        na tela (só deixou de ser o "mais recente", não perdeu efeito legal)."""
        await self.conn.execute(
            """
            WITH calculado AS (
                SELECT id, numero_aditivo, nova_data_fim,
                       MAX(numero_aditivo) OVER () AS max_numero_ativo
                FROM termo_aditivo
                WHERE contrato_id = $1 AND ativo = TRUE
            )
            UPDATE termo_aditivo t
            SET status = CASE
                    WHEN c.nova_data_fim IS NOT NULL AND c.nova_data_fim < CURRENT_DATE THEN 'Vencido'
                    WHEN c.numero_aditivo < c.max_numero_ativo THEN 'Inativo'
                    ELSE 'Ativo'
                END,
                updated_at = NOW()
            FROM calculado c
            WHERE t.id = c.id
              AND t.status IS DISTINCT FROM CASE
                    WHEN c.nova_data_fim IS NOT NULL AND c.nova_data_fim < CURRENT_DATE THEN 'Vencido'
                    WHEN c.numero_aditivo < c.max_numero_ativo THEN 'Inativo'
                    ELSE 'Ativo'
                END
            """,
            contrato_id
        )

    async def get_by_id(self, aditivo_id: int) -> Optional[Dict]:
        query = """
            SELECT ta.*
            FROM termo_aditivo ta
            WHERE ta.id = $1 AND ta.ativo = TRUE
        """
        row = await self.conn.fetchrow(query, aditivo_id)
        if not row:
            return None
        result = dict(row)
        result["arquivo_nome"] = None
        if result.get("arquivo_id"):
            arquivo = await self.conn.fetchrow(
                "SELECT nome_arquivo FROM arquivo WHERE id = $1", result["arquivo_id"]
            )
            if arquivo:
                result["arquivo_nome"] = arquivo["nome_arquivo"]
        return result

    async def get_by_contrato(self, contrato_id: int) -> List[Dict]:
        query = """
            SELECT ta.*
            FROM termo_aditivo ta
            WHERE ta.contrato_id = $1
            ORDER BY ta.numero_aditivo ASC
        """
        rows = await self.conn.fetch(query, contrato_id)
        results = []
        for row in rows:
            r = dict(row)
            r["arquivo_nome"] = None
            if r.get("arquivo_id"):
                arquivo = await self.conn.fetchrow(
                    "SELECT nome_arquivo FROM arquivo WHERE id = $1", r["arquivo_id"]
                )
                if arquivo:
                    r["arquivo_nome"] = arquivo["nome_arquivo"]
            results.append(r)
        return results

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
        """Exclusão lógica (inativar) — o registro continua existindo e visível na
        listagem, só marcado como ativo = FALSE. Depois recalcula o status dos
        demais aditivos do contrato: se este era o mais recente e "escondia"
        outro aditivo como Inativo, esse outro volta a aparecer como Ativo/Vencido
        (o inativado deixou de disputar a posição de mais recente)."""
        result = await self.conn.execute(
            """
            UPDATE termo_aditivo
            SET ativo = FALSE, status = 'Inativo', updated_at = NOW()
            WHERE id = $1 AND contrato_id = $2 AND ativo IS NOT FALSE
            """,
            aditivo_id, contrato_id
        )
        await self._recalcular_status_contrato(contrato_id)
        return result == "UPDATE 1"

    async def sincronizar_status_todos_aditivos(self) -> List[int]:
        """Recalcula o status (Ativo/Vencido/Inativo) de TODOS os termos aditivos de
        TODOS os contratos, aplicando a mesma regra de `_recalcular_status_contrato`
        (vencido tem prioridade sobre substituído; só o de maior número entre os
        ativos de cada contrato fica 'Ativo') — usado pelo job noturno (00:02),
        pra cobrir tanto um aditivo vencer só pela passagem do tempo quanto
        qualquer desalinhamento que porventura exista."""
        rows = await self.conn.fetch(
            """
            WITH calculado AS (
                SELECT id, contrato_id, numero_aditivo, nova_data_fim, ativo,
                       MAX(numero_aditivo) FILTER (WHERE ativo) OVER (PARTITION BY contrato_id) AS max_numero_ativo
                FROM termo_aditivo
            ),
            status_final AS (
                SELECT id,
                    CASE
                        WHEN ativo = FALSE THEN 'Inativo'
                        WHEN nova_data_fim IS NOT NULL AND nova_data_fim < CURRENT_DATE THEN 'Vencido'
                        WHEN max_numero_ativo IS NOT NULL AND numero_aditivo < max_numero_ativo THEN 'Inativo'
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

    async def hard_delete(self, aditivo_id: int, contrato_id: int) -> bool:
        """Exclusão definitiva — remove o registro do banco (diferente de `delete`,
        que só inativa). Funciona independente do estado atual de `ativo`, para
        permitir excluir de vez um aditivo que já tinha sido inativado antes.

        termo_aditivo e arquivo têm referência circular (termo_aditivo.arquivo_id
        aponta pro arquivo, e arquivo.termo_aditivo_id aponta de volta) — por isso
        primeiro zera termo_aditivo.arquivo_id, só depois consegue apagar o arquivo
        e, por fim, o próprio termo_aditivo, sem violar nenhuma das duas FKs.
        """
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

    async def get_relatorio_aditivos(
        self,
        filters: Optional[Dict] = None,
        limit: int = 15,
        offset: int = 0,
    ) -> tuple[List[Dict], int]:
        """Lista todos os termos aditivos de todos os contratos, com dados do
        contrato já embutidos — usado pela tela "Gestão de Termos Aditivos".
        Inclui inativos (status_calc = 'Inativo') para dar visibilidade total."""
        where_clauses = []
        params: list = []
        idx = 1

        if filters:
            if filters.get('nr_contrato'):
                where_clauses.append(f"c.nr_contrato ILIKE ${idx}")
                params.append(f"%{filters['nr_contrato']}%")
                idx += 1
            if filters.get('tipo'):
                where_clauses.append(f"ta.tipo = ${idx}")
                params.append(filters['tipo'])
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
            {where_sql}
        """
        total = await self.conn.fetchval(count_query, *params)

        data_query = f"""
            SELECT
                ta.id, ta.contrato_id, ta.numero_aditivo, ta.tipo, ta.objeto,
                ta.data_assinatura, ta.data_publicacao, ta.data_inicio, ta.nova_data_fim,
                ta.valor_acrescimo, ta.valor_supressao, ta.pae, ta.ativo,
                ta.arquivo_id,
                arq.nome_arquivo AS arquivo_nome,
                c.nr_contrato, c.objeto AS contrato_objeto,
                ct.nome AS contratado_nome,
                ta.status AS status_calc
            FROM termo_aditivo ta
            JOIN contrato c ON ta.contrato_id = c.id
            LEFT JOIN contratado ct ON c.contratado_id = ct.id
            LEFT JOIN arquivo arq ON ta.arquivo_id = arq.id
            {where_sql}
            ORDER BY ta.data_assinatura DESC, ta.numero_aditivo DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        rows = await self.conn.fetch(data_query, *params, limit, offset)
        return [dict(r) for r in rows], total if total else 0
