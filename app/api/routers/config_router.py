# app/api/routers/config_router.py
import asyncpg
from fastapi import APIRouter, Depends, status, File, UploadFile, Request
from fastapi.responses import FileResponse
from typing import List, Optional

from app.core.database import get_connection
from app.schemas.usuario_schema import Usuario
from app.api.permissions import admin_required, get_current_user
from app.repositories.config_repo import ConfigRepository
from app.repositories.arquivo_repo import ArquivoRepository
from app.services.config_service import ConfigService
from app.services.file_service import FileService
from app.schemas.config_schema import Config, ConfigUpdate, PendenciasIntervaloDiasUpdate, LembretesConfigUpdate, ModeloRelatorioInfo, ModeloRelatorioResponse, AlertasVencimentoConfig, AlertasVencimentoConfigUpdate, EscalonamentoConfig, EscalonamentoConfigUpdate

router = APIRouter(
    prefix="/config",
    tags=["Configurações"]
)

# --- Injeção de Dependências ---
def get_config_service(conn: asyncpg.Connection = Depends(get_connection)) -> ConfigService:
    return ConfigService(
        config_repo=ConfigRepository(conn)
    )

# --- Endpoints ---
# IMPORTANTE: Rotas específicas devem vir ANTES das rotas genéricas com path parameters!

@router.get("/", response_model=List[Config], summary="Listar todas as configurações")
async def list_configs(
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Lista todas as configurações do sistema.
    Requer permissão de administrador.
    """
    return await service.get_all_configs()


@router.get("/pendencias/intervalo-dias", response_model=dict, summary="Obter intervalo de dias para pendências")
async def get_pendencias_intervalo_dias(
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Retorna o intervalo de dias configurado para criação automática de pendências.
    Requer permissão de administrador.
    """
    intervalo = await service.get_pendencias_intervalo_dias()
    return {"intervalo_dias": intervalo}


@router.patch("/pendencias/intervalo-dias", response_model=Config, summary="Atualizar intervalo de dias")
async def update_pendencias_intervalo_dias(
    request: Request,
    update_data: PendenciasIntervaloDiasUpdate,
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Atualiza o intervalo de dias para criação automática de pendências.
    Requer permissão de administrador.

    - **intervalo_dias**: Número de dias entre cada pendência automática (1-365)
    """
    return await service.update_pendencias_intervalo_dias(update_data.intervalo_dias, admin_user, request)


@router.get("/lembretes/config", response_model=dict, summary="Obter configurações de lembretes")
async def get_lembretes_config(
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Retorna as configurações de lembretes de pendências.
    Requer permissão de administrador.
    
    Retorna:
    - **dias_antes_vencimento_inicio**: Quantos dias antes do vencimento começar a enviar lembretes
    - **intervalo_dias_lembrete**: A cada quantos dias enviar lembretes até o vencimento
    """
    return await service.get_lembretes_config()


@router.patch("/lembretes/config", response_model=dict, summary="Atualizar configurações de lembretes")
async def update_lembretes_config(
    update_data: LembretesConfigUpdate,
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Atualiza as configurações de lembretes de pendências.
    Requer permissão de administrador.
    
    - **dias_antes_vencimento_inicio**: Quantos dias antes do vencimento começar a enviar (1-90)
    - **intervalo_dias_lembrete**: A cada quantos dias enviar lembretes (1-30)
    
    Exemplo: dias_antes_vencimento_inicio=30 e intervalo_dias_lembrete=5
    Resultado: Lembretes serão enviados 30, 25, 20, 15, 10, 5 dias antes e no dia do vencimento.
    """
    return await service.update_lembretes_config(
        update_data.dias_antes_vencimento_inicio,
        update_data.intervalo_dias_lembrete
    )


# ==================== Modelo de Relatório ====================

@router.get("/modelo-relatorio/info", response_model=Optional[ModeloRelatorioInfo], summary="Obter informações do modelo de relatório")
async def get_modelo_relatorio_info(
    service: ConfigService = Depends(get_config_service),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Retorna informações sobre o modelo de relatório ativo.
    Disponível para todos os usuários autenticados.
    
    Retorna:
    - **arquivo_id**: ID do arquivo no sistema
    - **nome_original**: Nome original do arquivo
    - **ativo**: Se o modelo está ativo
    
    Retorna None se não houver modelo configurado.
    """
    return await service.get_modelo_relatorio_info()


@router.post("/modelo-relatorio/upload", response_model=ModeloRelatorioResponse, summary="Fazer upload do modelo de relatório")
async def upload_modelo_relatorio(
    file: UploadFile = File(...),
    conn: asyncpg.Connection = Depends(get_connection),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Faz upload de um novo modelo de relatório.
    Se já existir um modelo, substitui o anterior.
    Requer permissão de administrador.
    
    - **file**: Arquivo do modelo (PDF, DOC, DOCX, ODT)
    
    O modelo de relatório será disponibilizado para download em todos os contratos.
    """
    config_service = ConfigService(config_repo=ConfigRepository(conn))
    arquivo_repo = ArquivoRepository(conn)
    file_service = FileService()
    
    return await config_service.upload_modelo_relatorio(file, arquivo_repo, file_service)


@router.delete("/modelo-relatorio", response_model=ModeloRelatorioResponse, summary="Remover modelo de relatório")
async def remove_modelo_relatorio(
    conn: asyncpg.Connection = Depends(get_connection),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Remove o modelo de relatório ativo.
    Requer permissão de administrador.
    
    O arquivo será deletado do sistema de arquivos e do banco de dados.
    """
    config_service = ConfigService(config_repo=ConfigRepository(conn))
    arquivo_repo = ArquivoRepository(conn)
    
    return await config_service.remove_modelo_relatorio(arquivo_repo)


@router.get("/modelo-relatorio/download", summary="Fazer download do modelo de relatório")
async def download_modelo_relatorio(
    conn: asyncpg.Connection = Depends(get_connection),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Faz download do modelo de relatório ativo.
    Disponível para todos os usuários autenticados.
    
    Retorna o arquivo para download.
    """
    config_repo = ConfigRepository(conn)
    arquivo_repo = ArquivoRepository(conn)
    
    # Busca informações do modelo
    modelo_info = await config_repo.get_modelo_relatorio_info()
    if not modelo_info:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum modelo de relatório configurado"
        )
    
    # Busca informações do arquivo
    arquivo = await arquivo_repo.get_arquivo_by_id(modelo_info['arquivo_id'])
    if not arquivo:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo do modelo não encontrado"
        )
    
    # Retorna o arquivo (resolve caminho relativo para absoluto)
    from app.services.file_service import FileService
    path_completo = FileService.resolve_path(arquivo['caminho'])
    return FileResponse(
        path=path_completo,
        filename=arquivo['nome_original'],
        media_type='application/octet-stream'
    )


# ==================== Alertas de Vencimento ====================

@router.get("/alertas-vencimento", response_model=AlertasVencimentoConfig, summary="Obter configurações de alertas de vencimento")
async def get_alertas_vencimento_config(
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Retorna as configurações de alertas de vencimento de contratos.
    Requer permissão de administrador.
    
    Retorna:
    - **ativo**: Se os alertas estão ativos
    - **dias_antes**: Quantos dias antes do vencimento começar os alertas
    - **periodicidade_dias**: A cada quantos dias reenviar o alerta
    - **perfis_destino**: Lista de perfis que receberão os alertas
    - **hora_envio**: Hora do dia para enviar os alertas (HH:MM)
    """
    print("🔥 DEBUG ROUTER: Endpoint /alertas-vencimento chamado")
    print(f"🔥 DEBUG ROUTER: Service type: {type(service)}")
    print(f"🔥 DEBUG ROUTER: Admin user: {admin_user.nome if admin_user else 'None'}")
    result = await service.get_alertas_vencimento_config()
    print(f"🔥 DEBUG ROUTER: Resultado do service: {result}")
    return result


@router.patch("/alertas-vencimento", response_model=AlertasVencimentoConfig, summary="Atualizar configurações de alertas de vencimento")
async def update_alertas_vencimento_config(
    config: AlertasVencimentoConfigUpdate,
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Atualiza as configurações de alertas de vencimento de contratos.
    Requer permissão de administrador.
    
    - **ativo**: Ativar ou desativar alertas (true/false)
    - **dias_antes**: Dias antes do vencimento para começar (1-365)
    - **periodicidade_dias**: Dias entre cada reenvio (1-90)
    - **perfis_destino**: Array de perfis ["Administrador", "Gestor", "Fiscal"]
    - **hora_envio**: Hora do envio no formato HH:MM (ex: "10:00")
    
    **Exemplos de uso:**
    
    1. Alertas para Gestores, 90 dias antes, a cada 30 dias:
    ```json
    {
        "ativo": true,
        "dias_antes": 90,
        "periodicidade_dias": 30,
        "perfis_destino": ["Gestor"],
        "hora_envio": "10:00"
    }
    ```
    
    2. Alertas para Gestores E Fiscais, 60 dias antes, a cada 15 dias:
    ```json
    {
        "ativo": true,
        "dias_antes": 60,
        "periodicidade_dias": 15,
        "perfis_destino": ["Gestor", "Fiscal"],
        "hora_envio": "09:00"
    }
    ```
    
    3. Alertas apenas para Administradores (relatório completo):
    ```json
    {
        "ativo": true,
        "dias_antes": 120,
        "periodicidade_dias": 45,
        "perfis_destino": ["Administrador"],
        "hora_envio": "08:00"
    }
    ```
    
    **Comportamento:**
    - **Administrador**: Recebe relatório consolidado de TODOS os contratos vencendo
    - **Gestor**: Recebe apenas alertas dos contratos que gerencia
    - **Fiscal**: Recebe apenas alertas dos contratos que fiscaliza
    """
    return await service.update_alertas_vencimento_config(config)


# ==================== Escalonamento de Pendências ====================

@router.get("/escalonamento", response_model=EscalonamentoConfig, summary="Obter configurações de escalonamento")
async def get_escalonamento_config(
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Retorna as configurações de escalonamento de pendências vencidas.
    Requer permissão de administrador.

    Retorna:
    - **ativo**: Se o sistema de escalonamento está ativo
    - **dias_gestor**: Dias após vencimento para notificar o gestor
    - **dias_admin**: Dias após vencimento para notificar o administrador

    **Como funciona:**

    1. Quando uma pendência vence e não é resolvida
    2. Após **X dias** (dias_gestor), o **gestor do contrato** é notificado
    3. Após **Y dias** (dias_admin), o **administrador** é notificado
    4. Os emails continuam até a pendência ser resolvida
    """
    return await service.get_escalonamento_config()


@router.patch("/escalonamento", response_model=EscalonamentoConfig, summary="Atualizar configurações de escalonamento")
async def update_escalonamento_config(
    config: EscalonamentoConfigUpdate,
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Atualiza as configurações de escalonamento de pendências vencidas.
    Requer permissão de administrador.

    - **ativo**: Ativar ou desativar escalonamento (true/false)
    - **dias_gestor**: Dias após vencimento para notificar gestor (1-90)
    - **dias_admin**: Dias após vencimento para notificar admin (1-180)

    **Regra importante:** `dias_admin` deve ser maior que `dias_gestor`

    **Exemplo de configuração:**
    ```json
    {
        "ativo": true,
        "dias_gestor": 7,
        "dias_admin": 14
    }
    ```

    **Fluxo:**
    1. Pendência vence no dia 01/01
    2. Dia 08/01 (7 dias depois): Gestor recebe email
    3. Dia 15/01 (14 dias depois): Administrador recebe email
    4. Se não resolvida, emails continuam periodicamente
    """
    return await service.update_escalonamento_config(config)


# ==================== Rotas Genéricas (DEVEM VIR POR ÚLTIMO!) ====================
# IMPORTANTE: Estas rotas com path parameters capturam qualquer string
# Por isso devem estar NO FINAL, depois de todas as rotas específicas

@router.get("/{chave}", response_model=Config, summary="Buscar configuração por chave")
async def get_config(
    chave: str,
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Busca uma configuração específica pela chave.
    Requer permissão de administrador.
    """
    return await service.get_config(chave)


@router.patch("/{chave}", response_model=Config, summary="Atualizar configuração")
async def update_config(
    chave: str,
    config_update: ConfigUpdate,
    service: ConfigService = Depends(get_config_service),
    admin_user: Usuario = Depends(admin_required)
):
    """
    Atualiza o valor de uma configuração.
    Requer permissão de administrador.
    """
    return await service.update_config(chave, config_update)
