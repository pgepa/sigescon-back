# app/repositories/relatorio_repo.py
import asyncpg
from typing import List, Optional, Dict

class RelatorioRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create_relatorio(
        self,
        contrato_id: int,
        arquivo_id: int,
        status_id: int,
        data: Dict
    ) -> Dict:
        query = """
            INSERT INTO relatoriofiscal
                (contrato_id, fiscal_usuario_id, arquivo_id, status_id,
                 observacoes, pendencia_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """
        relatorio_id = await self.conn.fetchval(
            query,
            contrato_id,
            data['fiscal_usuario_id'],
            arquivo_id,
            status_id,
            data.get('observacoes_fiscal'),
            data['pendencia_id']
        )
        return await self.get_relatorio_by_id(relatorio_id)

    async def get_relatorios_by_contrato_id(self, contrato_id: int) -> List[Dict]:
        query = """
            SELECT
                rf.*, -- Seleciona todos os campos da tabela relatoriofiscal
                u.nome as enviado_por,
                s.nome as status_relatorio,
                a.nome_arquivo
            FROM relatoriofiscal rf
            LEFT JOIN usuario u ON rf.fiscal_usuario_id = u.id
            LEFT JOIN statusrelatorio s ON rf.status_id = s.id
            LEFT JOIN arquivo a ON rf.arquivo_id = a.id
            WHERE rf.contrato_id = $1 AND rf.ativo = TRUE
            ORDER BY rf.created_at DESC
        """
        records = await self.conn.fetch(query, contrato_id)
        return [dict(r) for r in records]

    async def get_relatorio_by_id(self, relatorio_id: int) -> Optional[Dict]:
        query = """
            SELECT
                rf.*,
                u.nome as enviado_por,
                s.nome as status_relatorio,
                a.nome_arquivo
            FROM relatoriofiscal rf
            LEFT JOIN usuario u ON rf.fiscal_usuario_id = u.id
            LEFT JOIN statusrelatorio s ON rf.status_id = s.id
            LEFT JOIN arquivo a ON rf.arquivo_id = a.id
            WHERE rf.id = $1 AND rf.ativo = TRUE
        """
        record = await self.conn.fetchrow(query, relatorio_id)
        return dict(record) if record else None

    async def finalizar_relatorio(self, relatorio_id: int, status_id: int) -> Dict:
        """Marca o relatório como Salvo (final) — sem aprovação de admin, é o
        próprio fiscal que finaliza. `data_envio` registra o momento em que o
        relatório deixou de ser Rascunho e passou a valer como entrega final."""
        query = """
            UPDATE relatoriofiscal
            SET status_id = $1, data_envio = NOW()
            WHERE id = $2
        """
        await self.conn.execute(query, status_id, relatorio_id)
        return await self.get_relatorio_by_id(relatorio_id)

    async def get_relatorios_pendentes_analise(self, contrato_id: int) -> List[Dict]:
        """Busca relatórios com status 'Pendente de Análise' para um contrato"""
        query = """
            SELECT
                rf.*,
                u.nome as enviado_por,
                s.nome as status_relatorio,
                a.nome_arquivo,
                p.descricao as pendencia_descricao
            FROM relatoriofiscal rf
            LEFT JOIN usuario u ON rf.fiscal_usuario_id = u.id
            LEFT JOIN statusrelatorio s ON rf.status_id = s.id
            LEFT JOIN arquivo a ON rf.arquivo_id = a.id
            LEFT JOIN pendenciarelatorio p ON rf.pendencia_id = p.id
            WHERE rf.contrato_id = $1 AND rf.ativo = TRUE AND s.nome = 'Pendente de Análise'
            ORDER BY rf.created_at DESC
        """
        records = await self.conn.fetch(query, contrato_id)
        return [dict(r) for r in records]

    async def get_relatorios_by_pendencia_id(self, pendencia_id: int) -> List[Dict]:
        """Busca todos os relatórios associados a uma pendência específica"""
        query = """
            SELECT
                rf.*,
                u.nome as enviado_por,
                s.nome as status_relatorio,
                a.nome_arquivo
            FROM relatoriofiscal rf
            LEFT JOIN usuario u ON rf.fiscal_usuario_id = u.id
            LEFT JOIN statusrelatorio s ON rf.status_id = s.id
            LEFT JOIN arquivo a ON rf.arquivo_id = a.id
            WHERE rf.pendencia_id = $1 AND rf.ativo = TRUE
            ORDER BY rf.created_at DESC
        """
        records = await self.conn.fetch(query, pendencia_id)
        return [dict(r) for r in records]

    async def update_relatorio_arquivo(self, relatorio_id: int, novo_arquivo_id: int, status_id: int) -> None:
        """Atualiza o arquivo de um relatório (para casos de reenvio)"""
        query = """
            UPDATE relatoriofiscal
            SET arquivo_id = $1, status_id = $2, created_at = NOW()
            WHERE id = $3
        """
        await self.conn.execute(query, novo_arquivo_id, status_id, relatorio_id)

    async def get_all_relatorios_pendentes_analise(self) -> List[Dict]:
        """Busca todos os relatórios com status 'Pendente de Análise' do sistema"""
        query = """
            SELECT
                rf.id,
                rf.contrato_id,
                rf.observacoes,
                rf.created_at as data_envio,
                rf.arquivo_id,
                rf.pendencia_id,
                c.nr_contrato as contrato_numero,
                c.objeto as contrato_objeto,
                ct.nome as contratado_nome,
                u_fiscal.nome as fiscal_nome,
                u_gestor.nome as gestor_nome,
                a.nome_arquivo as arquivo_nome,
                p.descricao as pendencia_titulo,
                s.nome as status_relatorio
            FROM relatoriofiscal rf
            JOIN contrato c ON rf.contrato_id = c.id
            JOIN contratado ct ON c.contratado_id = ct.id
            JOIN usuario u_fiscal ON rf.fiscal_usuario_id = u_fiscal.id
            JOIN usuario u_gestor ON c.gestor_id = u_gestor.id
            JOIN statusrelatorio s ON rf.status_id = s.id
            LEFT JOIN arquivo a ON rf.arquivo_id = a.id
            LEFT JOIN pendenciarelatorio p ON rf.pendencia_id = p.id
            WHERE c.ativo = TRUE AND rf.ativo = TRUE AND s.nome = 'Pendente de Análise'
            ORDER BY rf.created_at ASC
        """
        records = await self.conn.fetch(query)
        return [dict(r) for r in records]