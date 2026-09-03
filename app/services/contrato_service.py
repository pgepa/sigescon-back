# app/services/contrato_service.py
import math
from typing import List, Optional, Dict
from fastapi import HTTPException, status, UploadFile, Request
import logging

# Repositórios
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.usuario_repo import UsuarioRepository
from app.repositories.contratado_repo import ContratadoRepository as ContratadoRepo
from app.repositories.modalidade_repo import ModalidadeRepository
from app.repositories.status_repo import StatusRepository
from app.repositories.arquivo_repo import ArquivoRepository

# Services
from app.services.file_service import FileService
from app.services.email_service import EmailService
from app.services.audit_integration import (
    audit_criar_contrato,
    audit_atualizar_contrato
)

# Schemas
from app.schemas.contrato_schema import (
    Contrato, ContratoCreate, ContratoUpdate,
    ContratoPaginated, ContratoList
)
from app.schemas.usuario_schema import Usuario

logger = logging.getLogger(__name__)
class ContratoService:
    def __init__(self,
                 contrato_repo: ContratoRepository,
                 usuario_repo: UsuarioRepository,
                 contratado_repo: ContratadoRepo,
                 modalidade_repo: ModalidadeRepository,
                 status_repo: StatusRepository,
                 arquivo_repo: ArquivoRepository,
                 file_service: FileService):
        self.contrato_repo = contrato_repo
        self.usuario_repo = usuario_repo
        self.contratado_repo = contratado_repo
        self.modalidade_repo = modalidade_repo
        self.status_repo = status_repo
        self.arquivo_repo = arquivo_repo
        self.file_service = file_service

    async def _validate_foreign_keys(self, contrato: ContratoCreate | ContratoUpdate):
        """Valida se todas as chaves estrangeiras existem"""
        print(f"Validando foreign keys para: {contrato}")
        
        if hasattr(contrato, 'contratado_id') and contrato.contratado_id:
            print(f"Validando contratado_id: {contrato.contratado_id}")
            if not await self.contratado_repo.get_contratado_by_id(contrato.contratado_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contratado não encontrado")
        
        if hasattr(contrato, 'modalidade_id') and contrato.modalidade_id:
            print(f"Validando modalidade_id: {contrato.modalidade_id}")
            if not await self.modalidade_repo.get_modalidade_by_id(contrato.modalidade_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modalidade não encontrada")
        
        if hasattr(contrato, 'status_id') and contrato.status_id:
            print(f"Validando status_id: {contrato.status_id}")
            if not await self.status_repo.get_status_by_id(contrato.status_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status não encontrado")
        
        if hasattr(contrato, 'gestor_id') and contrato.gestor_id:
            print(f"Validando gestor_id: {contrato.gestor_id}")
            if not await self.usuario_repo.get_user_by_id(contrato.gestor_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gestor não encontrado")
        
        if hasattr(contrato, 'fiscal_id') and contrato.fiscal_id:
            print(f"Validando fiscal_id: {contrato.fiscal_id}")
            if not await self.usuario_repo.get_user_by_id(contrato.fiscal_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiscal não encontrado")
        
        if hasattr(contrato, 'fiscal_substituto_id') and contrato.fiscal_substituto_id:
            print(f"Validando fiscal_substituto_id: {contrato.fiscal_substituto_id}")
            if not await self.usuario_repo.get_user_by_id(contrato.fiscal_substituto_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiscal Substituto não encontrado")
        
        print("Todas as validações de foreign key passaram")

    async def _send_contract_assignment_email(self, contrato_data: Dict, fiscal_id: int, gestor_id: int, is_update: bool = False, old_fiscal_id: Optional[int] = None):
        """Envia emails de notificação para fiscal e gestor quando um contrato é criado ou atualizado"""
        from app.services.email_templates import EmailTemplates
        
        # Email para o fiscal (novo ou atual)
        if fiscal_id:
            fiscal = await self.usuario_repo.get_user_by_id(fiscal_id)
            if fiscal:
                subject, body = EmailTemplates.contract_assignment_fiscal(
                    fiscal_nome=fiscal['nome'],
                    contrato_data=contrato_data,
                    is_new=not is_update
                )
                await EmailService.send_email(fiscal['email'], subject, body, is_html=True)

        # Email para o gestor
        if gestor_id:
            gestor = await self.usuario_repo.get_user_by_id(gestor_id)
            if gestor:
                # Busca dados do fiscal para incluir no email do gestor
                fiscal_data = None
                if fiscal_id:
                    fiscal = await self.usuario_repo.get_user_by_id(fiscal_id)
                    if fiscal:
                        fiscal_data = {'nome': fiscal['nome'], 'email': fiscal['email']}
                
                subject, body = EmailTemplates.contract_assignment_manager(
                    gestor_nome=gestor['nome'],
                    contrato_data=contrato_data,
                    fiscal_data=fiscal_data,
                    is_new=not is_update
                )
                await EmailService.send_email(gestor['email'], subject, body, is_html=True)

        # Se houve mudança de fiscal, notifica o fiscal anterior
        if is_update and old_fiscal_id and old_fiscal_id != fiscal_id:
            old_fiscal = await self.usuario_repo.get_user_by_id(old_fiscal_id)
            if old_fiscal:
                # Busca nome do novo fiscal para incluir na notificação
                novo_fiscal_nome = None
                if fiscal_id:
                    novo_fiscal = await self.usuario_repo.get_user_by_id(fiscal_id)
                    if novo_fiscal:
                        novo_fiscal_nome = novo_fiscal['nome']
                
                subject, body = EmailTemplates.contract_transfer_notification(
                    fiscal_nome=old_fiscal['nome'],
                    contrato_data=contrato_data,
                    novo_fiscal_nome=novo_fiscal_nome
                )
                await EmailService.send_email(old_fiscal['email'], subject, body, is_html=True)

    async def _save_typed_file(self, contrato_id: int, file: UploadFile, tipo_vinculo: str) -> None:
        """Salva um arquivo com tipo_vinculo específico (portaria, ata, etc.)"""
        if not file or not file.filename or not file.filename.strip():
            return
        nome_original, file_path, file_size = await self.file_service.save_upload_file(
            contrato_id, file
        )
        await self.arquivo_repo.create_arquivo(
            nome_arquivo=nome_original,
            path_armazenamento=file_path,
            tipo_arquivo=file.content_type,
            tamanho_bytes=file_size,
            contrato_id=contrato_id,
            tipo_vinculo=tipo_vinculo,
        )

    async def create_contrato(
        self,
        contrato_create: ContratoCreate,
        files: Optional[List[UploadFile]] = None,
        current_user: Optional[Usuario] = None,
        request: Optional[Request] = None,
        documento_portaria: Optional[UploadFile] = None,
        documento_ata_registro: Optional[UploadFile] = None,
    ) -> Contrato:
        """Cria um novo contrato e, opcionalmente, anexa múltiplos arquivos"""

        # Dados recebidos validados pelo Pydantic

        # Validação de chaves estrangeiras
        await self._validate_foreign_keys(contrato_create)

        # Validação de número duplicado
        if await self.contrato_repo.exists_nr_contrato(contrato_create.nr_contrato):
            next_available = await self.contrato_repo.get_next_available_nr_contrato()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um contrato ativo com o número '{contrato_create.nr_contrato}'. Sugestão: use o número '{next_available}'."
            )

        # Cria o contrato primeiro para obter um ID
        new_contrato_data = await self.contrato_repo.create_contrato(contrato_create)
        contrato_id = new_contrato_data['id']

        # Processamento de arquivos do contrato
        if files and any(file.filename for file in files if file):
            # Filtra apenas arquivos válidos
            valid_files = [file for file in files if file and file.filename and file.filename.strip()]

            if valid_files:
                saved_files = await self.file_service.save_multiple_upload_files(contrato_id, valid_files)

                # Salva cada arquivo no banco de dados
                for file_info in saved_files:
                    arquivo_data = await self.arquivo_repo.create_arquivo(
                        nome_arquivo=file_info['original_filename'],
                        path_armazenamento=file_info['file_path'],
                        tipo_arquivo=file_info['content_type'],
                        tamanho_bytes=file_info['file_size'],
                        contrato_id=contrato_id
                    )
                    # Vincula o ID do arquivo ao contrato
                    await self.arquivo_repo.link_arquivo_to_contrato(arquivo_data['id'], contrato_id)

        # Processamento dos arquivos de portaria e ata
        if documento_portaria:
            try:
                await self._save_typed_file(contrato_id, documento_portaria, 'portaria')
            except Exception as e:
                logger.warning(f"Erro ao salvar arquivo da portaria para contrato {contrato_id}: {e}")

        if documento_ata_registro:
            try:
                await self._save_typed_file(contrato_id, documento_ata_registro, 'ata')
            except Exception as e:
                logger.warning(f"Erro ao salvar arquivo da ata para contrato {contrato_id}: {e}")

        # Retorna o contrato completo com JOINs
        contrato_response = Contrato.model_validate(new_contrato_data)

        # Log de auditoria
        if current_user:
            try:
                await audit_criar_contrato(
                    conn=self.contrato_repo.conn,
                    request=request,
                    usuario=current_user,
                    contrato_id=contrato_id,
                    dados_contrato={
                        'nr_contrato': contrato_create.nr_contrato,
                        'objeto': contrato_create.objeto,
                        'contratado_id': contrato_create.contratado_id,
                        'gestor_id': contrato_create.gestor_id,
                        'fiscal_id': contrato_create.fiscal_id,
                        'valor_global': str(contrato_create.valor_global) if contrato_create.valor_global else None,
                        'data_inicio': str(contrato_create.data_inicio),
                        'data_fim': str(contrato_create.data_fim)
                    },
                    perfil_usado=current_user.perfil_ativo if hasattr(current_user, 'perfil_ativo') else None
                )
            except Exception as e:
                logger.warning(f"Erro ao criar log de auditoria para contrato {contrato_id}: {e}")

        # Envio de emails de notificação
        try:
            await self._send_contract_assignment_email(
                contrato_data=new_contrato_data,
                fiscal_id=contrato_create.fiscal_id,
                gestor_id=contrato_create.gestor_id,
                is_update=False
            )
        except Exception as e:
            # Log do erro, mas não falha a criação do contrato
            logger.warning(f"Erro ao enviar emails de notificação para contrato {contrato_id}: {e}")

        return contrato_response

    async def get_contrato_by_id(self, contrato_id: int, user_context: Optional[Dict] = None) -> Optional[Contrato]:
        contrato_data = await self.contrato_repo.find_contrato_by_id(contrato_id, user_context=user_context)
        if contrato_data:
            return Contrato.model_validate(contrato_data)
        return None

    async def get_all_contratos(self, page: int, per_page: int, filters: Optional[Dict] = None, user_context: Optional[Dict] = None, order_by: str = 'c.data_fim DESC') -> ContratoPaginated:
        offset = (page - 1) * per_page
        contratos_data, total_items = await self.contrato_repo.get_all_contratos(
            filters=filters,
            limit=per_page,
            offset=offset,
            user_context=user_context,
            order_by=order_by
        )
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
        return ContratoPaginated(
            data=[ContratoList.model_validate(c) for c in contratos_data],
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            per_page=per_page
        )

    async def update_contrato(
        self,
        contrato_id: int,
        contrato_update: ContratoUpdate,
        documento_contrato: Optional[List[UploadFile]] = None,
        current_user: Optional[Usuario] = None,
        request: Optional[Request] = None,
        documento_portaria: Optional[UploadFile] = None,
        documento_ata_registro: Optional[UploadFile] = None,
    ) -> Optional[Contrato]:
        """
        Atualiza um contrato existente, incluindo upload de múltiplos arquivos opcionais.
        """

        try:
            # Verifica se o contrato existe
            existing_contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
            if not existing_contrato:
                return None

            # Valida chaves estrangeiras antes da atualização
            print(f"\n=== DEBUG - Iniciando validação foreign keys ===")
            await self._validate_foreign_keys(contrato_update)
            print(f"=== DEBUG - Validação foreign keys concluída ===\n")
            
            # Se está atualizando o número do contrato, verifica se já existe
            print(f"\n=== DEBUG SERVICE - Verificação nr_contrato ===")
            print(f"hasattr(contrato_update, 'nr_contrato'): {hasattr(contrato_update, 'nr_contrato')}")
            print(f"contrato_update.nr_contrato: {contrato_update.nr_contrato}")
            print(f"Condição completa: {hasattr(contrato_update, 'nr_contrato') and contrato_update.nr_contrato}")
            
            if hasattr(contrato_update, 'nr_contrato') and contrato_update.nr_contrato:
                print("Executando validação de nr_contrato duplicado...")
                if await self.contrato_repo.exists_nr_contrato(contrato_update.nr_contrato, exclude_id=contrato_id):
                    next_available = await self.contrato_repo.get_next_available_nr_contrato()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail=f"Já existe um contrato ativo com o número '{contrato_update.nr_contrato}'. Sugestão: use o número '{next_available}'."
                    )
            else:
                print("Validação de nr_contrato pulada - campo é None ou vazio")
            print(f"=== FIM DEBUG SERVICE ===\n")

            # Processa arquivos se fornecidos
            print(f"\n=== DEBUG - Processamento de arquivos ===")
            print(f"documento_contrato: {documento_contrato}")
            print(f"Tem arquivos: {documento_contrato and any(file.filename for file in documento_contrato if file)}")
            
            if documento_contrato and any(file.filename for file in documento_contrato if file):
                print("Iniciando processamento de arquivos...")
                # Filtra apenas arquivos válidos
                valid_files = [file for file in documento_contrato if file and file.filename and file.filename.strip()]
                print(f"Arquivos válidos: {len(valid_files)}")

                if valid_files:
                    print("Salvando arquivos...")
                    # Salva os novos arquivos
                    saved_files = await self.file_service.save_multiple_upload_files(contrato_id, valid_files)
                    print(f"Arquivos salvos: {len(saved_files)}")

                    # Salva cada arquivo no banco de dados
                    for i, file_info in enumerate(saved_files):
                        print(f"Salvando arquivo {i+1} no banco: {file_info['original_filename']}")
                        arquivo_data = await self.arquivo_repo.create_arquivo(
                            nome_arquivo=file_info['original_filename'],
                            path_armazenamento=file_info['file_path'],
                            tipo_arquivo=file_info['content_type'],
                            tamanho_bytes=file_info['file_size'],
                            contrato_id=contrato_id
                        )
                        print(f"Arquivo criado no banco: {arquivo_data}")
                        # Vincula o ID do arquivo ao contrato
                        print(f"Vinculando arquivo {arquivo_data['id']} ao contrato {contrato_id}")
                        await self.arquivo_repo.link_arquivo_to_contrato(arquivo_data['id'], contrato_id)
                        print(f"Arquivo {i+1} processado com sucesso")
            else:
                print("Nenhum arquivo para processar")
            print(f"=== FIM DEBUG - Processamento de arquivos ===\n")

            # Processamento dos arquivos de portaria e ata
            if documento_portaria:
                try:
                    await self._save_typed_file(contrato_id, documento_portaria, 'portaria')
                except Exception as e:
                    logger.warning(f"Erro ao salvar arquivo da portaria para contrato {contrato_id}: {e}")

            if documento_ata_registro:
                try:
                    await self._save_typed_file(contrato_id, documento_ata_registro, 'ata')
                except Exception as e:
                    logger.warning(f"Erro ao salvar arquivo da ata para contrato {contrato_id}: {e}")

            # Executa a atualização no banco (método correto)
            print(f"\n=== DEBUG - Chamando repositório update_contrato ===")
            print(f"contrato_id: {contrato_id} (tipo: {type(contrato_id).__name__})")
            print(f"contrato_update: {contrato_update}")
            updated_contrato = await self.contrato_repo.update_contrato(contrato_id, contrato_update)
            print(f"Resultado do repositório: {updated_contrato}")
            print(f"=== FIM DEBUG - Repositório ===\n")

            # Log de auditoria
            if current_user and existing_contrato:
                try:
                    # Preparar dados anteriores
                    dados_anteriores = {
                        'objeto': existing_contrato.get('objeto'),
                        'valor_global': str(existing_contrato.get('valor_global')) if existing_contrato.get('valor_global') else None,
                        'gestor_id': existing_contrato.get('gestor_id'),
                        'fiscal_id': existing_contrato.get('fiscal_id'),
                        'data_inicio': str(existing_contrato.get('data_inicio')) if existing_contrato.get('data_inicio') else None,
                        'data_fim': str(existing_contrato.get('data_fim')) if existing_contrato.get('data_fim') else None
                    }

                    # Preparar dados novos
                    dados_novos = {}
                    if contrato_update.objeto is not None:
                        dados_novos['objeto'] = contrato_update.objeto
                    if contrato_update.valor_global is not None:
                        dados_novos['valor_global'] = str(contrato_update.valor_global)
                    if contrato_update.gestor_id is not None:
                        dados_novos['gestor_id'] = contrato_update.gestor_id
                    if contrato_update.fiscal_id is not None:
                        dados_novos['fiscal_id'] = contrato_update.fiscal_id
                    if contrato_update.data_inicio is not None:
                        dados_novos['data_inicio'] = str(contrato_update.data_inicio)
                    if contrato_update.data_fim is not None:
                        dados_novos['data_fim'] = str(contrato_update.data_fim)

                    await audit_atualizar_contrato(
                        conn=self.contrato_repo.conn,
                        request=request,
                        usuario=current_user,
                        contrato_id=contrato_id,
                        nr_contrato=existing_contrato['nr_contrato'],
                        dados_anteriores=dados_anteriores,
                        dados_novos=dados_novos,
                        perfil_usado=current_user.perfil_ativo if hasattr(current_user, 'perfil_ativo') else None
                    )
                except Exception as e:
                    logger.warning(f"Erro ao criar log de auditoria para contrato {contrato_id}: {e}")

            return updated_contrato
            
        except Exception as e:
            logging.error(f"Erro ao atualizar contrato {contrato_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro interno ao atualizar contrato: {str(e)}"
            )

    async def delete_contrato(self, contrato_id: int) -> bool:
        if not await self.contrato_repo.find_contrato_by_id(contrato_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
        return await self.contrato_repo.delete_contrato(contrato_id)

    # Métodos para gerenciamento de arquivos do contrato
    async def get_arquivos_contrato(self, contrato_id: int) -> List[Dict]:
        """Lista todos os arquivos de um contrato específico"""
        # Verifica se o contrato existe
        contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
        if not contrato:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contrato não encontrado"
            )

        arquivos = await self.contrato_repo.get_arquivos_contrato(contrato_id)
        total_arquivos = await self.contrato_repo.count_arquivos_contrato(contrato_id)

        return {
            "arquivos": arquivos,
            "total_arquivos": total_arquivos,
            "contrato_id": contrato_id
        }

    async def get_arquivo_contrato(self, contrato_id: int, arquivo_id: int) -> Optional[Dict]:
        """Obtém um arquivo específico de um contrato"""
        # Verifica se o contrato existe
        contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
        if not contrato:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contrato não encontrado"
            )

        arquivo = await self.contrato_repo.get_arquivo_by_id(arquivo_id, contrato_id)
        if not arquivo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo não encontrado neste contrato"
            )

        return arquivo

    async def delete_arquivo_contrato(self, contrato_id: int, arquivo_id: int) -> bool:
        """Remove um arquivo específico de um contrato"""
        # Verifica se o contrato existe
        contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
        if not contrato:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contrato não encontrado"
            )

        # Busca o arquivo para verificar se existe e obter o path
        arquivo = await self.contrato_repo.get_arquivo_by_id(arquivo_id, contrato_id)
        if not arquivo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo não encontrado neste contrato"
            )

        try:
            # VALIDAÇÃO RESTRITIVA: Verifica se é um arquivo de relatório
            is_relatorio_arquivo = await self.contrato_repo.is_arquivo_de_relatorio(arquivo_id)

            if is_relatorio_arquivo:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Arquivos de relatórios fiscais não podem ser excluídos pois estão vinculados a pendências. "
                           "Apenas arquivos contratuais podem ser removidos."
                )

            # VALIDAÇÃO ADICIONAL: Verifica se arquivo contratual está sendo usado por relatórios
            relatorios_vinculados = await self.contrato_repo.check_arquivo_used_in_relatorios(arquivo_id)

            if relatorios_vinculados:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Este arquivo contratual não pode ser excluído porque está sendo usado por {len(relatorios_vinculados)} relatório(s) fiscal(is). "
                           f"Para excluir este arquivo, primeiro remova ou substitua os relatórios que o utilizam."
                )

            # Remove o arquivo do banco de dados
            deleted = await self.contrato_repo.delete_arquivo(arquivo_id, contrato_id)

            if deleted:
                # Remove o arquivo físico do sistema de arquivos
                await self.file_service.delete_file(arquivo['path_armazenamento'])

            return deleted

        except HTTPException:
            # Re-propaga HTTPExceptions (incluindo a nossa validação acima)
            raise
        except Exception as e:
            logging.error(f"Erro ao deletar arquivo {arquivo_id} do contrato {contrato_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro interno ao deletar arquivo: {str(e)}"
            )

    async def upload_arquivo_tipado(
        self, contrato_id: int, file: UploadFile, tipo_vinculo: str
    ) -> Dict:
        """Upload de arquivo com tipo_vinculo específico (portaria, ata, etc.)"""
        contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
        if not contrato:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contrato não encontrado"
            )

        if not file or not file.filename or not file.filename.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo não fornecido"
            )

        nome_original, file_path, file_size = await self.file_service.save_upload_file(
            contrato_id, file
        )
        arquivo_data = await self.arquivo_repo.create_arquivo(
            nome_arquivo=nome_original,
            path_armazenamento=file_path,
            tipo_arquivo=file.content_type,
            tamanho_bytes=file_size,
            contrato_id=contrato_id,
            tipo_vinculo=tipo_vinculo,
        )
        return arquivo_data