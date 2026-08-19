# app/main.py 
import time
import inspect
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import asyncpg

# Imports dos routers existentes
from app.api.routers import (
    contratado_router, auth_router, usuario_router, perfil_router,
    modalidade_router, status_router, status_relatorio_router,
    status_pendencia_router, contrato_router, pendencia_router, relatorio_router,
    arquivo_router, dashboard_router, config_router, audit_log_router
)
from app.api.routers import relatorio_fiscalizacao_router
from app.api.routers import usuario_perfil_router
from app.api.routers import termo_aditivo_router
from app.api.routers import aditivo_relatorio_router
from app.api.routers import contrato_responsavel_router
from app.api.routers import public_router
# Imports dos sistemas avançados
from app.core.database import get_db_pool, close_db_pool
from app.core.config import settings
from app.middleware.audit import AuditMiddleware
from app.middleware.logging import setup_logging
from app.services.notification_service import NotificationScheduler
from app.api.exception_handlers import (
    sigescon_exception_handler,
    database_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler
)
from app.core.exceptions import SigesconException

from app.api.doc_dependencies import get_admin_for_docs


def _parse_cors_origins() -> list[str]:
    raw = (settings.CORS_ALLOW_ORIGINS or "").strip()
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def _cors_middleware_kwargs() -> dict:
    """CORS para SPA com JWT no header Authorization (sem cookies cross-origin)."""
    kw: dict = {
        "allow_origins": _parse_cors_origins(),
        # Bearer token não depende de cookie; False evita combinações problemáticas com allow_origins=["*"] em alguns navegadores.
        "allow_credentials": False,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if "allow_private_network" in inspect.signature(CORSMiddleware.__init__).parameters:
        kw["allow_private_network"] = True
    return kw


# Configuração de logging
setup_logging()

# Instância do scheduler de notificações
notification_scheduler = NotificationScheduler()

# Gerenciador de contexto para o ciclo de vida da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    print("Iniciando aplicação SIGESCON...")
    
    # === STARTUP ===
    try:
        # 1. Conexão com banco de dados
        print("Conectando ao banco de dados...")
        await get_db_pool()
        
        # 2. Configuração do scheduler de notificações
        print("Configurando scheduler de notificações...")
        await notification_scheduler.setup_services()
        notification_scheduler.start_scheduler()
        
        print("Aplicação iniciada com sucesso!")
        
        # Debug: Listar todas as rotas registradas
        print("\n🔍 DEBUG: Rotas registradas no FastAPI:")
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                methods = ', '.join(route.methods) if route.methods else 'N/A'
                print(f"  {methods:<10} {route.path}")
        print(" DEBUG: Fim da lista de rotas\n")
        
        yield  # Aplicação está rodando
        
    except Exception as e:
        print(f" Erro durante inicialização: {e}")
        raise
    
    # === SHUTDOWN ===
    print("Encerrando aplicação...")
    
    try:
        # 1. Para o scheduler
        print(" Parando scheduler...")
        notification_scheduler.stop_scheduler()
        
        # 2. Fecha conexões do banco
        print(" Fechando conexões do banco...")
        await close_db_pool()
        
        print(" Aplicação encerrada com sucesso!")
    
    except Exception as e:
        print(f" Erro durante encerramento: {e}")

# Criação da aplicação FastAPI
app = FastAPI(
    title="SIGESCON API",
    description="""
    Sistema de Gestão de Contratos - API RESTful
    
    ## Funcionalidades Principais:
    
    * **Autenticação JWT** - Sistema seguro de login
    * **Gestão de Usuários** - CRUD completo com perfis
    * **Gestão de Contratos** - Ciclo completo com upload de arquivos
    * **Relatórios Fiscais** - Workflow de submissão e aprovação
    * **Notificações** - Sistema automatizado de lembretes
    * **Auditoria** - Log completo de todas as ações
    
    ## Permissões:
    
    * **Administrador** - Acesso total ao sistema
    * **Gestor** - Visualização de contratos sob sua gestão
    * **Fiscal** - Submissão de relatórios e consulta de pendências
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# === CONFIGURAÇÃO CRUCIAL PARA RESOLVER REDIRECTS 307 ===

app.router.redirect_slashes = False
print("Redirects automáticos desabilitados - URLs com e sem barra final funcionam igualmente")

# === MIDDLEWARE ===
# CORSMiddleware deve ser registrado por último para ficar o mais externo e tratar OPTIONS/preflight primeiro.
# (add_middleware empilha em LIFO no Starlette.)

# 1. Middleware de auditoria
app.add_middleware(AuditMiddleware)

# 2. CORS (Private Network Access quando o Starlette suportar)
app.add_middleware(CORSMiddleware, **_cors_middleware_kwargs())

# 3. Middleware para adicionar timestamp na request
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Adiciona informações de timing e request ID"""
    start_time = time.time()
    request.state.timestamp = start_time
    
    # Adiciona ID único para rastreamento
    import uuid
    request.state.request_id = str(uuid.uuid4())[:8]
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request.state.request_id
    
    return response 

# === EXCEPTION HANDLERS ===

# Handlers customizados (ordem importante - mais específico primeiro)
app.add_exception_handler(SigesconException, sigescon_exception_handler)
app.add_exception_handler(asyncpg.PostgresError, database_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# === ROUTERS ===

# Autenticação: /auth/* na raiz (legado e tokenUrl OAuth2).
app.include_router(auth_router.router)
app.include_router(usuario_perfil_router.router)

# Routers principais com prefixo /api/v1
API_PREFIX = "/api/v1"

# Mesmas rotas de auth em /api/v1/auth/* (alinha com o restante da API e evita 404 no front).
app.include_router(auth_router.router, prefix=API_PREFIX)

print("🔧 Registrando routers principais...")

try:
    app.include_router(usuario_router.router, prefix=API_PREFIX)
    print(f"Router de usuários registrado: {API_PREFIX}/usuarios")
except Exception as e:
    print(f"Erro ao registrar router de usuários: {e}")

try:
    print(f"DEBUG: contratado_router.router = {contratado_router.router}")
    print(f"DEBUG: Rotas no contratado_router: {[route.path for route in contratado_router.router.routes]}")
    app.include_router(contratado_router.router, prefix=API_PREFIX)
    print(f"Router de contratados registrado: {API_PREFIX}/contratados")
except Exception as e:
    print(f"Erro ao registrar router de contratados: {e}")
    import traceback
    traceback.print_exc()

app.include_router(public_router.router, prefix=API_PREFIX)
print(f"✅ Router público registrado: {API_PREFIX}/public/...")

app.include_router(contrato_responsavel_router.router, prefix=API_PREFIX)
print(f"✅ Router de responsáveis registrado: {API_PREFIX}/contratos/{{id}}/responsaveis")

app.include_router(contrato_router.router, prefix=API_PREFIX)
print(f"✅ Router de contratos registrado: {API_PREFIX}/contratos")

app.include_router(pendencia_router.router, prefix=API_PREFIX)
print(f"✅ Router de pendências registrado: {API_PREFIX}/pendencias")

app.include_router(relatorio_router.router, prefix=API_PREFIX)
print(f"✅ Router de relatórios registrado: {API_PREFIX}/relatorios")

app.include_router(relatorio_fiscalizacao_router.router, prefix=API_PREFIX)
print(f"✅ Router de relatórios de fiscalização registrado: {API_PREFIX}/relatorios/salvar")

app.include_router(arquivo_router.router, prefix=API_PREFIX)
print(f"✅ Router de arquivos registrado: {API_PREFIX}/arquivos")

app.include_router(dashboard_router.router, prefix=API_PREFIX)
print(f"✅ Router de dashboard registrado: {API_PREFIX}/dashboard")

app.include_router(config_router.router, prefix=API_PREFIX)
print(f"✅ Router de configurações registrado: {API_PREFIX}/config")

app.include_router(audit_log_router.router, prefix=API_PREFIX)
print(f"✅ Router de auditoria registrado: {API_PREFIX}/audit-logs")

app.include_router(termo_aditivo_router.router, prefix=API_PREFIX)
print(f"✅ Router de termos aditivos registrado: {API_PREFIX}/contratos/{{id}}/aditivos")

app.include_router(aditivo_relatorio_router.router, prefix=API_PREFIX)
print(f"✅ Router de relatório de termos aditivos registrado: {API_PREFIX}/aditivos/relatorio")


# Routers de tabelas auxiliares
app.include_router(perfil_router.router, prefix=API_PREFIX)
app.include_router(modalidade_router.router, prefix=API_PREFIX)
app.include_router(status_router.router, prefix=API_PREFIX)
app.include_router(status_relatorio_router.router, prefix=API_PREFIX)
app.include_router(status_pendencia_router.router, prefix=API_PREFIX)

# === ENDPOINTS ADICIONAIS ===

@app.get("/docs", include_in_schema=False)
async def get_protected_docs(is_admin: bool = Depends(get_admin_for_docs)):
    """Rota protegida para a UI do Swagger."""
    return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title + " - Swagger UI")

@app.get("/redoc", include_in_schema=False)
async def get_protected_redoc(is_admin: bool = Depends(get_admin_for_docs)):
    """Rota protegida para a UI do ReDoc."""
    return get_redoc_html(openapi_url="/openapi.json", title=app.title + " - ReDoc")

@app.get("/openapi.json", include_in_schema=False)
async def get_protected_openapi(is_admin: bool = Depends(get_admin_for_docs)):
    """Rota protegida para o schema OpenAPI."""
    return JSONResponse(get_openapi(title=app.title, version=app.version, routes=app.routes))

@app.get("/", tags=["Root"])
async def read_root():
    """Endpoint raiz da API com informações básicas."""
    return {
        "message": "Bem-vindo à SIGESCON API v2.0!",
        "status": "operational",
        "features": [
            "Autenticação JWT",
            "Gestão de Contratos",
            "Upload de Arquivos",
            "Notificações Automáticas",
            "Sistema de Auditoria",
            "Performance Monitoring",
            "Permissões Granulares"
        ],
        "docs": "/docs",
        "redoc": "/redoc",
        "version": "2.0.0"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de health check para monitoramento."""
    try:
        # Testa conexão com banco
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    # Status geral
    overall_status = "healthy" if db_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "services": {
            "database": db_status,
            "notifications": "healthy" if notification_scheduler.scheduler.running else "stopped"
        }
    }

@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """Endpoint básico de métricas para monitoramento."""
    try:
        pool = await get_db_pool()
        
        # Estatísticas do pool de conexões
        pool_stats = {
            "max_size": pool.get_max_size(),
            "min_size": pool.get_min_size(),
            "size": pool.get_size(),
            "idle_size": pool.get_idle_size()
        }
        
        return {
            "database": {
                "connection_pool": pool_stats
            },
            "application": {
                "version": "2.0.0",
                "uptime": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
            }
        }
    except Exception as e:
        return {
            "error": "Failed to collect metrics",
            "details": str(e)
        }



# === CONFIGURAÇÕES ADICIONAIS ===

# Configuração de tags para documentação
tags_metadata = [
    {
        "name": "Root",
        "description": "Endpoints básicos da API",
    },
    {
        "name": "Autenticação",
        "description": "Login e gerenciamento de tokens JWT",
    },
    {
        "name": "Usuários",
        "description": "CRUD de usuários e gerenciamento de perfis",
    },
    {
        "name": "Contratos",
        "description": "Gestão completa do ciclo de vida de contratos",
    },
    {
        "name": "Contratados",
        "description": "Cadastro de empresas e pessoas contratadas",
    },
    {
        "name": "Relatórios Fiscais",
        "description": "Submissão e aprovação de relatórios de fiscalização",
    },
    {
        "name": "Pendências",
        "description": "Criação e acompanhamento de pendências de relatórios",
    },
    {
        "name": "Perfis",
        "description": "Tipos de perfil de usuário no sistema",
    },
    {
        "name": "Modalidades",
        "description": "Modalidades de contratação",
    },
    {
        "name": "Status de Contratos",
        "description": "Status possíveis para contratos",
    },
    {
        "name": "Status de Relatórios",
        "description": "Status possíveis para relatórios fiscais",
    },
    {
        "name": "Status de Pendências",
        "description": "Status possíveis para pendências",
    },
    {
        "name": "Health",
        "description": "Monitoramento de saúde da aplicação",
    },
    {
        "name": "Monitoring",
        "description": "Métricas e estatísticas do sistema",
    },
    {
        "name": "Dashboard",
        "description": "Endpoints para dashboards administrativos e do fiscal",
    },
    {
        "name": "Auditoria",
        "description": "Logs de auditoria e rastreamento de ações no sistema",
    },
    {
        "name": "Configurações",
        "description": "Configurações gerais do sistema (pendências, lembretes, alertas)",
    }
]

app.openapi_tags = tags_metadata

# === DESENVOLVIMENTO ===
if __name__ == "__main__":
    import uvicorn
    
    print("Modo de desenvolvimento detectado")
    print("Documentação disponível em: http://localhost:8000/docs")
    print("ReDoc disponível em: http://localhost:8000/redoc")
    print("Health check em: http://localhost:8000/health")
    print("Métricas em: http://localhost:8000/metrics")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )