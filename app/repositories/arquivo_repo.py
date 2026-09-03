# app/repositories/arquivo_repo.py
import asyncpg
from typing import Dict, Optional 

class ArquivoRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create_arquivo(
        self,
        nome_arquivo: str,
        path_armazenamento: str,
        tipo_arquivo: str,
        tamanho_bytes: int,
        contrato_id: int,
        tipo_vinculo: str = 'contrato'
    ) -> Dict:
        query = """
            INSERT INTO arquivo (nome_arquivo, caminho_arquivo, tipo_mime, tamanho_bytes, contrato_id, tipo_vinculo)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, nome_arquivo, caminho_arquivo as path_armazenamento, tipo_mime as tipo_arquivo, tamanho_bytes, contrato_id, tipo_vinculo, ativo, created_at, updated_at
        """
        new_arquivo = await self.conn.fetchrow(
            query, nome_arquivo, path_armazenamento, tipo_arquivo, tamanho_bytes, contrato_id, tipo_vinculo
        )
        return dict(new_arquivo)
    
    async def create_arquivo_global(
        self,
        nome_arquivo: str,
        path_armazenamento: str,
        tipo_arquivo: str,
        tamanho_bytes: int
    ) -> Dict:
        """
        Cria um arquivo global (não vinculado a nenhum contrato específico).
        Usado para modelos de relatório e outros arquivos do sistema.
        """
        query = """
            INSERT INTO arquivo (nome_arquivo, caminho_arquivo, tipo_mime, tamanho_bytes, contrato_id)
            VALUES ($1, $2, $3, $4, NULL)
            RETURNING id, nome_arquivo, caminho_arquivo as path_armazenamento, tipo_mime as tipo_arquivo, tamanho_bytes, contrato_id, ativo, created_at, updated_at
        """
        new_arquivo = await self.conn.fetchrow(
            query, nome_arquivo, path_armazenamento, tipo_arquivo, tamanho_bytes
        )
        return dict(new_arquivo)

    async def link_arquivo_to_contrato(self, arquivo_id: int, contrato_id: int):
        """Define o arquivo como o documento principal do contrato."""
        query = "UPDATE contrato SET documento = $1 WHERE id = $2"
        # Converter arquivo_id para string, pois a coluna documento é VARCHAR
        await self.conn.execute(query, str(arquivo_id), contrato_id)
        
    async def find_arquivo_by_id(self, arquivo_id: int) -> Optional[Dict]:
        """Busca um arquivo pelo seu ID."""
        query = """
            SELECT id, nome_arquivo, caminho_arquivo as path_armazenamento,
                   tipo_mime as tipo_arquivo, tamanho_bytes, contrato_id,
                   ativo, created_at, updated_at
            FROM arquivo WHERE id = $1 AND ativo = TRUE
        """
        record = await self.conn.fetchrow(query, arquivo_id)
        return dict(record) if record else None
    
    async def get_arquivo_by_id(self, arquivo_id: int) -> Optional[Dict]:
        """Busca um arquivo pelo seu ID (alias para compatibilidade)."""
        arquivo = await self.find_arquivo_by_id(arquivo_id)
        if arquivo:
            # Retorna no formato esperado pelo config_service
            return {
                'id': arquivo['id'],
                'nome_original': arquivo['nome_arquivo'],
                'caminho': arquivo['path_armazenamento'],
                'tamanho': arquivo['tamanho_bytes'],
                'tipo_arquivo': arquivo['tipo_arquivo']
            }
        return None
    
    async def delete_arquivo(self, arquivo_id: int) -> bool:
        """Remove um arquivo do banco de dados (soft delete)."""
        query = "UPDATE arquivo SET ativo = FALSE, updated_at = NOW() WHERE id = $1"
        await self.conn.execute(query, arquivo_id)
        return True
