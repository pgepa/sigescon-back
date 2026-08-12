# app/api/routers/contrato_router.py
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from typing import List, Optional
from datetime import date

from app.core.database import get_connection
from app.schemas.usuario_schema import Usuario
from app.api.dependencies import get_current_user, get_current_admin_user, get_current_user_with_context

# Repositórios
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.usuario_repo import UsuarioRepository
from app.repositories.contratado_repo import ContratadoRepository as ContratadoRepo
from app.repositories.modalidade_repo import ModalidadeRepository
from app.repositories.status_repo import StatusRepository
from app.repositories.arquivo_repo import ArquivoRepository
from app.api.permissions import admin_required, PermissionChecker

# Services
from app.services.contrato_service import ContratoService
from app.services.file_service import FileService

# Schemas
from app.schemas.contrato_schema import (
    Contrato, ContratoCreate, ContratoUpdate, ContratoPaginated, ArquivoContrato, ArquivoContratoList
)

router = APIRouter(
    prefix="/contratos",
    tags=["Contratos"]
)

# --- Injeção de Dependências ---
def get_contrato_service(conn: asyncpg.Connection = Depends(get_connection)) -> ContratoService:
    return ContratoService(
        contrato_repo=ContratoRepository(conn),
        usuario_repo=UsuarioRepository(conn),
        contratado_repo=ContratadoRepo(conn),
        modalidade_repo=ModalidadeRepository(conn),
        status_repo=StatusRepository(conn),
        arquivo_repo=ArquivoRepository(conn),
        file_service=FileService()
    )

# --- Função auxiliar para criação de contrato ---
async def _create_contrato_logic(
    nr_contrato: str,
    objeto: str,
    data_inicio: date,
    data_fim: date,
    contratado_id: int,
    modalidade_id: int,
    status_id: int,
    gestor_id: Optional[int],
    fiscal_id: Optional[int],
    valor_anual: Optional[float],
    valor_global: Optional[float],
    base_legal: Optional[str],
    termos_contratuais: Optional[str],
    fiscal_substituto_id: Optional[int],
    pae: Optional[str],
    doe: Optional[str],
    data_doe: Optional[date],
    garantia: Optional[date],
    portaria_fiscal: Optional[str],
    nr_adesao_ata: Optional[str],
    documento_contrato: List[UploadFile],
    documento_portaria: Optional[UploadFile],
    documento_ata_registro: Optional[UploadFile],
    service: ContratoService,
    current_user: Usuario,
    request: Request
):
    """Lógica comum para criação de contrato"""
    contrato_create = ContratoCreate(
        nr_contrato=nr_contrato,
        objeto=objeto,
        data_inicio=data_inicio,
        data_fim=data_fim,
        contratado_id=contratado_id,
        modalidade_id=modalidade_id,
        status_id=status_id,
        gestor_id=gestor_id,
        fiscal_id=fiscal_id,
        valor_anual=valor_anual,
        valor_global=valor_global,
        base_legal=base_legal,
        termos_contratuais=termos_contratuais,
        fiscal_substituto_id=fiscal_substituto_id,
        pae=pae,
        doe=doe,
        data_doe=data_doe,
        garantia=garantia,
        portaria_fiscal=portaria_fiscal,
        nr_adesao_ata=nr_adesao_ata,
    )
    return await service.create_contrato(
        contrato_create, documento_contrato, current_user, request,
        documento_portaria=documento_portaria,
        documento_ata_registro=documento_ata_registro,
    )

# --- Endpoints ---

# Rota POST com barra final
@router.post("/", response_model=Contrato, status_code=status.HTTP_201_CREATED)
async def create_contrato_with_slash(
    request: Request,
    nr_contrato: str = Form(...),
    objeto: str = Form(...),
    data_inicio: date = Form(...),
    data_fim: date = Form(...),
    contratado_id: int = Form(...),
    modalidade_id: int = Form(...),
    status_id: int = Form(...),
    gestor_id: Optional[int] = Form(None),
    fiscal_id: Optional[int] = Form(None),
    valor_anual: Optional[float] = Form(None),
    valor_global: Optional[float] = Form(None),
    base_legal: Optional[str] = Form(None),
    termos_contratuais: Optional[str] = Form(None),
    fiscal_substituto_id: Optional[int] = Form(None),
    pae: Optional[str] = Form(None),
    doe: Optional[str] = Form(None),
    data_doe: Optional[date] = Form(None),
    garantia: Optional[date] = Form(None),
    portaria_fiscal: Optional[str] = Form(None),
    nr_adesao_ata: Optional[str] = Form(None),
    documento_contrato: List[UploadFile] = File(None),
    documento_portaria: Optional[UploadFile] = File(None),
    documento_ata_registro: Optional[UploadFile] = File(None),
    service: ContratoService = Depends(get_contrato_service),
    admin_user: Usuario = Depends(admin_required)
):
    """Cria um novo contrato (rota com barra final)"""
    return await _create_contrato_logic(
        nr_contrato, objeto, data_inicio, data_fim, contratado_id,
        modalidade_id, status_id, gestor_id, fiscal_id, valor_anual,
        valor_global, base_legal, termos_contratuais, fiscal_substituto_id,
        pae, doe, data_doe, garantia, portaria_fiscal, nr_adesao_ata,
        documento_contrato, documento_portaria, documento_ata_registro,
        service, admin_user, request
    )

# Rota POST sem barra final
@router.post("", response_model=Contrato, status_code=status.HTTP_201_CREATED)
async def create_contrato(
    request: Request,
    nr_contrato: str = Form(...),
    objeto: str = Form(...),
    data_inicio: date = Form(...),
    data_fim: date = Form(...),
    contratado_id: int = Form(...),
    modalidade_id: int = Form(...),
    status_id: int = Form(...),
    gestor_id: Optional[int] = Form(None),
    fiscal_id: Optional[int] = Form(None),
    valor_anual: Optional[float] = Form(None),
    valor_global: Optional[float] = Form(None),
    base_legal: Optional[str] = Form(None),
    termos_contratuais: Optional[str] = Form(None),
    fiscal_substituto_id: Optional[int] = Form(None),
    pae: Optional[str] = Form(None),
    doe: Optional[str] = Form(None),
    data_doe: Optional[date] = Form(None),
    garantia: Optional[date] = Form(None),
    portaria_fiscal: Optional[str] = Form(None),
    nr_adesao_ata: Optional[str] = Form(None),
    documento_contrato: List[UploadFile] = File(None),
    documento_portaria: Optional[UploadFile] = File(None),
    documento_ata_registro: Optional[UploadFile] = File(None),
    service: ContratoService = Depends(get_contrato_service),
    admin_user: Usuario = Depends(admin_required)
):
    """Cria um novo contrato (rota sem barra final)"""
    return await _create_contrato_logic(
        nr_contrato, objeto, data_inicio, data_fim, contratado_id,
        modalidade_id, status_id, gestor_id, fiscal_id, valor_anual,
        valor_global, base_legal, termos_contratuais, fiscal_substituto_id,
        pae, doe, data_doe, garantia, portaria_fiscal, nr_adesao_ata,
        documento_contrato, documento_portaria, documento_ata_registro,
        service, admin_user, request
    )


@router.get("/next-number", response_model=dict)
async def get_next_contract_number(
    service: ContratoService = Depends(get_contrato_service),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Retorna o próximo número de contrato disponível.
    Útil para sugerir um número ao criar um novo contrato.
    """
    next_number = await service.contrato_repo.get_next_available_nr_contrato()
    return {"next_number": next_number}

# Rota GET com barra final
@router.get("/", response_model=ContratoPaginated)
async def list_contratos_with_slash(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(10, ge=1, le=100, description="Itens por página"),
    nome: Optional[str] = Query(None, description="Filtrar por nome do contratado"),
    numero: Optional[str] = Query(None, description="Filtrar por número do contrato"),
    objeto: Optional[str] = Query(None, description="Filtrar por objeto do contrato"),
    status_id: Optional[int] = Query(None, description="Filtrar por status"),
    modalidade_id: Optional[int] = Query(None, description="Filtrar por modalidade"),
    contratado_id: Optional[int] = Query(None, description="Filtrar por contratado"),
    gestor_id: Optional[int] = Query(None, description="Filtrar por gestor"),
    fiscal_id: Optional[int] = Query(None, description="Filtrar por fiscal"),
    data_inicio: Optional[date] = Query(None, description="Data de início mínima"),
    data_fim: Optional[date] = Query(None, description="Data de fim máxima"),
    vencimento_30_dias: Optional[bool] = Query(None, description="Contratos vencendo em 30 dias"),
    vencimento_60_dias: Optional[bool] = Query(None, description="Contratos vencendo em 60 dias"),
    vencimento_90_dias: Optional[bool] = Query(None, description="Contratos vencendo em 90 dias"),
    tem_garantia: Optional[bool] = Query(None, description="Filtrar contratos com garantia"),
    garantia_prazo_dias: Optional[str] = Query(None, description="Filtrar por prazo de garantia"),
    service: ContratoService = Depends(get_contrato_service),
    current_user: Usuario = Depends(get_current_user)
):
    return await _list_contratos_logic(
        page, per_page, nome, numero, objeto, status_id, modalidade_id,
        contratado_id, gestor_id, fiscal_id, data_inicio, data_fim,
        vencimento_30_dias, vencimento_60_dias, vencimento_90_dias,
        tem_garantia, garantia_prazo_dias, service, current_user
    )

def _build_contratos_filters(gestor_id, fiscal_id, objeto, nr_contrato, status_id, pae, ano,
                              vencimento_dias, tem_garantia, garantia_prazo_dias, contratado_nome=None):
    filters = {
        'gestor_id': gestor_id, 'fiscal_id': fiscal_id, 'objeto': objeto,
        'nr_contrato': nr_contrato, 'status_id': status_id, 'pae': pae, 'ano': ano,
        'vencimento_dias': vencimento_dias, 'tem_garantia': tem_garantia,
        'garantia_prazo_dias': garantia_prazo_dias, 'contratado_nome': contratado_nome
    }
    return {k: v for k, v in filters.items() if v is not None}


def _build_order_by(sort_by: Optional[str], sort_order: Optional[str]) -> str:
    allowed = {
        'nr_contrato': 'c.nr_contrato',
        'contratado_nome': 'ct.nome',
        'data_fim': 'c.data_fim',
        'objeto': 'c.objeto',
        'total_aditivos': '(SELECT COUNT(*) FROM termo_aditivo ta WHERE ta.contrato_id = c.id AND ta.ativo = TRUE)',
    }
    col = allowed.get(sort_by, 'c.data_fim') if sort_by else 'c.data_fim'
    direction = 'ASC' if sort_order and sort_order.lower() == 'asc' else 'DESC'
    return f"{col} {direction}"


# Rota GET sem barra final
@router.get("", response_model=ContratoPaginated)
async def list_contratos(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    gestor_id: Optional[int] = Query(None),
    fiscal_id: Optional[int] = Query(None),
    objeto: Optional[str] = Query(None),
    nr_contrato: Optional[str] = Query(None),
    status_id: Optional[int] = Query(None),
    pae: Optional[str] = Query(None),
    ano: Optional[int] = Query(None),
    contratado_nome: Optional[str] = Query(None),
    vencimento_dias: Optional[str] = Query(None),
    tem_garantia: Optional[bool] = Query(None),
    garantia_prazo_dias: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None, description="Campo para ordenação"),
    sort_order: Optional[str] = Query(None, description="Direção: asc ou desc"),
    service: ContratoService = Depends(get_contrato_service),
    user_context: tuple = Depends(get_current_user_with_context)
):
    current_user, context = user_context
    active_filters = _build_contratos_filters(
        gestor_id, fiscal_id, objeto, nr_contrato, status_id, pae, ano,
        vencimento_dias, tem_garantia, garantia_prazo_dias, contratado_nome
    )
    order_by = _build_order_by(sort_by, sort_order)
    user_ctx = {'usuario_id': context.usuario_id, 'perfil_ativo_nome': context.perfil_ativo_nome}
    return await service.get_all_contratos(page=page, per_page=per_page, filters=active_filters,
                                           user_context=user_ctx, order_by=order_by)

# Rota sem barra final (para evitar redirects do frontend)
@router.get("", response_model=ContratoPaginated)
async def list_contratos_without_slash(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    gestor_id: Optional[int] = Query(None),
    fiscal_id: Optional[int] = Query(None),
    objeto: Optional[str] = Query(None),
    nr_contrato: Optional[str] = Query(None),
    status_id: Optional[int] = Query(None),
    pae: Optional[str] = Query(None),
    ano: Optional[int] = Query(None),
    contratado_nome: Optional[str] = Query(None),
    vencimento_dias: Optional[str] = Query(None),
    tem_garantia: Optional[bool] = Query(None),
    garantia_prazo_dias: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query(None),
    service: ContratoService = Depends(get_contrato_service),
    user_context: tuple = Depends(get_current_user_with_context)
):
    current_user, context = user_context
    active_filters = _build_contratos_filters(
        gestor_id, fiscal_id, objeto, nr_contrato, status_id, pae, ano,
        vencimento_dias, tem_garantia, garantia_prazo_dias, contratado_nome
    )
    order_by = _build_order_by(sort_by, sort_order)
    user_ctx = {'usuario_id': context.usuario_id, 'perfil_ativo_nome': context.perfil_ativo_nome}
    return await service.get_all_contratos(page=page, per_page=per_page, filters=active_filters,
                                           user_context=user_ctx, order_by=order_by)

@router.get("/{contrato_id}", response_model=Contrato)
async def get_contrato_by_id(
    contrato_id: int,
    service: ContratoService = Depends(get_contrato_service),
    user_context: tuple = Depends(get_current_user_with_context)
):
    current_user, context = user_context

    # Criar contexto do usuário para isolamento de dados
    user_ctx = {
        'usuario_id': context.usuario_id,
        'perfil_ativo_nome': context.perfil_ativo_nome
    }


    contrato = await service.get_contrato_by_id(contrato_id, user_context=user_ctx)
    if not contrato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    return contrato

@router.patch("/{contrato_id}", response_model=Contrato)
async def update_contrato(
    request: Request,
    contrato_id: int,
    # Campos opcionais do formulário - apenas os campos que podem ser atualizados
    nr_contrato: Optional[str] = Form(None),
    objeto: Optional[str] = Form(None),
    data_inicio: Optional[date] = Form(None),
    data_fim: Optional[date] = Form(None),
    contratado_id: Optional[int] = Form(None),
    modalidade_id: Optional[int] = Form(None),
    status_id: Optional[int] = Form(None),
    gestor_id: Optional[int] = Form(None),
    fiscal_id: Optional[int] = Form(None),
    valor_anual: Optional[float] = Form(None),
    valor_global: Optional[float] = Form(None),
    base_legal: Optional[str] = Form(None),
    termos_contratuais: Optional[str] = Form(None),
    fiscal_substituto_id: Optional[int] = Form(None),
    pae: Optional[str] = Form(None),
    doe: Optional[str] = Form(None),
    data_doe: Optional[date] = Form(None),
    garantia: Optional[date] = Form(None),
    portaria_fiscal: Optional[str] = Form(None),
    nr_adesao_ata: Optional[str] = Form(None),
    # Arquivos opcionais para upload
    documento_contrato: List[UploadFile] = File(None),
    documento_portaria: Optional[UploadFile] = File(None),
    documento_ata_registro: Optional[UploadFile] = File(None),
    service: ContratoService = Depends(get_contrato_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Atualiza um contrato existente. Aceita dados de formulário e múltiplos ficheiros opcionais.
    Requer permissão de administrador.
    """

    # Constrói objeto ContratoUpdate apenas com campos fornecidos
    update_data = {}

    form_fields = {
        'nr_contrato': nr_contrato,
        'objeto': objeto,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'contratado_id': contratado_id,
        'modalidade_id': modalidade_id,
        'status_id': status_id,
        'gestor_id': gestor_id,
        'fiscal_id': fiscal_id,
        'valor_anual': valor_anual,
        'valor_global': valor_global,
        'base_legal': base_legal,
        'termos_contratuais': termos_contratuais,
        'fiscal_substituto_id': fiscal_substituto_id,
        'pae': pae,
        'doe': doe,
        'data_doe': data_doe,
        'garantia': garantia,
        'portaria_fiscal': portaria_fiscal,
        'nr_adesao_ata': nr_adesao_ata,
    }

    for field, value in form_fields.items():
        if value is not None:
            update_data[field] = value

    contrato_update = ContratoUpdate(**update_data)

    updated_contrato = await service.update_contrato(
        contrato_id=contrato_id,
        contrato_update=contrato_update,
        documento_contrato=documento_contrato,
        current_user=admin_user,
        request=request,
        documento_portaria=documento_portaria,
        documento_ata_registro=documento_ata_registro,
    )

    if not updated_contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato não encontrado para atualização"
        )

    return updated_contrato

@router.delete("/{contrato_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contrato(contrato_id: int, service: ContratoService = Depends(get_contrato_service), admin_user: Usuario = Depends(admin_required)):
    await service.delete_contrato(contrato_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Rotas para gerenciamento de arquivos do contrato
# Rota sem barra final (original)
@router.get("/{contrato_id}/arquivos", response_model=ArquivoContratoList, summary="Listar arquivos do contrato")
async def listar_arquivos_contrato(
    contrato_id: int,
    service: ContratoService = Depends(get_contrato_service),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos os arquivos de um contrato específico.

    - **contrato_id**: ID do contrato

    Retorna uma lista com todos os arquivos associados ao contrato,
    incluindo informações como nome, tipo, tamanho e data de criação.
    """
    return await service.get_arquivos_contrato(contrato_id)

# Rota com barra final (para evitar redirects do frontend)
@router.get("/{contrato_id}/arquivos/", response_model=ArquivoContratoList, summary="Listar arquivos do contrato")
async def listar_arquivos_contrato_with_slash(
    contrato_id: int,
    service: ContratoService = Depends(get_contrato_service),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos os arquivos de um contrato específico.

    - **contrato_id**: ID do contrato

    Retorna uma lista com todos os arquivos associados ao contrato,
    incluindo informações como nome, tipo, tamanho e data de criação.
    """
    return await service.get_arquivos_contrato(contrato_id)

@router.get("/{contrato_id}/arquivos/{arquivo_id}/download", summary="Download de arquivo do contrato")
async def download_arquivo_contrato(
    contrato_id: int,
    arquivo_id: int,
    service: ContratoService = Depends(get_contrato_service),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Download de um arquivo específico de um contrato.

    - **contrato_id**: ID do contrato
    - **arquivo_id**: ID do arquivo a ser baixado

    Retorna o arquivo para download com o nome original e tipo MIME correto.
    """
    arquivo = await service.get_arquivo_contrato(contrato_id, arquivo_id)

    # Verificação de existência física do arquivo
    import os
    from app.services.file_service import FileService
    path_completo = FileService.resolve_path(arquivo['path_armazenamento'])
    if not os.path.exists(path_completo):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo físico não encontrado no servidor"
        )

    nome_original = arquivo['nome_arquivo']

    return FileResponse(
        path=path_completo,
        filename=nome_original,
        media_type='application/octet-stream'
    )

@router.delete("/{contrato_id}/arquivos/{arquivo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir arquivo do contrato")
async def excluir_arquivo_contrato(
    contrato_id: int,
    arquivo_id: int,
    service: ContratoService = Depends(get_contrato_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Remove um arquivo específico de um contrato.

    - **contrato_id**: ID do contrato
    - **arquivo_id**: ID do arquivo a ser removido

    **Atenção**: Esta operação remove permanentemente o arquivo tanto do banco
    de dados quanto do sistema de arquivos. Requer permissão de administrador.
    """
    await service.delete_arquivo_contrato(contrato_id, arquivo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Endpoints dedicados para upload de arquivos por tipo ---

@router.post(
    "/{contrato_id}/arquivos/portaria",
    status_code=status.HTTP_201_CREATED,
    summary="Upload de arquivo da Portaria de Designação",
)
async def upload_portaria(
    contrato_id: int,
    arquivo: UploadFile = File(...),
    service: ContratoService = Depends(get_contrato_service),
    admin_user: Usuario = Depends(admin_required),
):
    """Faz upload de um arquivo de portaria de designação do fiscal."""
    return await service.upload_arquivo_tipado(contrato_id, arquivo, tipo_vinculo="portaria")


@router.post(
    "/{contrato_id}/arquivos/ata",
    status_code=status.HTTP_201_CREATED,
    summary="Upload de arquivo da Ata de Registro de Preço",
)
async def upload_ata(
    contrato_id: int,
    arquivo: UploadFile = File(...),
    service: ContratoService = Depends(get_contrato_service),
    admin_user: Usuario = Depends(admin_required),
):
    """Faz upload de um arquivo da Ata de Registro de Preço."""
    return await service.upload_arquivo_tipado(contrato_id, arquivo, tipo_vinculo="ata")