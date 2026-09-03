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
from app.services.audit_integration import audit_finalizar_relatorio

# Schemas
from app.schemas.relatorio_schema import Relatorio, RelatorioCreate
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

    async def _verificar_fiscal_ou_admin(self, contrato: dict, current_user: Usuario) -> None:
        """Só o fiscal titular do contrato ou um Administrador podem mexer no
        relatório dele — sem papel de Gestor aqui, o fiscal é quem escreve e
        quem finaliza, não tem aprovação de terceiros no meio."""
        perfil_usuario = await self.perfil_repo.get_perfil_by_id(current_user.perfil_id)
        is_admin = perfil_usuario and perfil_usuario.get("nome") == "Administrador"
        if not is_admin and contrato['fiscal_id'] != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: Você não é o fiscal deste contrato.")

    async def submit_relatorio(self, contrato_id: int, relatorio_data: RelatorioCreate, file: UploadFile, current_user: Usuario) -> Relatorio:
        """Salva o relatório como Rascunho — o fiscal pode chamar isso quantas
        vezes quiser pra ir editando (cada chamada substitui o arquivo/observações
        do rascunho atual), até decidir finalizar com `finalizar_relatorio`.
        Não existe etapa de análise/aprovação: a pendência só muda de status
        quando o relatório é finalizado."""
        contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
        if not contrato:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

        await self._verificar_fiscal_ou_admin(contrato, current_user)

        pendencia = await self.pendencia_repo.get_pendencia_by_id(relatorio_data.pendencia_id)
        if not pendencia:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pendência não encontrada")

        # Verifica se já existe relatório (rascunho) para esta pendência
        relatorios_existentes = await self.relatorio_repo.get_relatorios_by_pendencia_id(relatorio_data.pendencia_id)

        if relatorios_existentes and relatorios_existentes[0]['status_relatorio'] == 'Salvo':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este relatório já foi finalizado (Salvo) e não pode mais ser editado."
            )

        # Salva o novo arquivo
        nome_original, path, tamanho = await self.file_service.save_upload_file(contrato_id, file)

        arquivo_criado = await self.arquivo_repo.create_arquivo(
            nome_arquivo=nome_original,
            path_armazenamento=path,
            tipo_arquivo=file.content_type,
            tamanho_bytes=tamanho,
            contrato_id=contrato_id
        )

        status_rascunho = next(s for s in await self.status_relatorio_repo.get_all() if s['nome'] == 'Rascunho')

        # Se já existe rascunho para esta pendência, atualiza em vez de criar novo
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

            # Atualiza o rascunho existente
            await self.relatorio_repo.update_relatorio_arquivo(
                relatorio_existente['id'],
                arquivo_criado['id'],
                status_rascunho['id']
            )
            relatorio_atualizado = await self.relatorio_repo.get_relatorio_by_id(relatorio_existente['id'])

            print(f"✅ Rascunho atualizado para pendência {relatorio_data.pendencia_id}")
            return Relatorio.model_validate(relatorio_atualizado)
        else:
            # Primeiro salvamento - cria novo relatório como Rascunho
            novo_relatorio_data = await self.relatorio_repo.create_relatorio(
                contrato_id=contrato_id,
                arquivo_id=arquivo_criado['id'],
                status_id=status_rascunho['id'],
                data=relatorio_data.model_dump()
            )

            print(f"✅ Rascunho criado para pendência {relatorio_data.pendencia_id}")
            return Relatorio.model_validate(novo_relatorio_data)

    async def finalizar_relatorio(
        self,
        contrato_id: int,
        relatorio_id: int,
        current_user: Usuario,
        request: Optional[Request] = None
    ) -> Relatorio:
        """Marca o relatório como Salvo (final) e conclui a pendência direto —
        sem aprovação de ninguém. Só o fiscal titular do contrato (ou admin)
        pode finalizar, e só um relatório em Rascunho pode ser finalizado."""
        relatorio = await self.relatorio_repo.get_relatorio_by_id(relatorio_id)
        if not relatorio or relatorio['contrato_id'] != contrato_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relatório não encontrado")

        contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
        if not contrato:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

        await self._verificar_fiscal_ou_admin(contrato, current_user)

        if relatorio['status_relatorio'] != 'Rascunho':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Só é possível finalizar um relatório em Rascunho (status atual: {relatorio['status_relatorio']})."
            )

        pendencia = await self.pendencia_repo.get_pendencia_by_id(relatorio['pendencia_id'])
        fiscal = await self.usuario_repo.get_user_by_id(relatorio['fiscal_usuario_id'])

        status_salvo = next(s for s in await self.status_relatorio_repo.get_all() if s['nome'] == 'Salvo')
        relatorio_atualizado = await self.relatorio_repo.finalizar_relatorio(relatorio_id, status_salvo['id'])

        # Conclui a pendência direto — sem etapa de análise
        status_concluida = next(s for s in await self.status_pendencia_repo.get_all() if s['nome'] == 'Concluída')
        await self.pendencia_repo.update_pendencia_status(pendencia['id'], status_concluida['id'])

        # Log de auditoria
        try:
            await audit_finalizar_relatorio(
                conn=self.relatorio_repo.conn,
                request=request,
                usuario=current_user,
                relatorio_id=relatorio_id,
                pendencia_titulo=pendencia['titulo'],
                contrato_nr=contrato['nr_contrato'],
                perfil_usado=current_user.perfil_ativo if hasattr(current_user, 'perfil_ativo') else None
            )
        except Exception as e:
            logger.warning(f"Erro ao criar log de auditoria para finalização de relatório {relatorio_id}: {e}")

        # Notifica administrador (informativo — não precisa aprovar nada)
        await self._notify_admin_new_report(contrato, pendencia, fiscal)

        print(f"✅ Relatório {relatorio_id} finalizado (Salvo) e pendência {pendencia['id']} concluída")
        return Relatorio.model_validate(relatorio_atualizado)

    async def _notify_admin_new_report(self, contrato: dict, pendencia: dict, fiscal) -> None:
        """Notifica administrador que um relatório foi finalizado — só informativo,
        não há ação de aprovação esperada."""
        try:
            # Busca usuário administrador
            admin_users = await self.usuario_repo.get_users_by_perfil("Administrador")
            if admin_users:
                admin = admin_users[0]  # Pega o primeiro admin encontrado

                from app.services.email_templates import EmailTemplates

                fiscal_data = {
                    'nome': fiscal['nome'],
                    'email': fiscal['email']
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

