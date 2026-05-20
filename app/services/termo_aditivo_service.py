# app/services/termo_aditivo_service.py
import logging
from typing import List
from fastapi import HTTPException, status, UploadFile

from app.repositories.termo_aditivo_repo import TermoAditivoRepository
from app.repositories.contrato_repo import ContratoRepository
from app.schemas.termo_aditivo_schema import TermoAditivo, TermoAditivoCreate, TermoAditivoUpdate

logger = logging.getLogger(__name__)


class TermoAditivoService:
    def __init__(
        self,
        repo: TermoAditivoRepository,
        contrato_repo: ContratoRepository,
    ):
        self.repo = repo
        self.contrato_repo = contrato_repo

    async def _verificar_contrato(self, contrato_id: int):
        contrato = await self.contrato_repo.find_contrato_by_id(contrato_id)
        if not contrato:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
        return contrato

    async def criar(self, contrato_id: int, dados: TermoAditivoCreate) -> TermoAditivo:
        await self._verificar_contrato(contrato_id)
        novo = await self.repo.create(contrato_id, dados)
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
        atualizado = await self.repo.update(aditivo_id, dados)
        return TermoAditivo.model_validate(atualizado)

    async def excluir(self, contrato_id: int, aditivo_id: int) -> dict:
        await self.buscar_por_id(contrato_id, aditivo_id)
        ok = await self.repo.delete(aditivo_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao excluir termo aditivo")
        return {"message": "Termo aditivo excluído com sucesso"}

    async def upload_arquivo(
        self,
        contrato_id: int,
        aditivo_id: int,
        arquivo: UploadFile,
    ) -> TermoAditivo:
        import os, aiofiles
        from app.core.config import settings

        aditivo = await self.buscar_por_id(contrato_id, aditivo_id)

        upload_dir = os.path.join(settings.UPLOAD_DIR, "aditivos", str(contrato_id))
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"aditivo_{aditivo_id}_{arquivo.filename}"
        filepath = os.path.join(upload_dir, filename)

        async with aiofiles.open(filepath, "wb") as f:
            content = await arquivo.read()
            await f.write(content)

        # Registra o arquivo na tabela arquivo
        insert_query = """
            INSERT INTO arquivo (nome_arquivo, caminho_arquivo, tamanho_bytes, tipo_mime, contrato_id, tipo_vinculo)
            VALUES ($1, $2, $3, $4, $5, 'termo_aditivo')
            RETURNING id
        """
        arquivo_id = await self.repo.conn.fetchval(
            insert_query,
            arquivo.filename,
            filepath,
            len(content),
            arquivo.content_type,
            contrato_id,
        )

        atualizado = await self.repo.vincular_arquivo(aditivo_id, arquivo_id)
        return TermoAditivo.model_validate(atualizado)
