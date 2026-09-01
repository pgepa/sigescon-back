# app/schemas/relatorio_schema.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date, datetime

class RelatorioBase(BaseModel):
    observacoes_fiscal: Optional[str] = None
    pendencia_id: int

class RelatorioCreate(RelatorioBase):
    fiscal_usuario_id: int

class Relatorio(RelatorioBase):
    id: int
    contrato_id: int
    fiscal_usuario_id: int
    arquivo_id: int
    status_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Campos de JOINs para exibição detalhada
    enviado_por: Optional[str] = None
    status_relatorio: Optional[str] = None
    nome_arquivo: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)