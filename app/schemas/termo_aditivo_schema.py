# app/schemas/termo_aditivo_schema.py
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import date

TIPOS_ADITIVO = ["Prazo", "Valor", "Objeto", "Misto"]

class TermoAditivoBase(BaseModel):
    tipo: str = Field(..., description="Tipo do aditivo: Prazo, Valor, Objeto ou Misto")
    objeto: str = Field(..., description="Descrição do objeto do aditivo")
    data_assinatura: date
    data_publicacao: Optional[date] = None
    data_inicio: Optional[date] = None
    nova_data_fim: Optional[date] = None
    valor_acrescimo: Optional[float] = None
    valor_supressao: Optional[float] = None
    pae: Optional[str] = Field(None, description="Número do Processo Administrativo Eletrônico")
    observacoes: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v):
        if v not in TIPOS_ADITIVO:
            raise ValueError(f"Tipo inválido. Deve ser um de: {', '.join(TIPOS_ADITIVO)}")
        return v

    @field_validator("valor_acrescimo", "valor_supressao")
    @classmethod
    def validate_valores(cls, v):
        if v is not None and v < 0:
            raise ValueError("Valores não podem ser negativos")
        return v


class TermoAditivoCreate(TermoAditivoBase):
    pass


class TermoAditivoUpdate(BaseModel):
    tipo: Optional[str] = None
    objeto: Optional[str] = None
    data_assinatura: Optional[date] = None
    data_publicacao: Optional[date] = None
    data_inicio: Optional[date] = None
    nova_data_fim: Optional[date] = None
    valor_acrescimo: Optional[float] = None
    valor_supressao: Optional[float] = None
    pae: Optional[str] = None
    observacoes: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v):
        if v is not None and v not in TIPOS_ADITIVO:
            raise ValueError(f"Tipo inválido. Deve ser um de: {', '.join(TIPOS_ADITIVO)}")
        return v


class TermoAditivo(TermoAditivoBase):
    id: int
    contrato_id: int
    numero_aditivo: int
    arquivo_id: Optional[int] = None
    arquivo_nome: Optional[str] = None
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class TermoAditivoList(BaseModel):
    data: List[TermoAditivo]
    total: int
    contrato_id: int
