# app/schemas/termo_aditivo_schema.py
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import date, datetime


class TipoTermoAditivoBase(BaseModel):
    id: int
    nome: str
    descricao: Optional[str] = None
    ativo: bool = True

    model_config = ConfigDict(from_attributes=True)


class TipoTermoAditivoResponse(TipoTermoAditivoBase):
    pass


class TermoAditivoBase(BaseModel):
    tipo_id: int = Field(..., description="ID do tipo do aditivo: 1 - Prazo, 2 - Valor, 3 - Misto, 4 - Outros")
    objeto: str = Field(..., description="Descrição do objeto do aditivo")
    data_assinatura: date
    data_publicacao: Optional[date] = None
    data_inicio: Optional[date] = None
    nova_data_fim: Optional[date] = None
    valor_acrescimo: Optional[float] = None
    valor_supressao: Optional[float] = None
    pae: Optional[str] = Field(None, description="Número do Processo Administrativo Eletrônico")
    observacoes: Optional[str] = None

    @field_validator("valor_acrescimo", "valor_supressao")
    @classmethod
    def validate_valores(cls, v):
        if v is not None and v < 0:
            raise ValueError("Valores não podem ser negativos")
        return v


class TermoAditivoCreate(TermoAditivoBase):
    numero_aditivo: Optional[int] = None  # Se omitido, calcula automaticamente


class TermoAditivoUpdate(BaseModel):
    tipo_id: Optional[int] = None
    objeto: Optional[str] = None
    data_assinatura: Optional[date] = None
    data_publicacao: Optional[date] = None
    data_inicio: Optional[date] = None
    nova_data_fim: Optional[date] = None
    valor_acrescimo: Optional[float] = None
    valor_supressao: Optional[float] = None
    pae: Optional[str] = None
    observacoes: Optional[str] = None
    status: Optional[str] = None
    ativo: Optional[bool] = None

    @field_validator("valor_acrescimo", "valor_supressao")
    @classmethod
    def validate_valores(cls, v):
        if v is not None and v < 0:
            raise ValueError("Valores não podem ser negativos")
        return v


class TermoAditivo(TermoAditivoBase):
    id: int
    contrato_id: int
    numero_aditivo: int
    tipo_nome: Optional[str] = None
    tipo_descricao: Optional[str] = None
    arquivo_id: Optional[int] = None
    arquivo_nome: Optional[str] = None
    ativo: bool = True
    status: str = Field("Ativo", description="Status calculado do aditivo: Ativo, Vencido ou Inativo")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TermoAditivoList(BaseModel):
    data: List[TermoAditivo]
    total: int
    contrato_id: int
