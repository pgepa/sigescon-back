# app/core/migration.py
import logging
from pathlib import Path
from alembic.config import Config
from alembic import command

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """
    Executa automaticamente as migrações pendentes do banco de dados (alembic upgrade head).
    Executado no startup da aplicação (lifespan do FastAPI) para garantir que ambientes
    de desenvolvimento, homologação e produção estejam sempre na versão mais recente.
    """
    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        ini_path = project_root / "alembic.ini"

        if not ini_path.exists():
            logger.warning(f"Arquivo alembic.ini não encontrado em {ini_path}. Pulando migrações automáticas.")
            return

        print("🔄 [Alembic] Verificando e aplicando migrações automáticas do banco de dados...")
        alembic_cfg = Config(str(ini_path))
        alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))

        command.upgrade(alembic_cfg, "head")
        print("✅ [Alembic] Migrações do banco de dados verificadas e atualizadas com sucesso!")
    except Exception as e:
        print(f"❌ [Alembic] Erro ao executar migrações do banco de dados: {e}")
        logger.error(f"Erro ao executar migrações do Alembic: {e}", exc_info=True)
        raise
