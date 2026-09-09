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
        assert contrato['data_inicio_original'] == hoje
        assert contrato['data_fim_original'] == data_fim_inicial

        try:
            # 3. Adicionar 1º Aditivo: PRAZO (ID 1) -> Nova data início e nova data fim (+1 ano)
            nova_data_inicio_1 = hoje + timedelta(days=10)
            nova_data_fim_1 = data_fim_inicial + timedelta(days=365)
            aditivo_1 = await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=1,
                    objeto="1º Aditivo de Prazo",
                    data_assinatura=hoje,
                    pae="PAE-001/2026",
                    data_publicacao=hoje,
                    data_inicio=nova_data_inicio_1,
                    nova_data_fim=nova_data_fim_1
                )
            )
            assert aditivo_1.status == 'Ativo'
            assert aditivo_1.tipo_id == 1

            # Validar que contrato pai atualizou data_inicio e data_fim, mantendo as originais
            contrato_atualizado = await contrato_repo.find_contrato_by_id(contrato_id)
            assert contrato_atualizado['data_inicio'] == nova_data_inicio_1
            assert contrato_atualizado['data_inicio_original'] == hoje
            assert contrato_atualizado['data_fim'] == nova_data_fim_1
            assert contrato_atualizado['data_fim_original'] == data_fim_inicial
            assert contrato_atualizado['status_nome'] == 'Ativo'

            # 4. Adicionar 2º Aditivo: VALOR (ID 2) -> Acréscimo de R$ 25.000,00 (sem data_inicio)
            aditivo_2 = await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=2,
                    objeto="2º Aditivo de Valor (Acréscimo)",
                    data_assinatura=hoje,
                    pae="PAE-002/2026",
                    data_publicacao=hoje,
                    valor_acrescimo=25000.0
                )
            )
            assert aditivo_2.status == 'Ativo'
            # Valida que herdou a vigência do contrato
            assert aditivo_2.nova_data_fim == nova_data_fim_1

            # Validar NOVA REGRA: Aditivo 1 (Prazo) AGORA PASSA A SER INATIVO!
            aditivo_1_check = await termo_aditivo_repo.get_by_id(aditivo_1.id)
            assert aditivo_1_check['status'] == 'Inativo', "Aditivo antecessor deve receber status Inativo!"

            # Validar que a vigência do Aditivo 1 e o valor do Aditivo 2 PERMANECEM NO CONTRATO
            contrato_atualizado = await contrato_repo.find_contrato_by_id(contrato_id)
            assert float(contrato_atualizado['valor_global']) == 125000.0
            assert contrato_atualizado['data_fim'] == nova_data_fim_1
            assert contrato_atualizado['data_inicio'] == nova_data_inicio_1
            assert contrato_atualizado['status_nome'] == 'Ativo'

            # 5. Adicionar 3º Aditivo: OUTROS (ID 4) -> Cláusula administrativa
            aditivo_3 = await service.criar(
                contrato_id=contrato_id,
                dados=TermoAditivoCreate(
                    tipo_id=4,
                    objeto="3º Aditivo - Alteração de Cláusula de Governança",
                    data_assinatura=hoje,
                    pae="PAE-003/2026",
                    data_publicacao=hoje
                )
            )
            assert aditivo_3.status == 'Ativo'
            assert aditivo_3.nova_data_fim == nova_data_fim_1

            # Validar que Aditivo 2 passou a ser Inativo e Aditivo 3 é o ÚNICO Ativo
            aditivo_1_check = await termo_aditivo_repo.get_by_id(aditivo_1.id)
            aditivo_2_check = await termo_aditivo_repo.get_by_id(aditivo_2.id)
            assert aditivo_1_check['status'] == 'Inativo'
            assert aditivo_2_check['status'] == 'Inativo'

            # 6. Executar a rotina do Robô de Sincronização Geral com contrato vigente
            await termo_aditivo_repo.sincronizar_status_todos_aditivos()
            await contrato_repo.sincronizar_status_vencimento_geral()

            lista = await service.listar_por_contrato(contrato_id)
            status_map = {a.id: a.status for a in lista}
            assert status_map[aditivo_1.id] == 'Inativo'
            assert status_map[aditivo_2.id] == 'Inativo'
            assert status_map[aditivo_3.id] == 'Ativo'

            # 7. Simular expiração do contrato (robô marca contrato como Encerrado e TODOS aditivos como Vencido)
            ontem = hoje - timedelta(days=1)
            await conn.execute("UPDATE contrato SET data_fim = $1, data_fim_original = $1 WHERE id = $2", ontem, contrato_id)
            await conn.execute("UPDATE termo_aditivo SET nova_data_fim = $1 WHERE contrato_id = $2", ontem, contrato_id)

            await contrato_repo.sincronizar_status_vencimento_geral()
            await termo_aditivo_repo.sincronizar_status_todos_aditivos()

            contrato_expirado = await contrato_repo.find_contrato_by_id(contrato_id)
            assert contrato_expirado['status_nome'] == 'Encerrado'

            lista_expirada = await service.listar_por_contrato(contrato_id)
            for ad in lista_expirada:
                assert ad.status == 'Vencido', f"Aditivo {ad.numero_aditivo} deveria estar Vencido, mas está {ad.status}"

            print("\n[OK] Todas as novas regras de negocio e sincronizacao do robo passaram com 100% de sucesso!")

        finally:
            # Limpeza do contrato e aditivos de teste
            await conn.execute("DELETE FROM termo_aditivo WHERE contrato_id = $1", contrato_id)
            await conn.execute("DELETE FROM contrato WHERE id = $1", contrato_id)
