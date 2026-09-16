# app/services/sincronizacao_retroativa_service.py
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import asyncpg

from app.core.database import get_db_pool
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.termo_aditivo_repo import TermoAditivoRepository

logger = logging.getLogger(__name__)


class SincronizacaoRetroativaService:
    """
    Serviço do Robô Retroativo para varredura e sincronização em massa
    de toda a base de dados de contratos e termos aditivos conforme a Lei 14.133/2021.
    """

    @staticmethod
    async def executar(conn: Optional[asyncpg.Connection] = None) -> Dict[str, Any]:
        """
        Executa a sincronização retroativa de todos os registros do banco de dados:
        1. Assegura data_inicio_original e data_fim_original para contratos que ainda não possuem.
        2. Recalcula o status (Ativo, Aguardando Vigência, Vencido, Inativo) de TODOS os termos aditivos.
        3. Recalcula a vigência mandatória, status (Ativo, Encerrado) e valor consolidado de TODOS os contratos.
        """
        if conn is not None:
            return await SincronizacaoRetroativaService._executar_na_conexao(conn)

        pool = await get_db_pool()
        async with pool.acquire() as connection:
            return await SincronizacaoRetroativaService._executar_na_conexao(connection)

    @staticmethod
    async def _executar_na_conexao(conn: asyncpg.Connection) -> Dict[str, Any]:
        logger.info("🤖 Iniciando execução do Robô Retroativo de Sincronização...")
        inicio_proc = datetime.now()

        # 1. Assegurar preservação das datas originais em todos os contratos ativos
        res_datas_originais = await conn.execute(
            """
            UPDATE contrato
            SET 
                data_inicio_original = COALESCE(data_inicio_original, data_inicio),
                data_fim_original = COALESCE(data_fim_original, data_fim),
                updated_at = NOW()
            WHERE ativo = TRUE 
              AND (data_inicio_original IS NULL OR data_fim_original IS NULL)
            """
        )
        logger.info(f"Datas originais asseguradas: {res_datas_originais}")

        # 2. Sincronizar todos os termos aditivos
        termo_aditivo_repo = TermoAditivoRepository(conn)
        aditivos_atualizados = await termo_aditivo_repo.sincronizar_status_todos_aditivos()
        logger.info(f"Termos aditivos recalculados: {len(aditivos_atualizados)} atualizados.")

        # 3. Sincronizar todos os contratos
        contrato_repo = ContratoRepository(conn)
        contratos_atualizados = await contrato_repo.sincronizar_status_vencimento_geral()
        logger.info(f"Contratos recalculados: {len(contratos_atualizados)} atualizados.")

        # Contagem total para o relatório
        total_contratos = await conn.fetchval("SELECT COUNT(*) FROM contrato WHERE ativo = TRUE")
        total_aditivos = await conn.fetchval("SELECT COUNT(*) FROM termo_aditivo WHERE ativo = TRUE")

        fim_proc = datetime.now()
        duracao_ms = int((fim_proc - inicio_proc).total_seconds() * 1000)

        resultado = {
            "sucesso": True,
            "mensagem": "Sincronização retroativa executada com sucesso.",
            "total_contratos_ativos": total_contratos,
            "contratos_modificados": len(contratos_atualizados),
            "total_termos_aditivos_ativos": total_aditivos,
            "termos_aditivos_modificados": len(aditivos_atualizados),
            "tempo_execucao_ms": duracao_ms,
            "executado_em": fim_proc.isoformat()
        }

        logger.info(f"🤖 Robô Retroativo finalizado com sucesso: {resultado}")
        return resultado
