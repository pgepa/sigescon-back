# app/schemas/contrato_schema.py
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import date

# Schema base com os campos comuns
class ContratoBase(BaseModel):
    nr_contrato: str = Field(..., max_length=50)
    objeto: str
    data_inicio: date
    data_fim: date
    contratado_id: int
    modalidade_id: int
    status_id: int
    gestor_id: Optional[int] = None
    fiscal_id: Optional[int] = None
    valor_anual: Optional[float] = None
    valor_global: Optional[float] = None
    base_legal: Optional[str] = Field(None, max_length=255)
    termos_contratuais: Optional[str] = None
    fiscal_substituto_id: Optional[int] = None
    pae: Optional[str] = Field(None, max_length=50)
    doe: Optional[str] = Field(None, max_length=50)
    data_doe: Optional[date] = None
    garantia: Optional[date] = None
    portaria_fiscal: Optional[str] = Field(None, max_length=255)
    nr_adesao_ata: Optional[str] = Field(None, max_length=255)

    @field_validator('valor_anual')
    @classmethod
    def validate_valor_anual(cls, v):
        if v is not None and v < 0:
            raise ValueError('Valor anual não pode ser negativo')
        return v

    @field_validator('valor_global')
    @classmethod
    def validate_valor_global(cls, v):
        if v is not None and v < 0:
            raise ValueError('Valor global não pode ser negativo')
        return v

# Schema para a resposta da API (leitura de um contrato)
# Inclui campos de tabelas relacionadas (JOINs)
class Contrato(ContratoBase):
    id: int
    ativo: bool
    data_fim_original: Optional[date] = None
    contratado_nome: Optional[str] = None
    modalidade_nome: Optional[str] = None
    status_nome: Optional[str] = None
    gestor_nome: Optional[str] = None
    fiscal_nome: Optional[str] = None
    fiscal_substituto_nome: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Schema para a criação de um novo contrato 
class ContratoCreate(ContratoBase):
    pass

# Schema para atualização
class ContratoUpdate(BaseModel):
    nr_contrato: Optional[str] = Field(None, max_length=50)
    objeto: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    contratado_id: Optional[int] = None
    modalidade_id: Optional[int] = None
    status_id: Optional[int] = None
    gestor_id: Optional[int] = None
    fiscal_id: Optional[int] = None
    valor_anual: Optional[float] = None
    valor_global: Optional[float] = None
    base_legal: Optional[str] = Field(None, max_length=255)
    termos_contratuais: Optional[str] = None
    fiscal_substituto_id: Optional[int] = None
    pae: Optional[str] = Field(None, max_length=50)
    doe: Optional[str] = Field(None, max_length=50)
    data_doe: Optional[date] = None
    garantia: Optional[date] = None
    portaria_fiscal: Optional[str] = Field(None, max_length=255)
    nr_adesao_ata: Optional[str] = Field(None, max_length=255)

    @field_validator('valor_anual')
    @classmethod
    def validate_valor_anual(cls, v):
        if v is not None and v < 0:
            raise ValueError('Valor anual não pode ser negativo')
        return v

    @field_validator('valor_global')
    @classmethod
    def validate_valor_global(cls, v):
        if v is not None and v < 0:
            raise ValueError('Valor global não pode ser negativo')
        return v

# Schema para a resposta da listagem
class ContratoList(BaseModel):
    id: int
    nr_contrato: str
    objeto: str
    data_fim: date
    fiscal_id: Optional[int] = None
    gestor_id: Optional[int] = None
    contratado_nome: Optional[str] = None
    status_nome: Optional[str] = None
    fiscal_nome: Optional[str] = None
    gestor_nome: Optional[str] = None
    total_aditivos: int = 0

    model_config = ConfigDict(from_attributes=True)

# Schema para a resposta paginada da API
class ContratoPaginated(BaseModel):
    data: List[ContratoList]
    total_items: int
    total_pages: int
    current_page: int
    per_page: int

# Schemas para gerenciamento de arquivos do contrato
class ArquivoContrato(BaseModel):
    """Schema para representar um arquivo de contrato"""
    id: int
    nome_arquivo: str
    tipo_arquivo: Optional[str] = None
    tamanho_bytes: Optional[int] = None
    contrato_id: int
    tipo_vinculo: Optional[str] = None
    termo_aditivo_id: Optional[int] = None
    termo_aditivo_numero: Optional[int] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ArquivoContratoList(BaseModel):
    """Schema para listagem de arquivos de um contrato"""
    arquivos: List[ArquivoContrato]
    total_arquivos: int
    contrato_id: int