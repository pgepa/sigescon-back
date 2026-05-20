# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict # <-- IMPORTAR SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Dicionário de configuração do Pydantic v2
    model_config = SettingsConfigDict(env_file=".env", extra='ignore') 

    # Configuração do Banco de Dados
    DATABASE_URL: str

    # Configuração de Autenticação JWT
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1400

    # CORS: origens permitidas separadas por vírgula (ex.: "https://app.org,http://10.0.0.1:8080").
    # Se vazio, usa ["*"] (Starlette replica o Origin nas respostas quando allow_credentials=True).
    CORS_ALLOW_ORIGINS: Optional[str] = None

    # Credenciais do Admin 
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None

    # Configuração do Servidor de Email (SMTP)
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SENDER_EMAIL: Optional[str] = None
    SENDER_PASSWORD: Optional[str] = None

 

settings = Settings()