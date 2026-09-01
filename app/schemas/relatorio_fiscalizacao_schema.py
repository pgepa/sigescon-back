# app/schemas/relatorio_fiscalizacao_schema.py
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, Literal


# Status possíveis do relatório de fiscalização
# rascunho → fiscal está preenchendo, pode salvar e voltar quantas vezes quiser
# salvo    → finalizado pelo próprio fiscal, não é mais editável
#
# Sem etapa de aprovação do gestor: os status antigos (enviado, aprovado,
# nao_conforme) ficam só como histórico de relatórios anteriores a essa mudança.


class RelatorioCreateSchema(BaseModel):
    """Usado para gerar PDF — datas obrigatórias, não salva no banco."""
    periodo_inicio: date
    periodo_fim: date
    data_relatorio: date

    execucao_objeto_sim: bool
    execucao_objeto_detalhes: Optional[str] = ""

    prazo_execucao_sim: bool
    prazo_execucao_detalhes: Optional[str] = ""

    nivel_qualidade_sim: bool
    nivel_qualidade_detalhes: Optional[str] = ""

    medicoes_servicos_sim: bool
    medicoes_servicos_detalhes: Optional[str] = ""

    ocorrencias_sim: bool
    ocorrencias_detalhes: Optional[str] = ""

    documentos_habilitacao_sim: bool
    documentos_habilitacao_detalhes: Optional[str] = ""

    subcontratacao_sim: bool
    subcontratacao_detalhes: Optional[str] = ""

    obrigacoes_empregados_resposta: str
    obrigacoes_empregados_detalhes: Optional[str] = ""

    garantias_contratuais_resposta: str
    garantias_contratuais_detalhes: Optional[str] = ""

    execucao_satisfatoria_sim: bool
    execucao_satisfatoria_detalhes: Optional[str] = ""

    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class RelatorioSalvarSchema(BaseModel):
    """Usado para salvar rascunho — datas opcionais."""
    status: Literal["rascunho"] = "rascunho"

    periodo_inicio: Optional[date] = None
    periodo_fim: Optional[date] = None
    data_relatorio: Optional[date] = None

    execucao_objeto_sim: bool = False
    execucao_objeto_detalhes: Optional[str] = ""

    prazo_execucao_sim: bool = False
    prazo_execucao_detalhes: Optional[str] = ""

    nivel_qualidade_sim: bool = False
    nivel_qualidade_detalhes: Optional[str] = ""

    medicoes_servicos_sim: bool = False
    medicoes_servicos_detalhes: Optional[str] = ""

    ocorrencias_sim: bool = False
    ocorrencias_detalhes: Optional[str] = ""

    documentos_habilitacao_sim: bool = False
    documentos_habilitacao_detalhes: Optional[str] = ""

    subcontratacao_sim: bool = False
    subcontratacao_detalhes: Optional[str] = ""

    obrigacoes_empregados_resposta: str = ""
    obrigacoes_empregados_detalhes: Optional[str] = ""

    garantias_contratuais_resposta: str = ""
    garantias_contratuais_detalhes: Optional[str] = ""

    execucao_satisfatoria_sim: bool = False
    execucao_satisfatoria_detalhes: Optional[str] = ""

    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None