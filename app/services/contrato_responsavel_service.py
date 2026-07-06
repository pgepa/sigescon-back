# app/services/contrato_responsavel_service.py
import math
import logging
from typing import Optional, Dict
from fastapi import HTTPException, status

from app.repositories.contrato_responsavel_repo import ContratoResponsavelRepository
from app.repositories.contrato_repo import ContratoRepository
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.contrato_responsavel_schema import (
    ContratoResponsavelCreate, ContratoResponsavelUpdate,
    ContratoResponsavel, ContratoResponsavelList,
    RelatorioResponsaveisItem, RelatorioResponsaveisPaginated
)
from app.schemas.usuario_schema import Usuario

logger = logging.getLogger(__name__)

TIPO_CAMPO_MAP = {
    'fiscal': 'fiscal_id',
    'gestor': 'gestor_id',
    'fiscal_substituto': 'fiscal_substituto_id',
}


class ContratoResponsavelService:
    def __init__(
        self,
        responsavel_repo: ContratoResponsavelRepository,
        contrato_repo: ContratoRepository,
        usuario_repo: UsuarioRepository,
    ):
        self.responsavel_repo = responsavel_repo
        self.contrato_repo = contrato_repo
        self.usuario_repo = usuario_repo

    async def _validate_contrato(self, contrato_id: int) -> Dict:
        contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
        if not contrato:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contrato não encontrado"
            )
        return contrato

    async def _validate_usuario(self, usuario_id: int) -> Dict:
        usuario = await self.usuario_repo.get_user_by_id(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        return usuario

    async def designar_responsavel(
        self,
        contrato_id: int,
        dados: ContratoResponsavelCreate,
        current_user: Usuario
    ) -> ContratoResponsavel:
        await self._validate_contrato(contrato_id)
        await self._validate_usuario(dados.usuario_id)

        atual = await self.responsavel_repo.get_atual(contrato_id, dados.tipo)
        if atual and atual['usuario_id'] == dados.usuario_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Este usuário já é o {dados.tipo} atual deste contrato"
            )

        if atual:
            await self.responsavel_repo.encerrar_atual(
                contrato_id, dados.tipo, dados.data_inicio
            )

        novo = await self.responsavel_repo.create(
            contrato_id=contrato_id,
            usuario_id=dados.usuario_id,
            tipo=dados.tipo,
            data_inicio=dados.data_inicio,
            portaria=dados.portaria,
            criado_por_usuario_id=current_user.id,
        )

        campo = TIPO_CAMPO_MAP.get(dados.tipo)
        if campo:
            await self.contrato_repo.conn.execute(
                f"UPDATE contrato SET {campo} = $1, updated_at = NOW() WHERE id = $2",
                dados.usuario_id, contrato_id,
            )

        return ContratoResponsavel.model_validate(novo)

    async def listar_responsaveis(
        self,
        contrato_id: int,
        tipo: Optional[str] = None,
        apenas_atuais: bool = False
    ) -> ContratoResponsavelList:
        await self._validate_contrato(contrato_id)
        responsaveis = await self.responsavel_repo.get_by_contrato(
            contrato_id, tipo=tipo, apenas_atuais=apenas_atuais
        )
        return ContratoResponsavelList(
            responsaveis=[ContratoResponsavel.model_validate(r) for r in responsaveis],
            total=len(responsaveis),
            contrato_id=contrato_id,
        )

    async def atualizar_responsavel(
        self,
        contrato_id: int,
        responsavel_id: int,
        dados: ContratoResponsavelUpdate
    ) -> ContratoResponsavel:
        await self._validate_contrato(contrato_id)
        existente = await self.responsavel_repo.get_by_id(responsavel_id)
        if not existente or existente['contrato_id'] != contrato_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro de responsável não encontrado neste contrato"
            )
        atualizado = await self.responsavel_repo.update(
            responsavel_id,
            data_fim=dados.data_fim,
            portaria=dados.portaria,
        )
        return ContratoResponsavel.model_validate(atualizado)

    async def remover_responsavel(self, contrato_id: int, responsavel_id: int) -> bool:
        await self._validate_contrato(contrato_id)
        existente = await self.responsavel_repo.get_by_id(responsavel_id)
        if not existente or existente['contrato_id'] != contrato_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro de responsável não encontrado neste contrato"
            )
        return await self.responsavel_repo.delete(responsavel_id)

    async def relatorio_responsaveis(
        self,
        page: int,
        per_page: int,
        filters: Optional[Dict] = None
    ) -> RelatorioResponsaveisPaginated:
        offset = (page - 1) * per_page
        dados, total = await self.responsavel_repo.get_relatorio_responsaveis(
            filters=filters, limit=per_page, offset=offset
        )
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        return RelatorioResponsaveisPaginated(
            data=[RelatorioResponsaveisItem.model_validate(d) for d in dados],
            total_items=total,
            total_pages=total_pages,
            current_page=page,
            per_page=per_page,
        )
