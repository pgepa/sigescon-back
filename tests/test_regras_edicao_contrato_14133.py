# tests/test_regras_edicao_contrato_14133.py
import pytest
import asyncio
import asyncpg
from datetime import date, timedelta
from fastapi import HTTPException

from app.core.config import settings
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.contratado_repo import ContratadoRepository
from app.repositories.modalidade_repo import ModalidadeRepository
from app.repositories.status_repo import StatusRepository
from app.repositories.usuario_repo import UsuarioRepository
from app.repositories.arquivo_repo import ArquivoRepository
from app.repositories.termo_aditivo_repo import TermoAditivoRepository
from app.repositories.tipo_termo_aditivo_repo import TipoTermoAditivoRepository
from app.services.file_service import FileService
from app.services.contrato_service import ContratoService
from app.services.termo_aditivo_service import TermoAditivoService
from app.services.sincronizacao_retroativa_service import SincronizacaoRetroativaService
from app.schemas.contrato_schema import ContratoCreate, ContratoUpdate
from app.schemas.termo_aditivo_schema import TermoAditivoCreate


@pytest.mark.asyncio
async def test_regras_edicao_contrato_14133_e_sincronizacao():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        contrato_repo = ContratoRepository(conn)
        usuario_repo = UsuarioRepository(conn)
        contratado_repo = ContratadoRepository(conn)
        modalidade_repo = ModalidadeRepository(conn)
        status_repo = StatusRepository(conn)
        arquivo_repo = ArquivoRepository(conn)
        file_service = FileService()
        termo_aditivo_repo = TermoAditivoRepository(conn)
        tipo_repo = TipoTermoAditivoRepository(conn)

        service = ContratoService(
            contrato_repo=contrato_repo,
            usuario_repo=usuario_repo,
            contratado_repo=contratado_repo,
            modalidade_repo=modalidade_repo,
            status_repo=status_repo,
            arquivo_repo=arquivo_repo,
            file_service=file_service
        )

        termo_service = TermoAditivoService(
            repo=termo_aditivo_repo,
            tipo_repo=tipo_repo,
            contrato_repo=contrato_repo
        )

        hoje = date.today()
        fim_contrato = hoje + timedelta(days=365)
        uid = int(asyncio.get_event_loop().time() * 1000)

        # 1. Cria contrato válido inicial
        contrato_data = ContratoCreate(
            nr_contrato=f"TEST-GOV-{uid}",
            objeto="Contrato Inicial para Teste de Governança 14.133",
            data_inicio=hoje,
            data_fim=fim_contrato,
            contratado_id=1,
            modalidade_id=1,
            status_id=1,
            gestor_id=1,
            fiscal_id=1,
            valor_anual=100000.0,
            valor_global=100000.0
        )
        contrato = await contrato_repo.create_contrato(contrato_data)
        contrato_id = contrato['id']

        # =========================================================================
        # CENÁRIO 1: Edição de campo sensível SEM justificativa em contrato sem aditivos
        # Deve falhar (HTTP 400 - Justificativa obrigatória)
        # =========================================================================
        with pytest.raises(HTTPException) as exc_info:
            await service.update_contrato(
                contrato_id=contrato_id,
                contrato_update=ContratoUpdate(
                    valor_global=120000.0
                )
            )
        assert exc_info.value.status_code == 400
        assert "justificativa formal" in exc_info.value.detail.lower()

        # =========================================================================
        # CENÁRIO 2: Edição de campo sensível COM justificativa curta (< 10 chars)
        # Deve falhar (HTTP 400)
        # =========================================================================
        with pytest.raises(HTTPException) as exc_info:
            await service.update_contrato(
                contrato_id=contrato_id,
                contrato_update=ContratoUpdate(
                    valor_global=120000.0,
                    justificativa="ajuste"
                )
            )
        assert exc_info.value.status_code == 400

        # =========================================================================
        # CENÁRIO 3: Edição de campo sensível COM justificativa válida (>= 10 chars)
        # Deve ter SUCESSO
        # =========================================================================
        res_ok = await service.update_contrato(
            contrato_id=contrato_id,
            contrato_update=ContratoUpdate(
                valor_global=120000.0,
                justificativa="Correção formal do valor global conforme planilha aprovada"
            )
        )
        assert res_ok is not None
        assert float(res_ok['valor_global']) == 120000.0

        # =========================================================================
        # CENÁRIO 4: Adiciona um Termo Aditivo ao contrato
        # =========================================================================
        aditivo = await termo_service.criar(
            contrato_id=contrato_id,
            dados=TermoAditivoCreate(
                tipo_id=1,  # Prazo
                objeto="1º Aditivo de Prazo",
                data_assinatura=hoje,
                pae=f"PAE-ADIT-{uid}",
                data_publicacao=hoje,
                data_inicio=hoje,
                nova_data_fim=fim_contrato + timedelta(days=180)
            )
        )
        assert aditivo.status == 'Ativo'

        # =========================================================================
        # CENÁRIO 5: Tentar editar campo sensível (ex: objeto ou valor) com aditivos
        # Deve ser BLOQUEADO (HTTP 400) mesmo com justificativa
        # =========================================================================
        with pytest.raises(HTTPException) as exc_info:
            await service.update_contrato(
                contrato_id=contrato_id,
                contrato_update=ContratoUpdate(
                    objeto="Tentando mudar objeto com aditivos existentes",
                    justificativa="Justificativa longa o suficiente para teste"
                )
            )
        assert exc_info.value.status_code == 400
        assert "possui 1 termo(s) aditivo(s)" in exc_info.value.detail

        # =========================================================================
        # CENÁRIO 6: Editar campo NÃO sensível (ex: portaria_fiscal, pae, etc.) com aditivos
        # Deve ter SUCESSO (Apostilamento / Gestão Administrativa)
        # =========================================================================
        res_apostilamento = await service.update_contrato(
            contrato_id=contrato_id,
            contrato_update=ContratoUpdate(
                portaria_fiscal="Portaria PGE Nº 999/2026",
                pae="PAE-APOSTILAMENTO-2026/01"
            )
        )
        assert res_apostilamento is not None
        assert res_apostilamento['portaria_fiscal'] == "Portaria PGE Nº 999/2026"
        assert res_apostilamento['pae'] == "PAE-APOSTILAMENTO-2026/01"

        # =========================================================================
        # CENÁRIO 7: Contrato com status 'Encerrado' tentando editar campo sensível
        # Cria contrato encerrado sem aditivos
        # =========================================================================
        status_encerrado_id = await conn.fetchval(
            "SELECT id FROM status WHERE UPPER(nome) = 'ENCERRADO'"
        )
        contrato_enc = await contrato_repo.create_contrato(
            ContratoCreate(
                nr_contrato=f"TEST-ENC-{uid}",
                objeto="Contrato Encerrado Teste",
                data_inicio=hoje - timedelta(days=400),
                data_fim=hoje - timedelta(days=35),
                contratado_id=1,
                modalidade_id=1,
                status_id=status_encerrado_id,
                gestor_id=1,
                fiscal_id=1,
                valor_anual=50000.0,
                valor_global=50000.0
            )
        )
        with pytest.raises(HTTPException) as exc_info:
            await service.update_contrato(
                contrato_id=contrato_enc['id'],
                contrato_update=ContratoUpdate(
                    valor_global=60000.0,
                    justificativa="Tentativa de alterar contrato encerrado"
                )
            )
        assert exc_info.value.status_code == 400
        assert "encerrado" in exc_info.value.detail.lower()

        # =========================================================================
        # CENÁRIO 8: Sincronização Retroativa Service
        # Deve executar sem exceção e retornar o relatório das atualizações
        # =========================================================================
        resultado_sync = await SincronizacaoRetroativaService.executar(conn)
        assert resultado_sync["sucesso"] is True
        assert "total_contratos_ativos" in resultado_sync
        assert "total_termos_aditivos_ativos" in resultado_sync
        assert resultado_sync["total_contratos_ativos"] >= 2

    finally:
        await conn.close()
