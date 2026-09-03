# app/middleware/audit.py
import os
import time
import json
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Diretório de logs na raiz do projeto (evita falha ao iniciar se a pasta não existir)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

# Configurar logger específico para auditoria
audit_logger = logging.getLogger("audit")
audit_handler = logging.FileHandler(os.path.join(_LOG_DIR, "audit.log"))
audit_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
audit_handler.setFormatter(audit_formatter)
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)

class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware para logging de auditoria de todas as requisições"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Endpoints que requerem auditoria especial
        self.critical_endpoints = {
            "POST": ["/usuarios", "/contratos", "/auth/login"],
            "PATCH": ["/usuarios/", "/contratos/", "/alterar-senha", "/resetar-senha"],
            "DELETE": ["/usuarios/", "/contratos/", "/contratados/"],
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Captura dados iniciais
        start_time = time.time()
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        # Extrai informações do usuário se disponível
        user_info = "anonymous"
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                # Aqui você poderia decodificar o JWT para pegar info do usuário
                # Por simplicidade, vamos apenas indicar que está autenticado
                user_info = "authenticated_user"
            except:
                pass

        # Chama o endpoint
        response = await call_next(request)
        
        # Calcula tempo de processamento
        process_time = time.time() - start_time
        
        # Monta dados da auditoria
        audit_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "client_ip": client_ip,
            "user": user_info,
            "process_time": round(process_time, 4),
        }

        # Log especial para endpoints críticos
        if self._is_critical_endpoint(method, path):
            audit_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            audit_logger.log(
                audit_level,
                f"CRITICAL_ACTION: {json.dumps(audit_data, ensure_ascii=False)}"
            )
        
        # Log geral de performance para requisições lentas
        if process_time > 2.0:  # Mais de 2 segundos
            audit_logger.warning(
                f"SLOW_REQUEST: {json.dumps(audit_data, ensure_ascii=False)}"
            )

        # Adiciona headers de resposta para debugging
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

    def _is_critical_endpoint(self, method: str, path: str) -> bool:
        """Verifica se o endpoint é crítico para auditoria"""
        if method not in self.critical_endpoints:
            return False
        
        critical_paths = self.critical_endpoints[method]
        return any(critical_path in path for critical_path in critical_paths)

