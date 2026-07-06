# app/schemas/contrato_responsavel_schema.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date


class ContratoResponsavelBase(BaseModel):
    contrato_id: int
    usuario_id: int
    tipo: str = Field(..., pattern="^(fiscal|gestor|fiscal_substituto)$")
    data_inicio: date
    data_fim: Optional[date] = None
    portaria: Optional[str] = None


class ContratoResponsavelCreate(BaseModel):
    usuario_id: int
    tipo: str = Field(..., pattern="^(fiscal|gestor|fiscal_substituto)$")
    data_inicio: date
    portaria: Optional[str] = None


class ContratoResponsavelUpdate(BaseModel):
    data_fim: Optional[date] = None
    portaria: Optional[str] = None


class ContratoResponsavel(ContratoResponsavelBase):
    id: int
    ativo: bool
    usuario_nome: Optional[str] = None
    contrato_nr: Optional[str] = None
    criado_por_nome: Optional[str] = None
    criado_por_usuario_id: Optional[int] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContratoResponsavelList(BaseModel):
    responsaveis: List[ContratoResponsavel]
    total: int
    contrato_id: int


class RelatorioResponsaveisItem(BaseModel):
    contrato_id: int
    nr_contrato: str
    objeto: str
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    status_nome: Optional[str] = None
    gestor_atual_nome: Optional[str] = None
    gestor_atual_id: Optional[int] = None
    fiscal_atual_nome: Optional[str] = None
    fiscal_atual_id: Optional[int] = None
    fiscal_substituto_atual_nome: Optional[str] = None
    fiscal_substituto_atual_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RelatorioResponsaveisPaginated(BaseModel):
    data: List[RelatorioResponsaveisItem]
    total_items: int
    total_pages: int
    current_page: int
    per_page: int
