# tests/test_termo_aditivo_coexistencia.py
import pytest
import asyncio
from datetime import date, timedelta
from app.core.database import get_connection
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.termo_aditivo_repo import TermoAditivoRepository
from app.repositories.tipo_termo_aditivo_repo import TipoTermoAditivoRepository
from app.services.termo_aditivo_service import TermoAditivoService
from app.schemas.termo_aditivo_schema import TermoAditivoCreate
from app.schemas.contrato_schema import ContratoCreate


@pytest.mark.asyncio
async def test_fluxo_completo_termo_aditivo_e_coexistencia():
    async for conn in get_connection():
        contrato_repo = ContratoRepository(conn)
        termo_aditivo_repo = TermoAditivoRepository(conn)
        tipo_repo = TipoTermoAditivoRepository(conn)

        service = TermoAditivoService(
            repo=termo_aditivo_repo,
            tipo_repo=tipo_repo,
            contrato_repo=contrato_repo,
        )

        # 1. Validar tipos de termo aditivo (FK)
        tipos = await service.listar_tipos()
        assert len(tipos) == 4
        tipos_dict = {t.id: t.nome for t in tipos}
        assert tipos_dict[1] == 'Prazo'
        assert tipos_dict[2] == 'Valor'
        assert tipos_dict[3] == 'Misto'
        assert tipos_dict[4] == 'Outros'

        # 2. Criar contrato de teste
        hoje = date.today()
        data_fim_inicial = hoje + timedelta(days=365)
        contrato_data = ContratoCreate(
            nr_contrato=f"TESTE-TA-{int(asyncio.get_event_loop().time())}",
            objeto="Contrato de Teste para Validação de Termos Aditivos e Coexistência",
            data_inicio=hoje,
            data_fim=data_fim_inicial,
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
        assert contrato_id is not None

        try:
            # 3. Adicionar 1º Aditivo: PRAZO (ID 1) -> Vigência +1 ano
            nova_data_fim_1 = data_fim_inicial + timedelta(days=365)
            aditivo_1 = await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=1,
                    objeto="1º Aditivo de Prazo",
                    data_assinatura=hoje,
                    nova_data_fim=nova_data_fim_1
                )
            )
            assert aditivo_1.status == 'Ativo'
            assert aditivo_1.tipo_id == 1

            # Validar que contrato pai atualizou a data_fim
            contrato_atualizado = await contrato_repo.find_contrato_by_id(contrato_id)
            assert contrato_atualizado['data_fim'] == nova_data_fim_1

            # 4. Adicionar 2º Aditivo: VALOR (ID 2) -> Acréscimo de R$ 25.000,00
            aditivo_2 = await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=2,
                    objeto="2º Aditivo de Valor (Acréscimo)",
                    data_assinatura=hoje,
                    valor_acrescimo=25000.0
                )
            )
            assert aditivo_2.status == 'Ativo'

            # Validar REGRA DE CONVIVÊNCIA: Aditivo 1 (Prazo) DEVE CONTINUAR ATIVO!
            aditivo_1_check = await termo_aditivo_repo.get_by_id(aditivo_1.id)
            assert aditivo_1_check['status'] == 'Ativo', "Aditivo de Prazo não pode ser inativado por Aditivo de Valor!"

            # Validar valor recalculado no contrato pai
            contrato_atualizado = await contrato_repo.find_contrato_by_id(contrato_id)
            assert float(contrato_atualizado['valor_global']) == 125000.0
            assert contrato_atualizado['data_fim'] == nova_data_fim_1

            # 5. Adicionar 3º Aditivo: OUTROS (ID 4) -> Cláusula administrativa
            aditivo_3 = await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=4,
                    objeto="3º Aditivo - Alteração de Cláusula de Governança",
                    data_assinatura=hoje
                )
            )
            assert aditivo_3.status == 'Ativo'

            # Validar que Aditivos 1, 2 e 3 estão TODOS ATIVOS (coexistência harmônica)
            aditivo_1_check = await termo_aditivo_repo.get_by_id(aditivo_1.id)
            aditivo_2_check = await termo_aditivo_repo.get_by_id(aditivo_2.id)
            assert aditivo_1_check['status'] == 'Ativo'
            assert aditivo_2_check['status'] == 'Ativo'

            # 6. Adicionar 4º Aditivo: PRAZO (ID 1) -> Nova prorrogação de vigência
            nova_data_fim_2 = nova_data_fim_1 + timedelta(days=365)
            aditivo_4 = await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=1,
                    objeto="4º Aditivo de Prazo (Nova Prorrogação)",
                    data_assinatura=hoje,
                    nova_data_fim=nova_data_fim_2
                )
            )
            assert aditivo_4.status == 'Ativo'

            # Validar REGRA DE INATIVAÇÃO SELETIVA:
            # - Aditivo 1 (Prazo anterior) DEVE FICAR INATIVO!
            # - Aditivo 2 (Valor) DEVE PERMANECER ATIVO!
            # - Aditivo 3 (Outros) DEVE PERMANECER ATIVO!
            aditivo_1_check = await termo_aditivo_repo.get_by_id(aditivo_1.id)
            aditivo_2_check = await termo_aditivo_repo.get_by_id(aditivo_2.id)
            aditivo_3_check = await termo_aditivo_repo.get_by_id(aditivo_3.id)

            assert aditivo_1_check['status'] == 'Inativo', "Aditivo 1 de Prazo deveria ter sido inativado pelo novo Aditivo 4 de Prazo"
            assert aditivo_2_check['status'] == 'Ativo', "Aditivo 2 de Valor deve continuar Ativo!"
            assert aditivo_3_check['status'] == 'Ativo', "Aditivo 3 de Outros deve continuar Ativo!"

            # Validar contrato pai após 4º aditivo
            contrato_atualizado = await contrato_repo.find_contrato_by_id(contrato_id)
            assert contrato_atualizado['data_fim'] == nova_data_fim_2
            assert float(contrato_atualizado['valor_global']) == 125000.0

            # 7. Executar a rotina do Robô de Sincronização Geral
            alterados = await termo_aditivo_repo.sincronizar_status_todos_aditivos()
            contratos_sync = await contrato_repo.sincronizar_status_vencimento_geral()

            # 8. Validar listagem consolidada do contrato
            lista = await service.listar_por_contrato(contrato_id)
            assert len(lista) == 4
            status_map = {a.id: a.status for a in lista}
            assert status_map[aditivo_1.id] == 'Inativo'
            assert status_map[aditivo_2.id] == 'Ativo'
            assert status_map[aditivo_3.id] == 'Ativo'
            assert status_map[aditivo_4.id] == 'Ativo'

            print("\n✅ Todos os testes de coexistência por natureza e robô passaram com 100% de sucesso!")

        finally:
            # Limpeza do contrato e aditivos de teste
            await conn.execute("DELETE FROM termo_aditivo WHERE contrato_id = $1", contrato_id)
            await conn.execute("DELETE FROM contrato WHERE id = $1", contrato_id)
