"""
Integração de auditoria com os services existentes
Este módulo adiciona logs de auditoria nos principais services do sistema
"""
from typing import Optional, Dict, Any
from fastapi import Request
import asyncpg

from app.schemas.usuario_schema import Usuario
from app.repositories.audit_log_repo import AuditLogRepository
from app.services.audit_log_service import (
    AuditLogService,
    log_criar_contrato,
    log_atualizar_contrato,
    log_criar_pendencia,
    log_avaliar_pendencia,
    log_atualizar_config
)
from app.schemas.audit_log_schema import AcaoAuditoria, EntidadeAuditoria


async def get_audit_service(conn: asyncpg.Connection) -> AuditLogService:
    """Helper para criar instância do serviço de auditoria"""
    return AuditLogService(audit_repo=AuditLogRepository(conn))


async def audit_criar_contrato(
    conn: asyncpg.Connection,
    request: Optional[Request],
    usuario: Usuario,
    contrato_id: int,
    dados_contrato: Dict[str, Any],
    perfil_usado: Optional[str] = None
):
    """Registra log de criação de contrato"""
    try:
        service = await get_audit_service(conn)

        if request:
            await log_criar_contrato(
                service=service,
                request=request,
                usuario=usuario,
                contrato_id=contrato_id,
                dados_contrato=dados_contrato,
                perfil_usado=perfil_usado
            )
        else:
            # Fallback sem request
            await service.criar_log(
                usuario=usuario,
                acao=AcaoAuditoria.CRIAR,
                entidade=EntidadeAuditoria.CONTRATO,
                entidade_id=contrato_id,
                descricao=f"Criou o contrato #{dados_contrato.get('nr_contrato', contrato_id)}",
                dados_novos=dados_contrato,
                perfil_usado=perfil_usado
            )
    except Exception as e:
        print(f"⚠️ Erro ao criar log de auditoria (criar contrato): {e}")


async def audit_atualizar_contrato(
    conn: asyncpg.Connection,
    request: Optional[Request],
    usuario: Usuario,
    contrato_id: int,
    nr_contrato: str,
    dados_anteriores: Dict[str, Any],
    dados_novos: Dict[str, Any],
    perfil_usado: Optional[str] = None
):
    """Registra log de atualização de contrato"""
    try:
        service = await get_audit_service(conn)

        if request:
            await log_atualizar_contrato(
                service=service,
                request=request,
                usuario=usuario,
                contrato_id=contrato_id,
                nr_contrato=nr_contrato,
                dados_anteriores=dados_anteriores,
                dados_novos=dados_novos,
                perfil_usado=perfil_usado
            )
        else:
            # Identificar campos alterados
            campos_alterados = []
            for key in dados_novos:
                if key in dados_anteriores and dados_anteriores[key] != dados_novos[key]:
                    campos_alterados.append(key)

            descricao = f"Atualizou o contrato #{nr_contrato}"
            if campos_alterados:
                descricao += f" (campos: {', '.join(campos_alterados)})"

            await service.criar_log(
                usuario=usuario,
                acao=AcaoAuditoria.ATUALIZAR,
                entidade=EntidadeAuditoria.CONTRATO,
                entidade_id=contrato_id,
                descricao=descricao,
                dados_anteriores=dados_anteriores,
                dados_novos=dados_novos,
                perfil_usado=perfil_usado
            )
    except Exception as e:
        print(f"⚠️ Erro ao criar log de auditoria (atualizar contrato): {e}")


async def audit_criar_pendencia(
    conn: asyncpg.Connection,
    request: Optional[Request],
    usuario: Usuario,
    pendencia_id: int,
    titulo_pendencia: str,
    contrato_nr: str,
    perfil_usado: Optional[str] = None
):
    """Registra log de criação de pendência"""
    try:
        service = await get_audit_service(conn)

        if request:
            await log_criar_pendencia(
                service=service,
                request=request,
                usuario=usuario,
                pendencia_id=pendencia_id,
                titulo_pendencia=titulo_pendencia,
                contrato_nr=contrato_nr,
                perfil_usado=perfil_usado
            )
        else:
            await service.criar_log(
                usuario=usuario,
                acao=AcaoAuditoria.CRIAR,
                entidade=EntidadeAuditoria.PENDENCIA,
                entidade_id=pendencia_id,
                descricao=f"Criou a pendência '{titulo_pendencia}' no contrato #{contrato_nr}",
                perfil_usado=perfil_usado
            )
    except Exception as e:
        print(f"⚠️ Erro ao criar log de auditoria (criar pendência): {e}")


async def audit_atualizar_pendencia(
    conn: asyncpg.Connection,
    request: Optional[Request],
    usuario: Usuario,
    pendencia_id: int,
    titulo_pendencia: str,
    status_anterior: str,
    status_novo: str,
    perfil_usado: Optional[str] = None
):
    """Registra log de atualização de pendência"""
    try:
        service = await get_audit_service(conn)

        if request:
            await log_avaliar_pendencia(
                service=service,
                request=request,
                usuario=usuario,
                pendencia_id=pendencia_id,
                titulo_pendencia=titulo_pendencia,
                status_anterior=status_anterior,
                status_novo=status_novo,
                perfil_usado=perfil_usado
            )
        else:
            acao = AcaoAuditoria.CONCLUIR if status_novo == "Concluída" else AcaoAuditoria.ATUALIZAR

            await service.criar_log(
                usuario=usuario,
                acao=acao,
                entidade=EntidadeAuditoria.PENDENCIA,
                entidade_id=pendencia_id,
                descricao=f"Alterou status da pendência '{titulo_pendencia}' de '{status_anterior}' para '{status_novo}'",
                dados_anteriores={"status": status_anterior},
                dados_novos={"status": status_novo},
                perfil_usado=perfil_usado
            )
    except Exception as e:
        print(f"⚠️ Erro ao criar log de auditoria (atualizar pendência): {e}")


async def audit_criar_pendencias_automaticas(
    conn: asyncpg.Connection,
    request: Optional[Request],
    usuario: Usuario,
    contrato_id: int,
    contrato_nr: str,
    quantidade: int,
    perfil_usado: Optional[str] = None
):
    """Registra log de criação de pendências automáticas"""
    try:
        service = await get_audit_service(conn)

        await service.criar_log_from_request(
            request=request,
            usuario=usuario,
            acao=AcaoAuditoria.CRIAR_PENDENCIAS_AUTOMATICAS,
            entidade=EntidadeAuditoria.CONTRATO,
            entidade_id=contrato_id,
            descricao=f"Criou {quantidade} pendências automáticas no contrato #{contrato_nr}",
            dados_novos={"quantidade_pendencias": quantidade},
            perfil_usado=perfil_usado
        )
    except Exception as e:
        print(f"⚠️ Erro ao criar log de auditoria (pendências automáticas): {e}")


async def audit_atualizar_configuracao(
    conn: asyncpg.Connection,
    request: Optional[Request],
    usuario: Usuario,
    chave_config: str,
    valor_anterior: Any,
    valor_novo: Any,
    perfil_usado: Optional[str] = None
):
    """Registra log de atualização de configuração"""
    try:
        service = await get_audit_service(conn)

        if request:
            await log_atualizar_config(
                service=service,
                request=request,
                usuario=usuario,
                chave_config=chave_config,
                valor_anterior=valor_anterior,
                valor_novo=valor_novo,
                perfil_usado=perfil_usado
            )
        else:
            await service.criar_log(
                usuario=usuario,
                acao=AcaoAuditoria.ATUALIZAR_CONFIG,
                entidade=EntidadeAuditoria.CONFIG,
                descricao=f"Atualizou configuração '{chave_config}'",
                dados_anteriores={"chave": chave_config, "valor": valor_anterior},
                dados_novos={"chave": chave_config, "valor": valor_novo},
                perfil_usado=perfil_usado
            )
    except Exception as e:
        print(f"⚠️ Erro ao criar log de auditoria (atualizar config): {e}")


async def audit_finalizar_relatorio(
    conn: asyncpg.Connection,
    request: Optional[Request],
    usuario: Usuario,
    relatorio_id: int,
    pendencia_titulo: str,
    contrato_nr: str,
    perfil_usado: Optional[str] = None
):
    """Registra log de finalização de relatório (Rascunho -> Salvo, sem aprovação de admin)"""
    try:
        service = await get_audit_service(conn)

        descricao = f"Finalizou o relatório da pendência '{pendencia_titulo}' do contrato #{contrato_nr}"

        if request:
            await service.criar_log_from_request(
                request=request,
                usuario=usuario,
                acao=AcaoAuditoria.CONCLUIR,
                entidade=EntidadeAuditoria.RELATORIO,
                entidade_id=relatorio_id,
                descricao=descricao,
                dados_novos={"status": "Salvo"},
                perfil_usado=perfil_usado
            )
        else:
            await service.criar_log(
                usuario=usuario,
                acao=AcaoAuditoria.CONCLUIR,
                entidade=EntidadeAuditoria.RELATORIO,
                entidade_id=relatorio_id,
                descricao=descricao,
                dados_novos={"status": "Salvo"},
                perfil_usado=perfil_usado
            )
    except Exception as e:
        print(f"⚠️ Erro ao criar log de auditoria (finalizar relatório): {e}")
