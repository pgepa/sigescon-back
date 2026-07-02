# app/services/relatorio_service.py
import os
from typing import List, Optional
from fastapi import HTTPException, status, UploadFile, Request
import logging

# Repositórios
from app.repositories.relatorio_repo import RelatorioRepository
from app.repositories.arquivo_repo import ArquivoRepository
from app.repositories.pendencia_repo import PendenciaRepository
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.status_relatorio_repo import StatusRelatorioRepository
from app.repositories.status_pendencia_repo import StatusPendenciaRepository
from app.repositories.usuario_repo import UsuarioRepository
from app.repositories.perfil_repo import PerfilRepository

# Services
from app.services.file_service import FileService
from app.services.audit_integration import (
    audit_aprovar_relatorio,
    audit_rejeitar_relatorio
)

# Schemas
from app.schemas.relatorio_schema import Relatorio, RelatorioCreate, RelatorioAnalise
from app.schemas.usuario_schema import Usuario

logger = logging.getLogger(__name__)

class RelatorioService:
    def __init__(self,
                 relatorio_repo: RelatorioRepository,
                 arquivo_repo: ArquivoRepository,
                 pendencia_repo: PendenciaRepository,
                 contrato_repo: ContratoRepository,
                 status_relatorio_repo: StatusRelatorioRepository,
                 status_pendencia_repo: StatusPendenciaRepository,
                 usuario_repo: UsuarioRepository,
                 perfil_repo: PerfilRepository, 
                 file_service: FileService):
        self.relatorio_repo = relatorio_repo
        self.arquivo_repo = arquivo_repo
        self.pendencia_repo = pendencia_repo
        self.contrato_repo = contrato_repo
        self.status_relatorio_repo = status_relatorio_repo
        self.status_pendencia_repo = status_pendencia_repo
        self.usuario_repo = usuario_repo
        self.perfil_repo = perfil_repo 
        self.file_service = file_service

    async def get_relatorios_by_contrato_id(self, contrato_id: int) -> List[Relatorio]:
        if not await self.contrato_repo.find_contrato_by_id(contrato_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
        
        relatorios_data = await self.relatorio_repo.get_relatorios_by_contrato_id(contrato_id)
        return [Relatorio.model_validate(r) for r in relatorios_data]

    async def submit_relatorio(self, contrato_id: int, relatorio_data: RelatorioCreate, file: UploadFile, current_user: Usuario) -> Relatorio:
        contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
        if not contrato:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

        perfil_usuario = await self.perfil_repo.get_perfil_by_id(current_user.perfil_id)
        is_admin = perfil_usuario and perfil_usuario.get("nome") == "Administrador"

        if not is_admin and contrato['fiscal_id'] != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: Você não é o fiscal deste contrato.")

        pendencia = await self.pendencia_repo.get_pendencia_by_id(relatorio_data.pendencia_id)
        if not pendencia:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pendência não encontrada")

        # Verifica se é reenvio - se já existe relatório para esta pendência, substitui o arquivo
        relatorios_existentes = await self.relatorio_repo.get_relatorios_by_pendencia_id(relatorio_data.pendencia_id)

        # Salva o novo arquivo
        nome_original, path, tamanho = await self.file_service.save_upload_file(contrato_id, file)

        arquivo_criado = await self.arquivo_repo.create_arquivo(
            nome_arquivo=nome_original,
            path_armazenamento=path,
            tipo_arquivo=file.content_type,
            tamanho_bytes=tamanho,
            contrato_id=contrato_id
        )

        status_relatorio_pendente = next(s for s in await self.status_relatorio_repo.get_all() if s['nome'] == 'Pendente de Análise')

        # Se for reenvio, atualiza o relatório existente em vez de criar novo
        if relatorios_existentes:
            relatorio_existente = relatorios_existentes[0]  # Pega o mais recente

            # Remove o arquivo antigo fisicamente
            arquivo_antigo = await self.arquivo_repo.find_arquivo_by_id(relatorio_existente['arquivo_id'])
            if arquivo_antigo:
                from app.services.file_service import FileService
                path_abs = FileService.resolve_path(arquivo_antigo['path_armazenamento'])
                if os.path.exists(path_abs):
                    try:
                        os.remove(path_abs)
                    except Exception as e:
                        print(f"❌ Erro ao remover arquivo antigo: {e}")

            # Atualiza o relatório existente
            await self.relatorio_repo.update_relatorio_arquivo(
                relatorio_existente['id'],
                arquivo_criado['id'],
                status_relatorio_pendente['id']
            )
            relatorio_atualizado = await self.relatorio_repo.get_relatorio_by_id(relatorio_existente['id'])

            # Muda status da pendência para 'pendente de análise' (status customizado)
            await self._update_pendencia_para_analise(relatorio_data.pendencia_id)

            print(f"✅ Relatório reenviado para pendência {relatorio_data.pendencia_id}")
            return Relatorio.model_validate(relatorio_atualizado)
        else:
            # Primeiro envio - cria novo relatório
            novo_relatorio_data = await self.relatorio_repo.create_relatorio(
                contrato_id=contrato_id,
                arquivo_id=arquivo_criado['id'],
                status_id=status_relatorio_pendente['id'],
                data=relatorio_data.model_dump()
            )

            # Muda status da pendência para 'pendente de análise'
            await self._update_pendencia_para_analise(relatorio_data.pendencia_id)

            # === NOTIFICAÇÃO POR EMAIL PARA ADMINISTRADOR ===
            await self._notify_admin_new_report(contrato, pendencia, current_user)

            print(f"✅ Primeiro relatório enviado para pendência {relatorio_data.pendencia_id}")
            return Relatorio.model_validate(novo_relatorio_data)

    async def _update_pendencia_para_analise(self, pendencia_id: int):
        """Atualiza status da pendência para indicar que tem relatório aguardando análise"""
        # Atualiza para o novo status 'Aguardando Análise' (ID=4)
        await self.pendencia_repo.update_pendencia_status(pendencia_id, 4)
        print(f"✅ Pendência {pendencia_id} alterada para 'Aguardando Análise'")

    async def _notify_admin_new_report(self, contrato: dict, pendencia: dict, fiscal: Usuario):
        """Notifica administrador sobre novo relatório submetido"""
        try:
            # Busca usuário administrador
            admin_users = await self.usuario_repo.get_users_by_perfil("Administrador")
            if admin_users:
                admin = admin_users[0]  # Pega o primeiro admin encontrado

                from app.services.email_templates import EmailTemplates

                fiscal_data = {
                    'nome': fiscal.nome,
                    'email': fiscal.email
                }

                subject, body = EmailTemplates.report_submitted_notification(
                    admin_nome=admin['nome'],
                    contrato_data=contrato,
                    pendencia_data=pendencia,
                    fiscal_data=fiscal_data
                )

                from app.services.email_service import EmailService
                await EmailService.send_email(admin['email'], subject, body, is_html=True)

                print(f"✅ Email de notificação enviado para admin {admin['email']}")
        except Exception as e:
            print(f"❌ Erro ao enviar notificação para admin: {e}")

    async def analisar_relatorio(
        self,
        relatorio_id: int,
        analise_data: RelatorioAnalise,
        current_user: Optional[Usuario] = None,
        request: Optional[Request] = None
    ) -> Relatorio:
        relatorio = await self.relatorio_repo.get_relatorio_by_id(relatorio_id)
        if not relatorio:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relatório não encontrado")

        if not await self.usuario_repo.get_user_by_id(analise_data.aprovador_usuario_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário aprovador não encontrado")

        status_relatorio = await self.status_relatorio_repo.get_by_id(analise_data.status_id)
        if not status_relatorio:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status de relatório não encontrado")

        # Busca dados necessários para notificações
        contrato = await self.contrato_repo.find_contrato_by_id(relatorio['contrato_id'])
        pendencia = await self.pendencia_repo.get_pendencia_by_id(relatorio['pendencia_id'])
        fiscal = await self.usuario_repo.get_user_by_id(relatorio['fiscal_usuario_id'])

        # Atualiza o relatório
        relatorio_atualizado = await self.relatorio_repo.analise_relatorio(relatorio_id, analise_data.model_dump())

        # Processa baseado no status
        status_nome = status_relatorio['nome']

        if status_nome == 'Aprovado':
            # Aprova o relatório e conclui a pendência
            await self._aprovar_relatorio(relatorio, contrato, pendencia, fiscal, current_user, request)

        elif status_nome == 'Rejeitado com Pendência':
            # Rejeita o relatório e volta pendência para 'Pendente'
            await self._rejeitar_relatorio(relatorio, contrato, pendencia, fiscal, analise_data.observacoes_aprovador, current_user, request)

        return Relatorio.model_validate(relatorio_atualizado)

    async def _aprovar_relatorio(
        self,
        relatorio: dict,
        contrato: dict,
        pendencia: dict,
        fiscal: dict,
        current_user: Optional[Usuario] = None,
        request: Optional[Request] = None
    ):
        """Processa aprovação do relatório"""
        try:
            # Muda status da pendência para 'Concluída'
            status_concluida = next(s for s in await self.status_pendencia_repo.get_all() if s['nome'] == 'Concluída')
            await self.pendencia_repo.update_pendencia_status(pendencia['id'], status_concluida['id'])

            # Log de auditoria
            if current_user and contrato:
                try:
                    await audit_aprovar_relatorio(
                        conn=self.relatorio_repo.conn,
                        request=request,
                        usuario=current_user,
                        relatorio_id=relatorio['id'],
                        pendencia_titulo=pendencia['titulo'],
                        contrato_nr=contrato['nr_contrato'],
                        perfil_usado=current_user.perfil_ativo if hasattr(current_user, 'perfil_ativo') else None
                    )
                except Exception as e:
                    logger.warning(f"Erro ao criar log de auditoria para aprovação de relatório {relatorio['id']}: {e}")

            # Envia email de aprovação para o fiscal
            from app.services.email_templates import EmailTemplates
            subject, body = EmailTemplates.report_approved_notification(
                fiscal_nome=fiscal['nome'],
                contrato_data=contrato,
                pendencia_data=pendencia
            )

            from app.services.email_service import EmailService
            await EmailService.send_email(fiscal['email'], subject, body, is_html=True)

            print(f"✅ Relatório aprovado e email enviado para {fiscal['email']}")
        except Exception as e:
            print(f"❌ Erro ao processar aprovação: {e}")

    async def _rejeitar_relatorio(
        self,
        relatorio: dict,
        contrato: dict,
        pendencia: dict,
        fiscal: dict,
        observacoes: str = None,
        current_user: Optional[Usuario] = None,
        request: Optional[Request] = None
    ):
        """Processa rejeição do relatório"""
        try:
            # Volta status da pendência para 'Pendente' para que o fiscal possa reenviar
            status_pendente = next(s for s in await self.status_pendencia_repo.get_all() if s['nome'] == 'Pendente')
            await self.pendencia_repo.update_pendencia_status(pendencia['id'], status_pendente['id'])

            # Log de auditoria
            if current_user and contrato:
                try:
                    await audit_rejeitar_relatorio(
                        conn=self.relatorio_repo.conn,
                        request=request,
                        usuario=current_user,
                        relatorio_id=relatorio['id'],
                        pendencia_titulo=pendencia['titulo'],
                        contrato_nr=contrato['nr_contrato'],
                        motivo=observacoes,
                        perfil_usado=current_user.perfil_ativo if hasattr(current_user, 'perfil_ativo') else None
                    )
                except Exception as e:
                    logger.warning(f"Erro ao criar log de auditoria para rejeição de relatório {relatorio['id']}: {e}")

            # Envia email de rejeição para o fiscal
            from app.services.email_templates import EmailTemplates
            subject, body = EmailTemplates.report_rejected_notification(
                fiscal_nome=fiscal['nome'],
                contrato_data=contrato,
                pendencia_data=pendencia,
                observacoes=observacoes
            )

            from app.services.email_service import EmailService
            await EmailService.send_email(fiscal['email'], subject, body, is_html=True)

            print(f"✅ Relatório rejeitado e email enviado para {fiscal['email']}")
        except Exception as e:
            print(f"❌ Erro ao processar rejeição: {e}")