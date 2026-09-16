# app/scripts/sync_retroativo.py
"""
Script CLI para execução do Robô Retroativo de Sincronização de Contratos e Termos Aditivos.

Uso:
    python -m app.scripts.sync_retroativo
"""
import asyncio
import sys
import logging
from app.core.database import get_db_pool, close_db_pool
from app.services.sincronizacao_retroativa_service import SincronizacaoRetroativaService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sync_retroativo")


async def main():
    print("=" * 70)
    print("  SIGESCON - Robô Retroativo de Sincronização (Lei 14.133/2021)")
    print("=" * 70)
    try:
        resultado = await SincronizacaoRetroativaService.executar()
        print("\nResultado da Operação:")
        print(f" - Contratos Ativos no Banco: {resultado['total_contratos_ativos']}")
        print(f" - Contratos com Status/Vigência/Valor Atualizados: {resultado['contratos_modificados']}")
        print(f" - Termos Aditivos Ativos: {resultado['total_termos_aditivos_ativos']}")
        print(f" - Termos Aditivos Recalculados: {resultado['termos_aditivos_modificados']}")
        print(f" - Tempo de Execução: {resultado['tempo_execucao_ms']} ms")
        print(f" - Executado em: {resultado['executado_em']}")
        print("\n[OK] Sincronização retroativa concluída com sucesso!")
        print("=" * 70)
    except Exception as e:
        logger.error(f"Falha na execução do robô retroativo: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
