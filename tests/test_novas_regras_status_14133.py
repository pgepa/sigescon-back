# tests/test_novas_regras_status_14133.py
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
from app.schemas.contrato_schema import ContratoCreate, ContratoUpdate
from app.schemas.termo_aditivo_schema import TermoAditivoCreate


@pytest.mark.asyncio
async def test_novas_regras_status_contrato_e_aditivos():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    contratos_criados = []

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

        contrato_service = ContratoService(
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

        contratado_id = await conn.fetchval("SELECT id FROM contratado LIMIT 1")
        modalidade_id = await conn.fetchval("SELECT id FROM modalidade LIMIT 1")
        usuario_id = await conn.fetchval("SELECT id FROM usuario LIMIT 1")
        status_rows = await conn.fetch("SELECT id, nome FROM status")
        status_map = {r['nome']: r['id'] for r in status_rows}

        hoje = date.today()
        uid = int(asyncio.get_event_loop().time() * 1000)

        # -------------------------------------------------------------------------
        # 1. CRIAÇÃO DE CONTRATO SEM STATUS_ID
        # Se data_fim >= hoje -> Ativo
        # -------------------------------------------------------------------------
        c_ativo = await contrato_service.create_contrato(ContratoCreate(
            nr_contrato=f"TESTE-AUTO-ATIVO-{uid}",
            objeto="Contrato com vigência futura sem status informado",
            data_inicio=hoje,
            data_fim=hoje + timedelta(days=180),
            contratado_id=contratado_id,
            modalidade_id=modalidade_id,
            status_id=None,
            gestor_id=usuario_id,
            fiscal_id=usuario_id,
            valor_anual=50000.0,
            valor_global=50000.0
        ))
        contratos_criados.append(c_ativo.id)
        assert c_ativo.status_id == status_map['Ativo'], f"Esperava Ativo, obteve {c_ativo.status_id}"
        assert c_ativo.status_nome == 'Ativo'

        # -------------------------------------------------------------------------
        # 2. CRIAÇÃO DE CONTRATO SEM STATUS_ID COM VIGÊNCIA EXPIRADA
        # Se data_fim < hoje -> Encerrado
        # -------------------------------------------------------------------------
        c_encerrado = await contrato_service.create_contrato(ContratoCreate(
            nr_contrato=f"TESTE-AUTO-ENCERRADO-{uid}",
            objeto="Contrato com vigência passada sem status informado",
            data_inicio=hoje - timedelta(days=200),
            data_fim=hoje - timedelta(days=10),
            contratado_id=contratado_id,
            modalidade_id=modalidade_id,
            status_id=None,
            gestor_id=usuario_id,
            fiscal_id=usuario_id,
            valor_anual=30000.0,
            valor_global=30000.0
        ))
        contratos_criados.append(c_encerrado.id)
        assert c_encerrado.status_id == status_map['Encerrado'], f"Esperava Encerrado, obteve {c_encerrado.status_id}"
        assert c_encerrado.status_nome == 'Encerrado'

        # -------------------------------------------------------------------------
        # 3. CRIAÇÃO DE CONTRATO COM STATUS MANUAL INVÁLIDO
        # Usuário não pode informar Ativo ou Encerrado na criação manual
        # -------------------------------------------------------------------------
        with pytest.raises(HTTPException) as exc_info:
            await contrato_service.create_contrato(ContratoCreate(
                nr_contrato=f"TESTE-INVALIDO-{uid}",
                objeto="Tentativa de fixar status Ativo manualmente",
                data_inicio=hoje,
                data_fim=hoje + timedelta(days=180),
                contratado_id=contratado_id,
                modalidade_id=modalidade_id,
                status_id=status_map['Ativo'],  # Não permitido manualmente
                gestor_id=usuario_id,
                fiscal_id=usuario_id,
                valor_anual=10000.0,
                valor_global=10000.0
            ))
        assert exc_info.value.status_code == 400
        assert "apenas os status 'Suspenso' ou 'Cancelado'" in exc_info.value.detail

        # -------------------------------------------------------------------------
        # 4. CRIAÇÃO DE CONTRATO COM STATUS MANUAL VÁLIDO: SUSPENSO E CANCELADO
        # -------------------------------------------------------------------------
        c_suspenso = await contrato_service.create_contrato(ContratoCreate(
            nr_contrato=f"TESTE-SUSPENSO-{uid}",
            objeto="Contrato criado diretamente como Suspenso",
            data_inicio=hoje,
            data_fim=hoje + timedelta(days=180),
            contratado_id=contratado_id,
            modalidade_id=modalidade_id,
            status_id=status_map['Suspenso'],
            gestor_id=usuario_id,
            fiscal_id=usuario_id,
            valor_anual=20000.0,
            valor_global=20000.0
        ))
        contratos_criados.append(c_suspenso.id)
        assert c_suspenso.status_id == status_map['Suspenso']
        assert c_suspenso.status_nome == 'Suspenso'

        # -------------------------------------------------------------------------
        # 5. TRANSIÇÕES DE STATUS EM CONTRATOS (Cancelado / Suspenso / Reativação)
        # -------------------------------------------------------------------------
        # 5.0 Transição de status sem matrícula deve falhar
        with pytest.raises(HTTPException) as exc_info:
            await contrato_service.update_contrato(
                c_ativo.id,
                ContratoUpdate(
                    status_id=status_map['Suspenso'],
                    justificativa="Suspensão sem informar matrícula do responsável"
                )
            )
        assert exc_info.value.status_code == 400
        assert "matrícula do responsável" in exc_info.value.detail.lower()

        # 5.1 Transição para Suspenso sem justificativa suficiente (< 10 chars) deve falhar
        with pytest.raises(HTTPException) as exc_info:
            await contrato_service.update_contrato(
                c_ativo.id,
                ContratoUpdate(
                    status_id=status_map['Suspenso'],
                    justificativa="Curto",
                    matricula="PGE-12345"
                )
            )
        assert exc_info.value.status_code == 400
        assert "justificativa formal" in exc_info.value.detail.lower()
        assert "10 caracteres" in exc_info.value.detail.lower()

        # 5.2 Transição para Suspenso com justificativa válida e matrícula
        c_ativo_up = await contrato_service.update_contrato(
            c_ativo.id,
            ContratoUpdate(
                status_id=status_map['Suspenso'],
                justificativa="Suspensão cautelar do contrato por decisão administrativa",
                matricula="PGE-12345"
            )
        )
        assert c_ativo_up['status_id'] == status_map['Suspenso']
        assert c_ativo_up['status_nome'] == 'Suspenso'

        # 5.3 Reativação de Suspenso para Ativo exige justificativa e matrícula
        c_reativado = await contrato_service.update_contrato(
            c_ativo.id,
            ContratoUpdate(
                status_id=status_map['Ativo'],
                justificativa="Retomada regular da execução contratual após saneamento",
                matricula="PGE-12345"
            )
        )
        assert c_reativado['status_id'] == status_map['Ativo']
        assert c_reativado['status_nome'] == 'Ativo'

        # 5.4 Transição de Ativo para Encerrado manual é bloqueada (controlada pelo sistema)
        with pytest.raises(HTTPException) as exc_info:
            await contrato_service.update_contrato(
                c_ativo.id,
                ContratoUpdate(
                    status_id=status_map['Encerrado'],
                    justificativa="Tentativa de encerrar manualmente",
                    matricula="PGE-12345"
                )
            )
        assert exc_info.value.status_code == 400
        assert "gerido automaticamente pelo sistema" in exc_info.value.detail

        # 5.5 Transição para Cancelado com justificativa válida e matrícula
        c_cancelado = await contrato_service.update_contrato(
            c_ativo.id,
            ContratoUpdate(
                status_id=status_map['Cancelado'],
                justificativa="Cancelamento definitivo do contrato por anulação do certame",
                matricula="PGE-12345"
            )
        )
        assert c_cancelado['status_id'] == status_map['Cancelado']
        assert c_cancelado['status_nome'] == 'Cancelado'

        # 5.6 Contrato Cancelado é definitivo e bloqueia qualquer edição posterior
        with pytest.raises(HTTPException) as exc_info:
            await contrato_service.update_contrato(
                c_cancelado['id'],
                ContratoUpdate(
                    objeto="Tentativa de alteração em contrato cancelado"
                )
            )
        assert exc_info.value.status_code == 400
        assert "não pode ser reativado nem ter seus dados modificados" in exc_info.value.detail

        # -------------------------------------------------------------------------
        # 6. TERMOS ADITIVOS: REGRAS DE STATUS
        # -------------------------------------------------------------------------
        c_ta = await contrato_service.create_contrato(ContratoCreate(
            nr_contrato=f"TESTE-TA-STATUS-{uid}",
            objeto="Contrato para teste de status de termos aditivos",
            data_inicio=hoje,
            data_fim=hoje + timedelta(days=365),
            contratado_id=contratado_id,
            modalidade_id=modalidade_id,
            status_id=None,
            gestor_id=usuario_id,
            fiscal_id=usuario_id,
            valor_anual=100000.0,
            valor_global=100000.0
        ))
        contratos_criados.append(c_ta.id)

        # 6.1 TA Tipo 1 (Prazo): deve receber status 'Ativo'
        ta_prazo_1 = await termo_service.criar(
            contrato_id=c_ta.id,
            dados=TermoAditivoCreate(
                tipo_id=1,
                objeto="1º TA de Prazo",
                data_assinatura=hoje,
                pae="PAE-01/2026",
                data_publicacao=hoje,
                data_inicio=hoje,
                nova_data_fim=hoje + timedelta(days=500)
            )
        )
        assert ta_prazo_1.status == 'Ativo'

        # 6.2 TA Tipo 2 (Valor): deve receber status 'Incorporado'
        ta_valor = await termo_service.criar(
            contrato_id=c_ta.id,
            dados=TermoAditivoCreate(
                tipo_id=2,
                objeto="2º TA de Valor (Acréscimo)",
                data_assinatura=hoje,
                pae="PAE-02/2026",
                data_publicacao=hoje,
                valor_acrescimo=15000.0
            )
        )
        assert ta_valor.status == 'Incorporado'

        # 6.3 TA Tipo 4 (Outros): deve receber status 'Incorporado'
        ta_outros = await termo_service.criar(
            contrato_id=c_ta.id,
            dados=TermoAditivoCreate(
                tipo_id=4,
                objeto="3º TA Outros - Alteração de Governança",
                data_assinatura=hoje,
                pae="PAE-03/2026",
                data_publicacao=hoje
            )
        )
        assert ta_outros.status == 'Incorporado'

        # 6.4 Novo TA de Prazo substituindo o 1º TA de prazo:
        # data_inicio >= ta_prazo_1.data_inicio e nova_data_fim != ta_prazo_1.nova_data_fim
        # Deve tornar ta_prazo_1 'Inativo'!
        ta_prazo_2 = await termo_service.criar(
            contrato_id=c_ta.id,
            dados=TermoAditivoCreate(
                tipo_id=1,
                objeto="4º TA de Prazo estendendo vigência adicional",
                data_assinatura=hoje,
                pae="PAE-04/2026",
                data_publicacao=hoje,
                data_inicio=hoje,
                nova_data_fim=hoje + timedelta(days=700)
            )
        )
        assert ta_prazo_2.status == 'Ativo'

        # Verifica se ta_prazo_1 agora está 'Inativo' no banco
        ta_1_db = await termo_aditivo_repo.get_by_id(ta_prazo_1.id)
        assert ta_1_db['status'] == 'Inativo', f"Esperava Inativo, obteve {ta_1_db['status']}"

        # Aditivos de valor e outros continuam 'Incorporado'
        ta_val_db = await termo_aditivo_repo.get_by_id(ta_valor.id)
        assert ta_val_db['status'] == 'Incorporado'

    finally:
        for cid in contratos_criados:
            await conn.execute("DELETE FROM termo_aditivo WHERE contrato_id = $1", cid)
            await conn.execute("DELETE FROM contrato WHERE id = $1", cid)
        await conn.close()
