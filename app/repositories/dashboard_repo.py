# app/repositories/dashboard_repo.py
import asyncpg
from typing import List, Dict, Any
from datetime import date, datetime


class DashboardRepository:
    def __init__(self, connection: asyncpg.Connection):
        self.conn = connection

    async def get_contratos_com_relatorios_pendentes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Busca contratos que têm relatórios aguardando análise pelo administrador
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('contrato', 'contratado', 'usuario', 'status', 'relatoriofiscal', 'statusrelatorio')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['contrato', 'contratado', 'usuario', 'status', 'relatoriofiscal', 'statusrelatorio']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando lista vazia.")
                return []

            query = """
            SELECT DISTINCT
                c.id,
                c.nr_contrato,
                c.objeto,
                c.data_inicio,
                c.data_fim,
                ct.nome as contratado_nome,
                u_gestor.nome as gestor_nome,
                u_fiscal.nome as fiscal_nome,
                s.nome as status_nome,
                COUNT(r.id) as relatorios_pendentes_count,
                MAX(r.created_at) as ultimo_relatorio_data,
                u_ultimo_fiscal.nome as ultimo_relatorio_fiscal
            FROM contrato c
            JOIN contratado ct ON c.contratado_id = ct.id
            JOIN usuario u_gestor ON c.gestor_id = u_gestor.id
            JOIN usuario u_fiscal ON c.fiscal_id = u_fiscal.id
            JOIN status s ON c.status_id = s.id
            JOIN relatoriofiscal r ON r.contrato_id = c.id
            JOIN statusrelatorio sr ON r.status_id = sr.id
            LEFT JOIN usuario u_ultimo_fiscal ON r.fiscal_usuario_id = u_ultimo_fiscal.id
            WHERE
                c.ativo = true
                AND sr.nome = 'Pendente de Análise'
            GROUP BY
                c.id, c.nr_contrato, c.objeto, c.data_inicio, c.data_fim,
                ct.nome, u_gestor.nome, u_fiscal.nome, s.nome, u_ultimo_fiscal.nome
            ORDER BY MAX(r.created_at) ASC
            LIMIT $1
            """
            rows = await self.conn.fetch(query, limit)
            return [dict(row) for row in rows]

        except Exception as e:
            print(f"Erro ao buscar contratos com relatórios pendentes: {e}. Retornando lista vazia.")
            return []

    async def get_contratos_com_pendencias(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Busca contratos que têm pendências ativas (status 'Pendente')
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('contrato', 'contratado', 'usuario', 'status', 'pendenciarelatorio', 'statuspendencia')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['contrato', 'contratado', 'usuario', 'status', 'pendenciarelatorio', 'statuspendencia']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando lista vazia.")
                return []

            query = """
            SELECT DISTINCT
                c.id,
                c.nr_contrato,
                c.objeto,
                c.data_inicio,
                c.data_fim,
                ct.nome as contratado_nome,
                u_gestor.nome as gestor_nome,
                u_fiscal.nome as fiscal_nome,
                s.nome as status_nome,
                COUNT(p.id) as pendencias_count,
                SUM(CASE WHEN p.data_prazo < CURRENT_DATE THEN 1 ELSE 0 END) as pendencias_em_atraso,
                MAX(p.created_at) as ultima_pendencia_data
            FROM contrato c
            JOIN contratado ct ON c.contratado_id = ct.id
            JOIN usuario u_gestor ON c.gestor_id = u_gestor.id
            JOIN usuario u_fiscal ON c.fiscal_id = u_fiscal.id
            JOIN status s ON c.status_id = s.id
            JOIN pendenciarelatorio p ON p.contrato_id = c.id
            JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
            WHERE
                c.ativo = true
                AND sp.nome = 'Pendente'
            GROUP BY
                c.id, c.nr_contrato, c.objeto, c.data_inicio, c.data_fim,
                ct.nome, u_gestor.nome, u_fiscal.nome, s.nome
            ORDER BY MAX(p.created_at) ASC
            LIMIT $1
            """
            rows = await self.conn.fetch(query, limit)
            return [dict(row) for row in rows]

        except Exception as e:
            print(f"Erro ao buscar contratos com pendências: {e}. Retornando lista vazia.")
            return []

    async def get_minhas_pendencias_fiscal(self, fiscal_id: int) -> List[Dict[str, Any]]:
        """
        Busca todas as pendências ativas de um fiscal específico
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('pendenciarelatorio', 'contrato', 'statuspendencia')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['pendenciarelatorio', 'contrato', 'statuspendencia']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando lista vazia.")
                return []

            query = """
            SELECT
                c.id as contrato_id,
                c.nr_contrato as contrato_numero,
                c.objeto as contrato_objeto,
                p.id as pendencia_id,
                p.descricao as pendencia_descricao,
                p.created_at,
                p.data_prazo,
                CASE
                    WHEN p.data_prazo IS NOT NULL AND p.data_prazo < CURRENT_DATE
                    THEN (CURRENT_DATE - p.data_prazo)::int
                    WHEN p.data_prazo IS NOT NULL
                    THEN (p.data_prazo - CURRENT_DATE)::int
                    ELSE NULL
                END as dias_restantes,
                CASE
                    WHEN p.data_prazo IS NOT NULL AND p.data_prazo < CURRENT_DATE
                    THEN true
                    ELSE false
                END as em_atraso
            FROM pendenciarelatorio p
            JOIN contrato c ON p.contrato_id = c.id
            JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
            WHERE
                c.ativo = true
                AND (c.fiscal_id = $1 OR c.fiscal_substituto_id = $1)
                AND sp.nome = 'Pendente'
            ORDER BY
                CASE WHEN p.data_prazo < CURRENT_DATE THEN 0 ELSE 1 END,
                p.data_prazo ASC NULLS LAST,
                p.created_at ASC
            """
            rows = await self.conn.fetch(query, fiscal_id)
            return [dict(row) for row in rows]

        except Exception as e:
            print(f"Erro ao buscar pendências do fiscal: {e}. Retornando lista vazia.")
            return []

    async def get_contadores_admin(self) -> Dict[str, int]:
        """
        Busca contadores para o dashboard do administrador
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('relatoriofiscal', 'statusrelatorio', 'contrato', 'pendenciarelatorio', 'statuspendencia', 'usuario', 'contratado')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            contadores = {
                'relatorios_para_analise': 0,
                'contratos_com_pendencias': 0,
                'usuarios_ativos': 0,
                'contratos_ativos': 0,
                'total_contratacoes': 0,
                'contratados_com_pendencias_vencidas': 0,
                'minhas_pendencias': 0,
                'pendencias_em_atraso': 0,
                'relatorios_enviados_mes': 0,
                'contratos_sob_gestao': 0,
                'relatorios_equipe_pendentes': 0
            }

            # Relatórios para análise
            if all(table in table_names for table in ['relatoriofiscal', 'statusrelatorio']):
                query = """
                    SELECT COUNT(*)
                    FROM relatoriofiscal r
                    JOIN statusrelatorio sr ON r.status_id = sr.id
                    WHERE sr.nome = 'Pendente de Análise'
                """
                result = await self.conn.fetchval(query)
                contadores['relatorios_para_analise'] = result or 0

            # Contratos com pendências
            if all(table in table_names for table in ['contrato', 'pendenciarelatorio', 'statuspendencia']):
                query = """
                    SELECT COUNT(DISTINCT c.id)
                    FROM contrato c
                    JOIN pendenciarelatorio p ON p.contrato_id = c.id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE c.ativo = true AND sp.nome = 'Pendente'
                """
                result = await self.conn.fetchval(query)
                contadores['contratos_com_pendencias'] = result or 0

            # Usuários ativos
            if 'usuario' in table_names:
                query = """
                    SELECT COUNT(*)
                    FROM usuario
                    WHERE ativo = true
                """
                result = await self.conn.fetchval(query)
                contadores['usuarios_ativos'] = result or 0

            # Contratos ativos (apenas status "Ativo")
            if 'contrato' in table_names:
                query = """
                    SELECT COUNT(*)
                    FROM contrato c
                    JOIN status s ON c.status_id = s.id
                    WHERE c.ativo = true AND s.nome = 'Ativo'
                """
                result = await self.conn.fetchval(query)
                contadores['contratos_ativos'] = result or 0

            # Total de contratações (todos os contratos não excluídos, independente do status)
            if 'contrato' in table_names:
                query = "SELECT COUNT(*) FROM contrato WHERE ativo = true"
                result = await self.conn.fetchval(query)
                contadores['total_contratacoes'] = result or 0

            # Contratados com pendências vencidas
            if all(table in table_names for table in ['contrato', 'contratado', 'pendenciarelatorio', 'statuspendencia']):
                query = """
                    SELECT COUNT(DISTINCT ct.id)
                    FROM contratado ct
                    JOIN contrato c ON ct.id = c.contratado_id
                    JOIN pendenciarelatorio p ON c.id = p.contrato_id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE c.ativo = true
                    AND sp.nome = 'Pendente'
                    AND p.data_prazo < CURRENT_DATE
                """
                result = await self.conn.fetchval(query)
                contadores['contratados_com_pendencias_vencidas'] = result or 0

            return contadores

        except Exception as e:
            print(f"Erro ao buscar contadores admin: {e}. Retornando contadores zerados.")
            return {
                'relatorios_para_analise': 0,
                'contratos_com_pendencias': 0,
                'usuarios_ativos': 0,
                'contratos_ativos': 0,
                'total_contratacoes': 0,
                'contratados_com_pendencias_vencidas': 0,
                'minhas_pendencias': 0,
                'pendencias_em_atraso': 0,
                'relatorios_enviados_mes': 0,
                'contratos_sob_gestao': 0,
                'relatorios_equipe_pendentes': 0
            }

    async def get_contadores_fiscal(self, fiscal_id: int) -> Dict[str, int]:
        """
        Busca contadores para o dashboard do fiscal
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('pendenciarelatorio', 'contrato', 'statuspendencia', 'relatoriofiscal')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            contadores = {
                'minhas_pendencias': 0,
                'pendencias_em_atraso': 0,
                'relatorios_enviados_mes': 0,
                'contratos_ativos': 0
            }

            # Minhas pendências
            if all(table in table_names for table in ['pendenciarelatorio', 'contrato', 'statuspendencia']):
                query = """
                    SELECT COUNT(*)
                    FROM pendenciarelatorio p
                    JOIN contrato c ON p.contrato_id = c.id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE c.fiscal_id = $1 AND c.ativo = true AND sp.nome = 'Pendente'
                """
                result = await self.conn.fetchval(query, fiscal_id)
                contadores['minhas_pendencias'] = result or 0

            # Pendências em atraso
            if all(table in table_names for table in ['pendenciarelatorio', 'contrato', 'statuspendencia']):
                query = """
                    SELECT COUNT(*)
                    FROM pendenciarelatorio p
                    JOIN contrato c ON p.contrato_id = c.id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE c.fiscal_id = $1
                        AND c.ativo = true
                        AND sp.nome = 'Pendente'
                        AND p.data_prazo IS NOT NULL
                        AND p.data_prazo < CURRENT_DATE
                """
                result = await self.conn.fetchval(query, fiscal_id)
                contadores['pendencias_em_atraso'] = result or 0

            # Relatórios enviados no mês
            if all(table in table_names for table in ['relatoriofiscal', 'contrato']):
                query = """
                    SELECT COUNT(*)
                    FROM relatoriofiscal r
                    JOIN contrato c ON r.contrato_id = c.id
                    WHERE r.fiscal_usuario_id = $1
                        AND c.ativo = true
                        AND EXTRACT(MONTH FROM r.created_at) = EXTRACT(MONTH FROM CURRENT_DATE)
                        AND EXTRACT(YEAR FROM r.created_at) = EXTRACT(YEAR FROM CURRENT_DATE)
                """
                result = await self.conn.fetchval(query, fiscal_id)
                contadores['relatorios_enviados_mes'] = result or 0

            # Contratos ativos do fiscal
            if 'contrato' in table_names:
                query = """
                    SELECT COUNT(*)
                    FROM contrato c
                    WHERE (c.fiscal_id = $1 OR c.fiscal_substituto_id = $1)
                        AND c.ativo = true
                """
                result = await self.conn.fetchval(query, fiscal_id)
                contadores['contratos_ativos'] = result or 0

            return contadores

        except Exception as e:
            print(f"Erro ao buscar contadores fiscal: {e}. Retornando contadores zerados.")
            return {
                'minhas_pendencias': 0,
                'pendencias_em_atraso': 0,
                'relatorios_enviados_mes': 0,
                'contratos_ativos': 0
            }

    async def get_pendencias_vencidas_admin(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Busca todas as pendências vencidas do sistema para o administrador
        com informações detalhadas e classificação de urgência
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('pendenciarelatorio', 'contrato', 'usuario', 'statuspendencia')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['pendenciarelatorio', 'contrato', 'usuario', 'statuspendencia']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando lista vazia.")
                return []

            query = """
            SELECT
                p.id as pendencia_id,
                p.descricao,
                p.created_at,
                p.data_prazo,
                (CURRENT_DATE - p.data_prazo)::int as dias_em_atraso,

                -- Informações do contrato
                c.id as contrato_id,
                c.nr_contrato as contrato_numero,
                c.objeto as contrato_objeto,

                -- Responsáveis
                u_fiscal.nome as fiscal_nome,
                u_gestor.nome as gestor_nome,

                -- Classificação de urgência baseada nos dias em atraso
                CASE
                    WHEN (CURRENT_DATE - p.data_prazo) > 30 THEN 'CRÍTICA'
                    WHEN (CURRENT_DATE - p.data_prazo) BETWEEN 15 AND 30 THEN 'ALTA'
                    ELSE 'MÉDIA'
                END as urgencia

            FROM pendenciarelatorio p
            JOIN contrato c ON p.contrato_id = c.id
            JOIN usuario u_fiscal ON c.fiscal_id = u_fiscal.id
            JOIN usuario u_gestor ON c.gestor_id = u_gestor.id
            JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
            WHERE
                c.ativo = true
                AND sp.nome = 'Pendente'
                AND p.data_prazo IS NOT NULL
                AND p.data_prazo < CURRENT_DATE
            ORDER BY
                -- Ordena por urgência (críticas primeiro) e depois por dias em atraso (maior primeiro)
                CASE
                    WHEN (CURRENT_DATE - p.data_prazo) > 30 THEN 1
                    WHEN (CURRENT_DATE - p.data_prazo) BETWEEN 15 AND 30 THEN 2
                    ELSE 3
                END,
                (CURRENT_DATE - p.data_prazo) DESC
            LIMIT $1
            """
            rows = await self.conn.fetch(query, limit)
            return [dict(row) for row in rows]

        except Exception as e:
            print(f"Erro ao buscar pendências vencidas: {e}. Retornando lista vazia.")
            return []

    async def get_estatisticas_pendencias_vencidas(self) -> Dict[str, int]:
        """
        Busca estatísticas das pendências vencidas para o dashboard do administrador
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('pendenciarelatorio', 'contrato', 'statuspendencia')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['pendenciarelatorio', 'contrato', 'statuspendencia']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando estatísticas zeradas.")
                return {
                    'total_pendencias_vencidas': 0,
                    'contratos_afetados': 0,
                    'pendencias_criticas': 0,
                    'pendencias_altas': 0,
                    'pendencias_medias': 0
                }

            query = """
            SELECT
                COALESCE(COUNT(*), 0) as total_pendencias_vencidas,
                COALESCE(COUNT(DISTINCT c.id), 0) as contratos_afetados,
                COALESCE(COUNT(*) FILTER (WHERE (CURRENT_DATE - p.data_prazo) > 30), 0) as pendencias_criticas,
                COALESCE(COUNT(*) FILTER (WHERE (CURRENT_DATE - p.data_prazo) BETWEEN 15 AND 30), 0) as pendencias_altas,
                COALESCE(COUNT(*) FILTER (WHERE (CURRENT_DATE - p.data_prazo) BETWEEN 1 AND 14), 0) as pendencias_medias
            FROM pendenciarelatorio p
            JOIN contrato c ON p.contrato_id = c.id
            JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
            WHERE
                c.ativo = true
                AND sp.nome = 'Pendente'
                AND p.data_prazo IS NOT NULL
                AND p.data_prazo < CURRENT_DATE
            """
            result = await self.conn.fetchrow(query)
            return dict(result) if result else {
                'total_pendencias_vencidas': 0,
                'contratos_afetados': 0,
                'pendencias_criticas': 0,
                'pendencias_altas': 0,
                'pendencias_medias': 0
            }

        except Exception as e:
            print(f"Erro ao buscar estatísticas de pendências vencidas: {e}. Retornando estatísticas zeradas.")
            return {
                'total_pendencias_vencidas': 0,
                'contratos_afetados': 0,
                'pendencias_criticas': 0,
                'pendencias_altas': 0,
                'pendencias_medias': 0
            }

    async def get_contadores_gestor(self, gestor_id: int) -> Dict[str, int]:
        """
        Busca contadores para o dashboard do gestor
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('contrato', 'relatoriofiscal', 'statusrelatorio')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            contadores = {
                'contratos_sob_gestao': 0,
                'contratos_ativos_sob_gestao': 0,
                'relatorios_equipe_pendentes': 0
            }

            # Contratos sob gestão (todos os contratos ativos, independente do status)
            if 'contrato' in table_names:
                # Total de contratos do gestor
                query_total = """
                    SELECT COUNT(*)
                    FROM contrato c
                    WHERE c.gestor_id = $1 AND c.ativo = true
                """
                result_total = await self.conn.fetchval(query_total, gestor_id)
                contadores['contratos_sob_gestao'] = result_total or 0

                # Contratos com status "Ativo" do gestor
                query_ativos = """
                    SELECT COUNT(*)
                    FROM contrato c
                    JOIN status s ON c.status_id = s.id
                    WHERE c.gestor_id = $1 AND c.ativo = true AND s.nome = 'Ativo'
                """
                result_ativos = await self.conn.fetchval(query_ativos, gestor_id)
                contadores['contratos_ativos_sob_gestao'] = result_ativos or 0

            # Relatórios da equipe pendentes
            if all(table in table_names for table in ['relatoriofiscal', 'contrato', 'statusrelatorio']):
                query = """
                    SELECT COUNT(*)
                    FROM relatoriofiscal r
                    JOIN contrato c ON r.contrato_id = c.id
                    JOIN statusrelatorio sr ON r.status_id = sr.id
                    WHERE c.gestor_id = $1
                        AND c.ativo = true
                        AND sr.nome = 'Pendente de Análise'
                """
                result = await self.conn.fetchval(query, gestor_id)
                contadores['relatorios_equipe_pendentes'] = result or 0

            return contadores

        except Exception as e:
            print(f"Erro ao buscar contadores gestor: {e}. Retornando contadores zerados.")
            return {
                'contratos_sob_gestao': 0,
                'relatorios_equipe_pendentes': 0
            }

    async def get_pendencias_gestor(self, gestor_id: int) -> List[Dict[str, Any]]:
        """
        Busca todas as pendências dos contratos gerenciados pelo gestor
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('pendenciarelatorio', 'contrato', 'statuspendencia', 'usuario')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['pendenciarelatorio', 'contrato', 'statuspendencia', 'usuario']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando lista vazia.")
                return []

            query = """
            SELECT
                p.id as pendencia_id,
                p.descricao,
                p.created_at,
                p.data_prazo,
                sp.nome as status_pendencia,

                -- Informações do contrato
                c.id as contrato_id,
                c.nr_contrato as contrato_numero,
                c.objeto as contrato_objeto,

                -- Fiscal responsável
                u_fiscal.nome as fiscal_nome,
                u_fiscal.email as fiscal_email,

                -- Status da pendência
                CASE
                    WHEN p.data_prazo IS NOT NULL AND p.data_prazo < CURRENT_DATE AND sp.nome = 'Pendente'
                    THEN 'vencida'
                    WHEN sp.nome = 'Pendente'
                    THEN 'pendente'
                    WHEN sp.nome = 'Concluída'
                    THEN 'concluida'
                    WHEN sp.nome = 'Cancelada'
                    THEN 'cancelada'
                    ELSE 'indefinido'
                END as status_classificacao,

                -- Dias restantes/vencidos
                CASE
                    WHEN p.data_prazo IS NOT NULL AND p.data_prazo < CURRENT_DATE
                    THEN (CURRENT_DATE - p.data_prazo)::int
                    WHEN p.data_prazo IS NOT NULL
                    THEN (p.data_prazo - CURRENT_DATE)::int
                    ELSE NULL
                END as dias_diferenca

            FROM pendenciarelatorio p
            JOIN contrato c ON p.contrato_id = c.id
            JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
            JOIN usuario u_fiscal ON c.fiscal_id = u_fiscal.id
            WHERE
                c.gestor_id = $1
                AND c.ativo = true
            ORDER BY
                -- Ordena por: vencidas primeiro, depois por data de prazo
                CASE
                    WHEN p.data_prazo IS NOT NULL AND p.data_prazo < CURRENT_DATE AND sp.nome = 'Pendente' THEN 1
                    WHEN sp.nome = 'Pendente' THEN 2
                    WHEN sp.nome = 'Concluída' THEN 3
                    ELSE 4
                END,
                p.data_prazo ASC NULLS LAST,
                p.created_at DESC
            """
            rows = await self.conn.fetch(query, gestor_id)
            return [dict(row) for row in rows]

        except Exception as e:
            print(f"Erro ao buscar pendências do gestor: {e}. Retornando lista vazia.")
            return []

    # ===== NOVOS MÉTODOS PARA DASHBOARDS MELHORADOS =====

    async def get_dashboard_admin_completo(self) -> Dict[str, Any]:
        """
        Busca métricas completas para o dashboard do administrador
        """
        try:
            # Verificar tabelas existentes
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('contrato', 'pendenciarelatorio', 'relatoriofiscal', 'usuario', 'statusrelatorio', 'statuspendencia')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            metrics = {
                'contratos_com_pendencias': 0,
                'contratos_ativos': 0,
                'relatorios_para_analise': 0,
                'total_contratacoes': 0,
                'usuarios_ativos_30_dias': 0,
                'fiscais_maior_carga': []
            }

            # 1. Contratos com pendências ativas
            if all(table in table_names for table in ['contrato', 'pendenciarelatorio', 'statuspendencia']):
                query = """
                    SELECT COUNT(DISTINCT c.id)
                    FROM contrato c
                    JOIN pendenciarelatorio p ON c.id = p.contrato_id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE c.ativo = true AND sp.nome = 'Pendente'
                """
                result = await self.conn.fetchval(query)
                metrics['contratos_com_pendencias'] = result or 0

            # 2. Contratos ativos (apenas status "Ativo")
            if 'contrato' in table_names:
                query = """
                    SELECT COUNT(*)
                    FROM contrato c
                    JOIN status s ON c.status_id = s.id
                    WHERE c.ativo = true AND s.nome = 'Ativo'
                """
                result = await self.conn.fetchval(query)
                metrics['contratos_ativos'] = result or 0

            # 3. Relatórios para análise
            if all(table in table_names for table in ['relatoriofiscal', 'statusrelatorio']):
                query = """
                    SELECT COUNT(*)
                    FROM relatoriofiscal r
                    JOIN statusrelatorio sr ON r.status_id = sr.id
                    WHERE sr.nome = 'Pendente de Análise'
                """
                result = await self.conn.fetchval(query)
                metrics['relatorios_para_analise'] = result or 0

            # 4. Total de contratações (todos os contratos não excluídos)
            if 'contrato' in table_names:
                query = "SELECT COUNT(*) FROM contrato WHERE ativo = true"
                result = await self.conn.fetchval(query)
                metrics['total_contratacoes'] = result or 0

            # 5. Usuários ativos nos últimos 30 dias
            if 'usuario' in table_names:
                query = """
                    SELECT COUNT(*)
                    FROM usuario
                    WHERE ultimo_login >= (CURRENT_DATE - INTERVAL '30 days')
                    AND ativo = true
                """
                result = await self.conn.fetchval(query)
                metrics['usuarios_ativos_30_dias'] = result or 0

            # 6. Fiscais com maior carga de trabalho (top 5)
            if all(table in table_names for table in ['usuario', 'contrato', 'pendenciarelatorio', 'statuspendencia']):
                query = """
                    SELECT
                        u.id as fiscal_id,
                        u.nome as fiscal_nome,
                        u.email as fiscal_email,
                        COUNT(p.id) as total_pendencias,
                        COUNT(CASE WHEN p.data_prazo < CURRENT_DATE THEN 1 END) as pendencias_vencidas,
                        COUNT(DISTINCT c.id) as contratos_ativos
                    FROM usuario u
                    LEFT JOIN contrato c ON u.id = c.fiscal_id AND c.ativo = true
                    LEFT JOIN pendenciarelatorio p ON c.id = p.contrato_id
                    LEFT JOIN statuspendencia sp ON p.status_pendencia_id = sp.id AND sp.nome = 'Pendente'
                    WHERE u.ativo = true
                    GROUP BY u.id, u.nome, u.email
                    HAVING COUNT(p.id) > 0
                    ORDER BY total_pendencias DESC, pendencias_vencidas DESC
                    LIMIT 5
                """
                rows = await self.conn.fetch(query)
                metrics['fiscais_maior_carga'] = [dict(row) for row in rows]

            return metrics

        except Exception as e:
            print(f"Erro ao buscar dashboard admin completo: {e}. Retornando métricas zeradas.")
            return {
                'contratos_com_pendencias': 0,
                'contratos_ativos': 0,
                'relatorios_para_analise': 0,
                'total_contratacoes': 0,
                'usuarios_ativos_30_dias': 0,
                'fiscais_maior_carga': []
            }

    async def get_all_relatorios_pendentes_analise(self) -> List[Dict[str, Any]]:
        """
        Busca todos os relatórios individuais com status 'Pendente de Análise' do sistema
        """
        try:
            # Verificar se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('relatoriofiscal', 'contrato', 'contratado', 'usuario', 'statusrelatorio', 'arquivo', 'pendenciarelatorio')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['relatoriofiscal', 'contrato', 'contratado', 'usuario', 'statusrelatorio']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando lista vazia.")
                return []

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
                COALESCE(a.nome_arquivo, 'relatorio.pdf') as arquivo_nome,
                COALESCE(p.descricao, 'Relatório Fiscal') as pendencia_titulo,
                s.nome as status_relatorio
            FROM relatoriofiscal rf
            JOIN contrato c ON rf.contrato_id = c.id
            JOIN contratado ct ON c.contratado_id = ct.id
            JOIN usuario u_fiscal ON rf.fiscal_usuario_id = u_fiscal.id
            JOIN usuario u_gestor ON c.gestor_id = u_gestor.id
            JOIN statusrelatorio s ON rf.status_id = s.id
            LEFT JOIN arquivo a ON rf.arquivo_id = a.id
            LEFT JOIN pendenciarelatorio p ON rf.pendencia_id = p.id
            WHERE c.ativo = true AND s.nome = 'Pendente de Análise'
            ORDER BY rf.created_at ASC
            """
            records = await self.conn.fetch(query)
            return [dict(r) for r in records]

        except Exception as e:
            print(f"Erro ao buscar relatórios pendentes de análise: {e}. Retornando lista vazia.")
            return []

    async def get_dashboard_fiscal_completo(self, fiscal_id: int) -> Dict[str, Any]:
        """
        Busca métricas completas para o dashboard do fiscal
        """
        try:
            # Verificar tabelas existentes
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('contrato', 'pendenciarelatorio', 'relatoriofiscal', 'statusrelatorio', 'statuspendencia')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            metrics = {
                'minhas_pendencias': 0,
                'pendencias_em_atraso': 0,
                'relatorios_enviados': 0,
                'contratos_ativos': 0,
                'pendencias_proximas_vencimento': 0,
                'relatorios_rejeitados': 0
            }

            # 1. Minhas pendências (ativas)
            # Inclui contratos onde o usuário é fiscal titular OU fiscal substituto
            if all(table in table_names for table in ['contrato', 'pendenciarelatorio', 'statuspendencia']):
                query = """
                    SELECT COUNT(*)
                    FROM pendenciarelatorio p
                    JOIN contrato c ON p.contrato_id = c.id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE (c.fiscal_id = $1 OR c.fiscal_substituto_id = $1)
                    AND c.ativo = true AND sp.nome = 'Pendente'
                """
                result = await self.conn.fetchval(query, fiscal_id)
                metrics['minhas_pendencias'] = result or 0

            # 2. Pendências em atraso
            if all(table in table_names for table in ['contrato', 'pendenciarelatorio', 'statuspendencia']):
                query = """
                    SELECT COUNT(*)
                    FROM pendenciarelatorio p
                    JOIN contrato c ON p.contrato_id = c.id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE (c.fiscal_id = $1 OR c.fiscal_substituto_id = $1) AND c.ativo = true
                    AND sp.nome = 'Pendente' AND p.data_prazo < CURRENT_DATE
                """
                result = await self.conn.fetchval(query, fiscal_id)
                metrics['pendencias_em_atraso'] = result or 0

            # 3. Relatórios enviados (total histórico)
            if all(table in table_names for table in ['contrato', 'relatoriofiscal']):
                query = """
                    SELECT COUNT(*)
                    FROM relatoriofiscal r
                    JOIN contrato c ON r.contrato_id = c.id
                    WHERE (c.fiscal_id = $1 OR c.fiscal_substituto_id = $1)
                """
                result = await self.conn.fetchval(query, fiscal_id)
                metrics['relatorios_enviados'] = result or 0

            # 4. Contratos ativos onde sou fiscal titular ou substituto (apenas status "Ativo")
            if 'contrato' in table_names:
                query = """
                    SELECT COUNT(*)
                    FROM contrato c
                    JOIN status s ON c.status_id = s.id
                    WHERE (c.fiscal_id = $1 OR c.fiscal_substituto_id = $1)
                    AND c.ativo = true AND s.nome = 'Ativo'
                """
                result = await self.conn.fetchval(query, fiscal_id)
                metrics['contratos_ativos'] = result or 0

            # 5. Pendências próximas do vencimento (próximos 7 dias)
            if all(table in table_names for table in ['contrato', 'pendenciarelatorio', 'statuspendencia']):
                query = """
                    SELECT COUNT(*)
                    FROM pendenciarelatorio p
                    JOIN contrato c ON p.contrato_id = c.id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE (c.fiscal_id = $1 OR c.fiscal_substituto_id = $1) AND c.ativo = true
                    AND sp.nome = 'Pendente'
                    AND p.data_prazo BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL '7 days')
                """
                result = await self.conn.fetchval(query, fiscal_id)
                metrics['pendencias_proximas_vencimento'] = result or 0

            # 6. Relatórios rejeitados (precisam reenvio)
            if all(table in table_names for table in ['contrato', 'relatoriofiscal', 'statusrelatorio']):
                query = """
                    SELECT COUNT(*)
                    FROM relatoriofiscal r
                    JOIN contrato c ON r.contrato_id = c.id
                    JOIN statusrelatorio sr ON r.status_id = sr.id
                    WHERE (c.fiscal_id = $1 OR c.fiscal_substituto_id = $1)
                    AND sr.nome = 'Rejeitado com Pendência'
                """
                result = await self.conn.fetchval(query, fiscal_id)
                metrics['relatorios_rejeitados'] = result or 0

            return metrics

        except Exception as e:
            print(f"Erro ao buscar dashboard fiscal completo: {e}. Retornando métricas zeradas.")
            return {
                'minhas_pendencias': 0,
                'pendencias_em_atraso': 0,
                'relatorios_enviados': 0,
                'contratos_ativos': 0,
                'pendencias_proximas_vencimento': 0,
                'relatorios_rejeitados': 0
            }

    async def get_dashboard_gestor_completo(self, gestor_id: int) -> Dict[str, Any]:
        """
        Busca métricas completas para o dashboard do gestor
        """
        try:
            # Verificar tabelas existentes
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('contrato', 'pendenciarelatorio', 'relatoriofiscal', 'usuario', 'statusrelatorio', 'statuspendencia')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            metrics = {
                'contratos_sob_gestao': 0,
                'contratos_ativos_sob_gestao': 0,
                'equipe_pendencias_atraso': 0,
                'relatorios_equipe_aguardando': 0,
                'performance_equipe': {
                    'total_fiscais': 0,
                    'fiscais_com_atraso': 0,
                    'taxa_cumprimento_prazos': 0.0,
                    'pendencias_vencidas_equipe': 0
                },
                'contratos_proximos_vencimento': []
            }

            # 1. Contratos sob gestão (todos os contratos ativos, independente do status)
            if 'contrato' in table_names:
                # Total de contratos do gestor
                query_total = """
                    SELECT COUNT(*)
                    FROM contrato c
                    WHERE c.gestor_id = $1 AND c.ativo = true
                """
                result_total = await self.conn.fetchval(query_total, gestor_id)
                metrics['contratos_sob_gestao'] = result_total or 0

                # Contratos com status "Ativo" do gestor
                query_ativos = """
                    SELECT COUNT(*)
                    FROM contrato c
                    JOIN status s ON c.status_id = s.id
                    WHERE c.gestor_id = $1 AND c.ativo = true AND s.nome = 'Ativo'
                """
                result_ativos = await self.conn.fetchval(query_ativos, gestor_id)
                metrics['contratos_ativos_sob_gestao'] = result_ativos or 0

            # 2. Equipe com pendências em atraso
            if all(table in table_names for table in ['contrato', 'pendenciarelatorio', 'statuspendencia']):
                query = """
                    SELECT COUNT(DISTINCT c.fiscal_id)
                    FROM contrato c
                    JOIN pendenciarelatorio p ON c.id = p.contrato_id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE c.gestor_id = $1 AND c.ativo = true
                    AND sp.nome = 'Pendente' AND p.data_prazo < CURRENT_DATE
                """
                result = await self.conn.fetchval(query, gestor_id)
                metrics['equipe_pendencias_atraso'] = result or 0

            # 3. Relatórios da equipe aguardando análise
            if all(table in table_names for table in ['contrato', 'relatoriofiscal', 'statusrelatorio']):
                query = """
                    SELECT COUNT(*)
                    FROM relatoriofiscal r
                    JOIN contrato c ON r.contrato_id = c.id
                    JOIN statusrelatorio sr ON r.status_id = sr.id
                    WHERE c.gestor_id = $1 AND c.ativo = true
                    AND sr.nome = 'Pendente de Análise'
                """
                result = await self.conn.fetchval(query, gestor_id)
                metrics['relatorios_equipe_aguardando'] = result or 0

            # 4. Performance da equipe
            if all(table in table_names for table in ['contrato', 'pendenciarelatorio', 'statuspendencia', 'usuario']):
                # Total de fiscais na equipe
                query = """
                    SELECT COUNT(DISTINCT c.fiscal_id)
                    FROM contrato c
                    WHERE c.gestor_id = $1 AND c.ativo = true
                """
                total_fiscais = await self.conn.fetchval(query, gestor_id) or 0
                metrics['performance_equipe']['total_fiscais'] = total_fiscais

                # Fiscais com pendências vencidas
                query = """
                    SELECT COUNT(DISTINCT c.fiscal_id)
                    FROM contrato c
                    JOIN pendenciarelatorio p ON c.id = p.contrato_id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE c.gestor_id = $1 AND c.ativo = true
                    AND sp.nome = 'Pendente' AND p.data_prazo < CURRENT_DATE
                """
                fiscais_com_atraso = await self.conn.fetchval(query, gestor_id) or 0
                metrics['performance_equipe']['fiscais_com_atraso'] = fiscais_com_atraso

                # Total de pendências vencidas da equipe
                query = """
                    SELECT COUNT(*)
                    FROM contrato c
                    JOIN pendenciarelatorio p ON c.id = p.contrato_id
                    JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
                    WHERE c.gestor_id = $1 AND c.ativo = true
                    AND sp.nome = 'Pendente' AND p.data_prazo < CURRENT_DATE
                """
                pendencias_vencidas = await self.conn.fetchval(query, gestor_id) or 0
                metrics['performance_equipe']['pendencias_vencidas_equipe'] = pendencias_vencidas

                # Taxa de cumprimento (fiscais sem atraso / total de fiscais)
                if total_fiscais > 0:
                    fiscais_em_dia = total_fiscais - fiscais_com_atraso
                    taxa = (fiscais_em_dia / total_fiscais) * 100
                    metrics['performance_equipe']['taxa_cumprimento_prazos'] = round(taxa, 2)

            # 5. Contratos próximos ao vencimento (próximos 30 dias)
            if all(table in table_names for table in ['contrato', 'usuario']):
                query = """
                    SELECT
                        c.id as contrato_id,
                        c.numero,
                        c.objeto,
                        c.data_fim,
                        (c.data_fim - CURRENT_DATE)::int as dias_restantes,
                        u.nome as fiscal_nome
                    FROM contrato c
                    JOIN usuario u ON c.fiscal_id = u.id
                    WHERE c.gestor_id = $1 AND c.ativo = true
                    AND c.data_fim BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL '30 days')
                    ORDER BY c.data_fim ASC
                    LIMIT 10
                """
                rows = await self.conn.fetch(query, gestor_id)
                metrics['contratos_proximos_vencimento'] = [dict(row) for row in rows]

            return metrics

        except Exception as e:
            print(f"Erro ao buscar dashboard gestor completo: {e}. Retornando métricas zeradas.")
            return {
                'contratos_sob_gestao': 0,
                'equipe_pendencias_atraso': 0,
                'relatorios_equipe_aguardando': 0,
                'performance_equipe': {
                    'total_fiscais': 0,
                    'fiscais_com_atraso': 0,
                    'taxa_cumprimento_prazos': 0.0,
                    'pendencias_vencidas_equipe': 0
                },
                'contratos_proximos_vencimento': []
            }

    async def get_pendencias_pendentes_admin(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Busca todas as pendências pendentes (não vencidas) do sistema para o administrador
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('pendenciarelatorio', 'contrato', 'usuario', 'statuspendencia')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['pendenciarelatorio', 'contrato', 'usuario', 'statuspendencia']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando lista vazia.")
                return []

            query = """
            SELECT
                p.id as pendencia_id,
                p.descricao,
                p.created_at,
                p.data_prazo,
                CASE
                    WHEN p.data_prazo IS NOT NULL
                    THEN (p.data_prazo - CURRENT_DATE)::int
                    ELSE NULL
                END as dias_restantes,

                -- Informações do contrato
                c.id as contrato_id,
                c.nr_contrato as contrato_numero,
                c.objeto as contrato_objeto,

                -- Responsáveis
                u_fiscal.nome as fiscal_nome,
                u_gestor.nome as gestor_nome

            FROM pendenciarelatorio p
            JOIN contrato c ON p.contrato_id = c.id
            JOIN usuario u_fiscal ON c.fiscal_id = u_fiscal.id
            JOIN usuario u_gestor ON c.gestor_id = u_gestor.id
            JOIN statuspendencia sp ON p.status_pendencia_id = sp.id
            WHERE
                c.ativo = true
                AND sp.nome = 'Pendente'
                AND (p.data_prazo IS NULL OR p.data_prazo >= CURRENT_DATE)
            ORDER BY
                -- Ordena por prazo (mais próximos primeiro)
                p.data_prazo ASC NULLS LAST,
                p.created_at DESC
            LIMIT $1
            """
            rows = await self.conn.fetch(query, limit)
            return [dict(row) for row in rows]

        except Exception as e:
            print(f"Erro ao buscar pendências pendentes: {e}. Retornando lista vazia.")
            return []

    async def get_contratos_proximos_vencimento_admin(self, dias_antecedencia: int = 90) -> List[Dict[str, Any]]:
        """
        Busca contratos que estão próximos ao vencimento (dentro do prazo especificado)
        Para o dashboard do administrador
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('contrato', 'contratado', 'usuario', 'status')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['contrato', 'contratado', 'usuario', 'status']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando lista vazia.")
                return []

            query = """
            SELECT
                c.id as contrato_id,
                c.nr_contrato as contrato_numero,
                c.objeto as contrato_objeto,
                c.data_inicio,
                c.data_fim,
                (c.data_fim - CURRENT_DATE)::int as dias_para_vencer,
                
                -- Informações do contratado
                ct.nome as contratado_nome,
                ct.cnpj as contratado_cnpj,
                
                -- Responsáveis
                u_fiscal.nome as fiscal_nome,
                u_fiscal.email as fiscal_email,
                u_gestor.nome as gestor_nome,
                u_gestor.email as gestor_email,
                
                -- Status do contrato
                s.nome as status_nome,
                
                -- Classificação de urgência baseada nos dias restantes
                CASE
                    WHEN (c.data_fim - CURRENT_DATE) <= 30 THEN 'CRÍTICO'
                    WHEN (c.data_fim - CURRENT_DATE) <= 60 THEN 'ALTO'
                    WHEN (c.data_fim - CURRENT_DATE) <= 90 THEN 'MÉDIO'
                    ELSE 'BAIXO'
                END as nivel_urgencia,
                
                -- Valor do contrato para priorização
                c.valor_global,
                c.valor_anual

            FROM contrato c
            JOIN contratado ct ON c.contratado_id = ct.id
            JOIN usuario u_fiscal ON c.fiscal_id = u_fiscal.id
            JOIN usuario u_gestor ON c.gestor_id = u_gestor.id
            JOIN status s ON c.status_id = s.id
            WHERE
                c.ativo = true
                AND s.nome = 'Ativo'  -- Apenas contratos ativos
                AND c.data_fim IS NOT NULL
                AND c.data_fim > CURRENT_DATE  -- Ainda não venceu
                AND c.data_fim <= (CURRENT_DATE + INTERVAL '%s days')  -- Dentro do prazo de antecedência
            ORDER BY
                -- Ordena por urgência (mais próximos primeiro) e depois por valor (maiores primeiro)
                CASE
                    WHEN (c.data_fim - CURRENT_DATE) <= 30 THEN 1
                    WHEN (c.data_fim - CURRENT_DATE) <= 60 THEN 2
                    WHEN (c.data_fim - CURRENT_DATE) <= 90 THEN 3
                    ELSE 4
                END,
                c.data_fim ASC,
                COALESCE(c.valor_global, c.valor_anual, 0) DESC
            """ % dias_antecedencia
            
            rows = await self.conn.fetch(query)
            return [dict(row) for row in rows]

        except Exception as e:
            print(f"Erro ao buscar contratos próximos ao vencimento: {e}. Retornando lista vazia.")
            return []

    async def get_estatisticas_contratos_vencimento(self) -> Dict[str, int]:
        """
        Busca estatísticas dos contratos próximos ao vencimento para o dashboard do administrador
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('contrato', 'status')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['contrato', 'status']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando estatísticas zeradas.")
                return {
                    'total_proximos_vencimento': 0,
                    'criticos_30_dias': 0,
                    'altos_60_dias': 0,
                    'medios_90_dias': 0
                }

            query = """
            SELECT
                COALESCE(COUNT(*), 0) as total_proximos_vencimento,
                COALESCE(COUNT(*) FILTER (WHERE (c.data_fim - CURRENT_DATE) <= 30), 0) as criticos_30_dias,
                COALESCE(COUNT(*) FILTER (WHERE (c.data_fim - CURRENT_DATE) BETWEEN 31 AND 60), 0) as altos_60_dias,
                COALESCE(COUNT(*) FILTER (WHERE (c.data_fim - CURRENT_DATE) BETWEEN 61 AND 90), 0) as medios_90_dias
            FROM contrato c
            JOIN status s ON c.status_id = s.id
            WHERE
                c.ativo = true
                AND s.nome = 'Ativo'
                AND c.data_fim IS NOT NULL
                AND c.data_fim > CURRENT_DATE
                AND c.data_fim <= (CURRENT_DATE + INTERVAL '90 days')
            """
            result = await self.conn.fetchrow(query)
            return dict(result) if result else {
                'total_proximos_vencimento': 0,
                'criticos_30_dias': 0,
                'altos_60_dias': 0,
                'medios_90_dias': 0
            }

        except Exception as e:
            print(f"Erro ao buscar estatísticas de contratos próximos ao vencimento: {e}. Retornando estatísticas zeradas.")
            return {
                'total_proximos_vencimento': 0,
                'criticos_30_dias': 0,
                'altos_60_dias': 0,
                'medios_90_dias': 0
            }

    async def get_garantias_proximas_vencimento_admin(self, dias_antecedencia: int = 90) -> List[Dict[str, Any]]:
        """
        Busca contratos com garantias próximas ao vencimento (dentro do prazo especificado)
        Para envio de alertas aos administradores
        """
        try:
            # Primeiro verifica se as tabelas existem
            check_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('contrato', 'contratado', 'usuario', 'status')
            """
            existing_tables = await self.conn.fetch(check_query)
            table_names = [row['table_name'] for row in existing_tables]

            required_tables = ['contrato', 'contratado', 'usuario', 'status']
            missing_tables = [table for table in required_tables if table not in table_names]

            if missing_tables:
                print(f"Tabelas não encontradas: {missing_tables}. Retornando lista vazia.")
                return []

            query = """
            SELECT
                c.id as contrato_id,
                c.nr_contrato as contrato_numero,
                c.objeto as contrato_objeto,
                c.data_inicio,
                c.garantia as data_garantia,
                (c.garantia - CURRENT_DATE)::int as dias_para_vencer,

                -- Informações do contratado
                ct.nome as contratado_nome,
                ct.cnpj as contratado_cnpj,

                -- Responsáveis
                u_fiscal.nome as fiscal_nome,
                u_fiscal.email as fiscal_email,
                u_gestor.nome as gestor_nome,
                u_gestor.email as gestor_email,

                -- Status do contrato
                s.nome as status_nome,

                -- Classificação de urgência baseada nos dias restantes
                CASE
                    WHEN (c.garantia - CURRENT_DATE) <= 30 THEN 'CRÍTICO'
                    WHEN (c.garantia - CURRENT_DATE) <= 60 THEN 'ALTO'
                    WHEN (c.garantia - CURRENT_DATE) <= 90 THEN 'MÉDIO'
                    ELSE 'BAIXO'
                END as nivel_urgencia,

                -- Valor do contrato para priorização
                c.valor_global,
                c.valor_anual

            FROM contrato c
            JOIN contratado ct ON c.contratado_id = ct.id
            JOIN usuario u_fiscal ON c.fiscal_id = u_fiscal.id
            JOIN usuario u_gestor ON c.gestor_id = u_gestor.id
            JOIN status s ON c.status_id = s.id
            WHERE
                c.ativo = true
                AND s.nome = 'Ativo'  -- Apenas contratos ativos
                AND c.garantia IS NOT NULL
                AND c.garantia > CURRENT_DATE  -- Ainda não venceu
                AND c.garantia <= (CURRENT_DATE + INTERVAL '%s days')  -- Dentro do prazo de antecedência
            ORDER BY
                -- Ordena por urgência (mais próximos primeiro) e depois por valor (maiores primeiro)
                CASE
                    WHEN (c.garantia - CURRENT_DATE) <= 30 THEN 1
                    WHEN (c.garantia - CURRENT_DATE) <= 60 THEN 2
                    WHEN (c.garantia - CURRENT_DATE) <= 90 THEN 3
                    ELSE 4
                END,
                c.garantia ASC,
                COALESCE(c.valor_global, c.valor_anual, 0) DESC
            """ % dias_antecedencia

            rows = await self.conn.fetch(query)
            return [dict(row) for row in rows]

        except Exception as e:
            print(f"Erro ao buscar garantias próximas ao vencimento: {e}. Retornando lista vazia.")
            return []