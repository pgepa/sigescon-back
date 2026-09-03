# app/services/termo_aditivo_service.py
import logging
from typing import List, Dict
from fastapi import HTTPException, status, UploadFile

from app.repositories.termo_aditivo_repo import TermoAditivoRepository
from app.repositories.tipo_termo_aditivo_repo import TipoTermoAditivoRepository
from app.repositories.contrato_repo import ContratoRepository
from app.schemas.termo_aditivo_schema import (
    TermoAditivo,
    TermoAditivoCreate,
    TermoAditivoUpdate,
    TipoTermoAditivoResponse
)

logger = logging.getLogger(__name__)


class TermoAditivoService:
    def __init__(
        self,
        repo: TermoAditivoRepository,
        tipo_repo: TipoTermoAditivoRepository,
        contrato_repo: ContratoRepository,
    ):
        self.repo = repo
        self.tipo_repo = tipo_repo
        self.contrato_repo = contrato_repo

    async def listar_tipos(self) -> List[TipoTermoAditivoResponse]:
        tipos = await self.tipo_repo.get_all(apenas_ativos=True)
        return [TipoTermoAditivoResponse.model_validate(t) for t in tipos]

    async def _verificar_contrato(self, contrato_id: int):
        contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
        if not contrato:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
        return contrato

    async def _validar_tipo(self, tipo_id: int):
        tipo = await self.tipo_repo.get_by_id(tipo_id)
        if not tipo:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de termo aditivo inválido")
        return tipo

    async def criar(self, contrato_id: int, dados: TermoAditivoCreate) -> TermoAditivo:
        await self._verificar_contrato(contrato_id)
        await self._validar_tipo(dados.tipo_id)

        # Validações por natureza
        if dados.tipo_id in [1, 3] and not dados.nova_data_fim:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Termos aditivos de Prazo ou Misto exigem a definição de 'nova_data_fim'."
            )
        if dados.tipo_id in [2, 3] and dados.valor_acrescimo is None and dados.valor_supressao is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Termos aditivos de Valor ou Misto exigem a definição de 'valor_acrescimo' ou 'valor_supressao'."
            )

        novo = await self.repo.create(contrato_id, dados)
        await self.contrato_repo.sincronizar_vigencia_contrato(contrato_id)
        return TermoAditivo.model_validate(novo)

    async def listar_por_contrato(self, contrato_id: int) -> List[TermoAditivo]:
        await self._verificar_contrato(contrato_id)
        itens = await self.repo.get_by_contrato(contrato_id)
        return [TermoAditivo.model_validate(i) for i in itens]

    async def buscar_por_id(self, contrato_id: int, aditivo_id: int) -> TermoAditivo:
        await self._verificar_contrato(contrato_id)
        item = await self.repo.get_by_id(aditivo_id)
        if not item or item["contrato_id"] != contrato_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Termo aditivo não encontrado")
        return TermoAditivo.model_validate(item)

    async def atualizar(self, contrato_id: int, aditivo_id: int, dados: TermoAditivoUpdate) -> TermoAditivo:
        await self.buscar_por_id(contrato_id, aditivo_id)
        if dados.tipo_id is not None:
            await self._validar_tipo(dados.tipo_id)

        atualizado = await self.repo.update(aditivo_id, dados)
        await self.contrato_repo.sincronizar_vigencia_contrato(contrato_id)
        return TermoAditivo.model_validate(atualizado)

    async def excluir(self, contrato_id: int, aditivo_id: int) -> dict:
        """Inativa o termo aditivo (soft delete)"""
        await self.buscar_por_id(contrato_id, aditivo_id)
        ok = await self.repo.delete(aditivo_id, contrato_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao inativar termo aditivo")
        await self.contrato_repo.sincronizar_vigencia_contrato(contrato_id)
        return {"message": "Termo aditivo inativado com sucesso"}

    async def excluir_definitivamente(self, contrato_id: int, aditivo_id: int) -> dict:
        """Exclusão definitiva"""
        await self._verificar_contrato(contrato_id)
        ok = await self.repo.hard_delete(aditivo_id, contrato_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Termo aditivo não encontrado")
        await self.contrato_repo.sincronizar_vigencia_contrato(contrato_id)
        return {"message": "Termo aditivo excluído definitivamente"}

    async def upload_arquivo(
        self,
        contrato_id: int,
        aditivo_id: int,
        arquivo: UploadFile,
    ) -> TermoAditivo:
        import os, aiofiles
        from pathlib import Path

        aditivo = await self.buscar_por_id(contrato_id, aditivo_id)

        BASE_DIR = Path(__file__).parent.parent.parent
        upload_dir = BASE_DIR / "uploads" / "aditivos" / str(contrato_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"aditivo_{aditivo_id}_{arquivo.filename}"
        filepath = upload_dir / filename

        async with aiofiles.open(filepath, "wb") as f:
            content = await arquivo.read()
            await f.write(content)

        insert_query = """
            INSERT INTO arquivo (nome_arquivo, caminho_arquivo, tamanho_bytes, tipo_mime, contrato_id, tipo_vinculo, termo_aditivo_id)
            VALUES ($1, $2, $3, $4, $5, 'termo_aditivo', $6)
            RETURNING id
        """
        relative_path = str(filepath.relative_to(BASE_DIR)).replace("\\", "/")
        arquivo_id = await self.repo.conn.fetchval(
            insert_query,
            arquivo.filename,
            relative_path,
            len(content),
            arquivo.content_type,
            contrato_id,
            aditivo_id,
        )

        atualizado = await self.repo.vincular_arquivo(aditivo_id, arquivo_id)
        return TermoAditivo.model_validate(atualizado)
