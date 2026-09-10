# tests/test_termo_aditivo_regras_14133.py
import pytest
import asyncio
import asyncpg
from datetime import date, timedelta
from app.core.config import settings
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.termo_aditivo_repo import TermoAditivoRepository
from app.repositories.tipo_termo_aditivo_repo import TipoTermoAditivoRepository
from app.services.termo_aditivo_service import TermoAditivoService
from app.schemas.termo_aditivo_schema import TermoAditivoCreate
from app.schemas.contrato_schema import ContratoCreate


@pytest.mark.asyncio
async def test_regras_vigencia_e_aditivos_lei_14133():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    contrato_repo = ContratoRepository(conn)
    termo_aditivo_repo = TermoAditivoRepository(conn)
    tipo_repo = TipoTermoAditivoRepository(conn)

    service = TermoAditivoService(
        repo=termo_aditivo_repo,
        tipo_repo=tipo_repo,
        contrato_repo=contrato_repo,
    )

    hoje = date.today()
    # Contrato de 1 ano
    fim_contrato = hoje + timedelta(days=365)
    contrato_data = ContratoCreate(
        nr_contrato=f"TESTE-14133-{int(asyncio.get_event_loop().time())}",
        objeto="Contrato de Teste - Regras da Lei 14.133 e Súmula 282 TCU",
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

    try:
        # =========================================================================
        # CENÁRIO A: Aditivo com vigência FUTURA (data_inicio > CURRENT_DATE)
        # Deve receber status 'Aguardando Vigência' e NÃO alterar a data do contrato
        # =========================================================================
        inicio_futuro = hoje + timedelta(days=30)
        fim_futuro = fim_contrato + timedelta(days=365)
        aditivo_futuro = await service.criar(
            contrato_id=contrato_id,
            dados=TermoAditivoCreate(
                tipo_id=1,  # Prazo
                objeto="Aditivo com vigência futura",
                data_assinatura=hoje,
                pae="PAE-FUTURO/2026",
                data_publicacao=hoje,
                data_inicio=inicio_futuro,
                nova_data_fim=fim_futuro
            )
        )
        assert aditivo_futuro.status == 'Aguardando Vigência', f"Esperava 'Aguardando Vigência', obteve {aditivo_futuro.status}"

        # Contrato ainda mantém a data_fim vigente atual (não prematuramente substituída)
        c_check = await contrato_repo.find_contrato_by_id(contrato_id)
        assert c_check['data_fim'] == fim_contrato
        assert c_check['status_nome'] == 'Ativo'

        # =========================================================================
        # CENÁRIO B: Múltiplos Aditivos de VALOR (Cumulatividade Financeira)
        # Ambos devem permanecer 'Ativo' simultaneamente!
        # =========================================================================
        aditivo_val_1 = await service.criar(
            contrato_id=contrato_id,
            dados=TermoAditivoCreate(
                tipo_id=2,  # Valor
                objeto="1º Aditivo de Valor: Acréscimo de R$ 10.000",
                data_assinatura=hoje,
                pae="PAE-VAL1/2026",
                data_publicacao=hoje,
                valor_acrescimo=10000.0
            )
        )
        assert aditivo_val_1.status == 'Ativo'

        c_check = await contrato_repo.find_contrato_by_id(contrato_id)
        assert float(c_check['valor_global']) == 110000.0

        aditivo_val_2 = await service.criar(
            contrato_id=contrato_id,
            dados=TermoAditivoCreate(
                tipo_id=2,  # Valor
                objeto="2º Aditivo de Valor: Acréscimo de R$ 15.000",
                data_assinatura=hoje,
                pae="PAE-VAL2/2026",
                data_publicacao=hoje,
                valor_acrescimo=15000.0
            )
        )
        assert aditivo_val_2.status == 'Ativo'

        # Verifica que o 1º aditivo de valor CONTINUA 'Ativo' (coexistência plena)
        ad_1_banco = await termo_aditivo_repo.get_by_id(aditivo_val_1.id)
        assert ad_1_banco['status'] == 'Ativo', "O 1º aditivo de valor deve continuar Ativo!"

        c_check = await contrato_repo.find_contrato_by_id(contrato_id)
        assert float(c_check['valor_global']) == 125000.0, f"Esperava 125000, obteve {c_check['valor_global']}"

        # =========================================================================
        # CENÁRIO C: Exclusão de um dos aditivos de valor (Estorno isolado)
        # =========================================================================
        await service.excluir(contrato_id, aditivo_val_2.id)
        ad_2_banco = await conn.fetchrow("SELECT status, ativo FROM termo_aditivo WHERE id = $1", aditivo_val_2.id)
        assert ad_2_banco['status'] == 'Inativo'
        assert ad_2_banco['ativo'] is False

        # O 1º aditivo de valor permanece Ativo
        ad_1_banco = await termo_aditivo_repo.get_by_id(aditivo_val_1.id)
        assert ad_1_banco['status'] == 'Ativo'

        # O valor_global regrediu para 110.000 (estorno do aditivo 2)
        c_check = await contrato_repo.find_contrato_by_id(contrato_id)
        assert float(c_check['valor_global']) == 110000.0

        # =========================================================================
        # CENÁRIO D: Contrato Encerrado com aditivo antigo Vencido
        # Ao adicionar novo aditivo de prazo estendendo vigência:
        # - Contrato reativa para 'Ativo'
        # - Aditivo antigo expirado PERMANECE 'Vencido'
        # =========================================================================
        passado_inicio = hoje - timedelta(days=400)
        passado_fim = hoje - timedelta(days=35)
        # Simula um aditivo passado que já venceu
        aditivo_passado = await service.criar(
            contrato_id=contrato_id,
            dados=TermoAditivoCreate(
                tipo_id=1,
                objeto="Aditivo antigo expirado",
                data_assinatura=passado_inicio,
                pae="PAE-ANTIGO/2025",
                data_publicacao=passado_inicio,
                data_inicio=passado_inicio,
                nova_data_fim=passado_fim
            )
        )
        # Como nova_data_fim < CURRENT_DATE, deve ser 'Vencido'
        assert aditivo_passado.status == 'Vencido'

        # Simula contrato como Encerrado
        await conn.execute("UPDATE contrato SET status_id = 3, data_fim = $1 WHERE id = $2", passado_fim, contrato_id)
        c_check = await contrato_repo.find_contrato_by_id(contrato_id)
        assert c_check['status_nome'] == 'Encerrado'

        # Agora usuário adiciona um novo aditivo de prazo vigente hoje
        novo_fim = hoje + timedelta(days=200)
        aditivo_novo_prazo = await service.criar(
            contrato_id=contrato_id,
            dados=TermoAditivoCreate(
                tipo_id=1,
                objeto="Novo aditivo reativando vigência",
                data_assinatura=hoje,
                pae="PAE-REATIVACAO/2026",
                data_publicacao=hoje,
                data_inicio=hoje,
                nova_data_fim=novo_fim
            )
        )
        assert aditivo_novo_prazo.status == 'Ativo'

        # Contrato foi reativado para Ativo com nova data fim
        c_check = await contrato_repo.find_contrato_by_id(contrato_id)
        assert c_check['status_nome'] == 'Ativo', f"Esperava Ativo, obteve {c_check['status_nome']}"
        assert c_check['data_fim'] == novo_fim

        # O aditivo antigo DEVE PERMANECER 'Vencido'! (Auditabilidade protegida)
        ad_passado_banco = await termo_aditivo_repo.get_by_id(aditivo_passado.id)
        assert ad_passado_banco['status'] == 'Vencido', f"Esperava Vencido, obteve {ad_passado_banco['status']}"

    finally:
        await conn.execute("DELETE FROM termo_aditivo WHERE contrato_id = $1", contrato_id)
        await conn.execute("DELETE FROM contrato WHERE id = $1", contrato_id)
        await conn.close()
