# tests/test_regras_datas_14133.py
import pytest
import asyncio
import asyncpg
from datetime import date, timedelta
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import settings
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.termo_aditivo_repo import TermoAditivoRepository
from app.repositories.tipo_termo_aditivo_repo import TipoTermoAditivoRepository
from app.services.termo_aditivo_service import TermoAditivoService
from app.schemas.contrato_schema import ContratoCreate
from app.schemas.termo_aditivo_schema import TermoAditivoCreate


@pytest.mark.asyncio
async def test_regras_datas_contrato_e_aditivo_14133():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        contrato_repo = ContratoRepository(conn)
        termo_aditivo_repo = TermoAditivoRepository(conn)
        tipo_repo = TipoTermoAditivoRepository(conn)

        service = TermoAditivoService(
            repo=termo_aditivo_repo,
            tipo_repo=tipo_repo,
            contrato_repo=contrato_repo
        )

        hoje = date.today()

        # =====================================================================
        # 1. Contrato com data_fim < data_inicio (inversão cronológica)
        # =====================================================================
        with pytest.raises(ValidationError) as exc_info:
            ContratoCreate(
                nr_contrato="TEST-DATA-INV",
                objeto="Teste data invertida",
                data_inicio=hoje,
                data_fim=hoje - timedelta(days=10),
                contratado_id=1,
                modalidade_id=1,
                status_id=1
            )
        assert "não pode ser anterior à data de início" in str(exc_info.value)

        # =====================================================================
        # 2. Contrato com vigência inicial excessiva (> 10 anos / erro de digitação)
        # =====================================================================
        with pytest.raises(ValidationError) as exc_info:
            ContratoCreate(
                nr_contrato="TEST-DATA-10A",
                objeto="Teste vigência excessiva",
                data_inicio=hoje,
                data_fim=hoje + timedelta(days=3660),
                contratado_id=1,
                modalidade_id=1,
                status_id=1
            )
        assert "não pode ser superior a 10 anos" in str(exc_info.value)

        # =====================================================================
        # 3. Criar contrato válido de base para testes dos aditivos
        # =====================================================================
        uid = int(asyncio.get_event_loop().time() * 1000)
        fim_contrato = hoje + timedelta(days=365)
        contrato = await contrato_repo.create_contrato(
            ContratoCreate(
                nr_contrato=f"TEST-DATE-{uid}",
                objeto="Contrato Base para Validação Temporal 14.133",
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
        )
        contrato_id = contrato["id"]

        # =====================================================================
        # 4. Aditivo com data_publicacao < data_assinatura
        # =====================================================================
        with pytest.raises(ValidationError) as exc_info:
            TermoAditivoCreate(
                tipo_id=1,
                objeto="Aditivo Publicação Anterior",
                data_assinatura=hoje,
                data_publicacao=hoje - timedelta(days=2),
                data_inicio=hoje,
                nova_data_fim=fim_contrato + timedelta(days=180),
                pae="PAE-001"
            )
        assert "data de publicação não pode ser anterior à data de assinatura" in str(exc_info.value).lower()

        # =====================================================================
        # 5. Aditivo de Prazo com nova_data_fim <= data_inicio do aditivo
        # =====================================================================
        with pytest.raises(ValidationError) as exc_info:
            TermoAditivoCreate(
                tipo_id=1,
                objeto="Aditivo Fim Menor que Início",
                data_assinatura=hoje,
                data_publicacao=hoje,
                data_inicio=hoje + timedelta(days=30),
                nova_data_fim=hoje + timedelta(days=10),
                pae="PAE-002"
            )
        assert "nova data fim deve ser posterior" in str(exc_info.value).lower()

        # =====================================================================
        # 6. Aditivo de Prazo assinado após término do contrato (Súmula 282 TCU / Art. 132)
        # =====================================================================
        with pytest.raises(HTTPException) as exc_info:
            await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=1,
                    objeto="Aditivo Extemporâneo Vencido",
                    data_assinatura=fim_contrato + timedelta(days=5),
                    data_publicacao=fim_contrato + timedelta(days=5),
                    data_inicio=fim_contrato,
                    nova_data_fim=fim_contrato + timedelta(days=180),
                    pae="PAE-003"
                )
            )
        assert exc_info.value.status_code == 400
        assert "súmula 282" in exc_info.value.detail.lower()

        # =====================================================================
        # 7. Aditivo de Prazo com data_inicio anterior ao contrato original
        # =====================================================================
        with pytest.raises(HTTPException) as exc_info:
            await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=1,
                    objeto="Aditivo Início Retroativo",
                    data_assinatura=hoje,
                    data_publicacao=hoje,
                    data_inicio=hoje - timedelta(days=30),
                    nova_data_fim=fim_contrato + timedelta(days=180),
                    pae="PAE-004"
                )
            )
        assert exc_info.value.status_code == 400
        assert "não pode ser anterior à data de início original" in exc_info.value.detail.lower()

        # =====================================================================
        # 8. Aditivo de Prazo com nova_data_fim <= data_fim atual (não estende prazo)
        # =====================================================================
        with pytest.raises(HTTPException) as exc_info:
            await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=1,
                    objeto="Aditivo Sem Ganho de Prazo",
                    data_assinatura=hoje,
                    data_publicacao=hoje,
                    data_inicio=hoje,
                    nova_data_fim=fim_contrato - timedelta(days=10),
                    pae="PAE-005"
                )
            )
        assert exc_info.value.status_code == 400
        assert "deve ser estritamente posterior à vigência atual" in exc_info.value.detail.lower()

        # =====================================================================
        # 9. Aditivo que extrapola o Limite Decenal (Arts. 106 e 107 Lei 14.133)
        # =====================================================================
        with pytest.raises(HTTPException) as exc_info:
            await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=1,
                    objeto="Aditivo Extrapolando 10 Anos",
                    data_assinatura=hoje,
                    data_publicacao=hoje,
                    data_inicio=hoje,
                    nova_data_fim=hoje + timedelta(days=3660),
                    pae="PAE-006"
                )
            )
        assert exc_info.value.status_code == 400
        assert "limite máximo decenal de 10 anos" in exc_info.value.detail.lower()

        # =====================================================================
        # 10. Aditivo plenamente válido dentro de todas as regras da 14.133
        # =====================================================================
        novo_fim = fim_contrato + timedelta(days=365)
        aditivo_valido = await service.criar(
            contrato_id=contrato_id,
            dados=TermoAditivoCreate(
                tipo_id=1,
                objeto="1º Aditivo de Prazo Legal e Válido",
                data_assinatura=hoje,
                data_publicacao=hoje,
                data_inicio=hoje,
                nova_data_fim=novo_fim,
                pae="PAE-LEGAL-001"
            )
        )
        assert aditivo_valido is not None
        assert aditivo_valido.status == "Ativo"
        assert aditivo_valido.nova_data_fim == novo_fim

        contrato_pos = await contrato_repo.find_contrato_by_id(contrato_id)
        assert contrato_pos["data_fim"] == novo_fim
        assert contrato_pos["data_fim_original"] == fim_contrato

    finally:
        await conn.close()
