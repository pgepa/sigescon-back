# app/services/file_service.py
import aiofiles
import os
import secrets
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from typing import Tuple, List, Dict, Any

# Caminho absoluto para a pasta uploads na raiz do projeto
UPLOAD_DIRECTORY = str(Path(__file__).parent.parent.parent / "uploads")
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'odt', 'ods'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB por arquivo
MAX_TOTAL_SIZE = 250 * 1024 * 1024  # 250MB total
MAX_FILES_COUNT = 10  # Máximo 10 arquivos por upload

class FileService:
    def __init__(self, upload_dir: str = UPLOAD_DIRECTORY):
        self.upload_dir = upload_dir
        # Garante que o diretório de uploads exista
        os.makedirs(self.upload_dir, exist_ok=True)

    def _is_allowed(self, filename: str) -> bool:
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def _validate_file_size(self, file: UploadFile) -> None:
        """Valida o tamanho de um arquivo individual"""
        if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo '{file.filename}' excede o tamanho máximo de {MAX_FILE_SIZE // (1024*1024)}MB"
            )

    def _validate_files_batch(self, files: List[UploadFile]) -> None:
        """Valida um lote de arquivos"""
        if len(files) > MAX_FILES_COUNT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Máximo de {MAX_FILES_COUNT} arquivos permitidos por upload"
            )

        total_size = 0
        for file in files:
            if hasattr(file, 'size') and file.size:
                total_size += file.size

        if total_size > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Tamanho total dos arquivos excede {MAX_TOTAL_SIZE // (1024*1024)}MB"
            )

    async def save_upload_file(self, contrato_id: int, file: UploadFile) -> Tuple[str, str, int]:
        """
        Valida e guarda um ficheiro de upload.
        Retorna (nome_original, caminho_completo, tamanho_em_bytes).
        """
        if not self._is_allowed(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de ficheiro não permitido. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Valida tamanho do arquivo
        self._validate_file_size(file)

        # Cria um subdiretório para cada contrato para manter os ficheiros organizados
        contrato_upload_folder = os.path.join(self.upload_dir, str(contrato_id))
        os.makedirs(contrato_upload_folder, exist_ok=True)

        # Cria um nome de ficheiro único para evitar conflitos
        original_filename = file.filename
        name, ext = os.path.splitext(original_filename)
        file_hash = secrets.token_hex(4)
        unique_filename = f"{name}_{file_hash}{ext}"

        file_path = os.path.join(contrato_upload_folder, unique_filename)

        try:
            # Escreve o ficheiro no disco de forma assíncrona
            async with aiofiles.open(file_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)

            file_size = os.path.getsize(file_path)
            return original_filename, file_path, file_size
        except Exception as e:
            # Em caso de erro, remove o ficheiro parcialmente escrito se existir
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao guardar o ficheiro: {e}"
            )

    async def save_multiple_upload_files(self, contrato_id: int, files: List[UploadFile]) -> List[Dict[str, Any]]:
        """
        Valida e guarda múltiplos ficheiros de upload.
        Retorna lista com informações de cada arquivo salvo.
        """
        if not files or all(not file.filename for file in files):
            return []

        # Remove arquivos vazios/inválidos
        valid_files = [file for file in files if file.filename and file.filename.strip()]

        if not valid_files:
            return []

        # Valida o lote de arquivos
        self._validate_files_batch(valid_files)

        saved_files = []
        failed_files = []

        for file in valid_files:
            try:
                # Valida cada arquivo individualmente
                if not self._is_allowed(file.filename):
                    failed_files.append({
                        'filename': file.filename,
                        'error': f"Tipo não permitido. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}"
                    })
                    continue

                # Salva o arquivo
                original_filename, file_path, file_size = await self.save_upload_file(contrato_id, file)

                saved_files.append({
                    'original_filename': original_filename,
                    'file_path': file_path,
                    'file_size': file_size,
                    'content_type': file.content_type
                })

            except HTTPException as e:
                failed_files.append({
                    'filename': file.filename,
                    'error': e.detail
                })
            except Exception as e:
                failed_files.append({
                    'filename': file.filename,
                    'error': f"Erro inesperado: {str(e)}"
                })

        # Se houver falhas, inclui na resposta
        if failed_files:
            error_details = []
            for failed in failed_files:
                error_details.append(f"{failed['filename']}: {failed['error']}")

            # Se todos falharam, levanta exceção
            if not saved_files:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Nenhum arquivo foi salvo. Erros: {'; '.join(error_details)}"
                )

            # Se alguns falharam, adiciona informação de warning
            for saved_file in saved_files:
                saved_file['warnings'] = error_details

        return saved_files

    async def delete_file(self, file_path: str) -> bool:
        """
        Remove um arquivo físico do sistema de arquivos.

        Args:
            file_path: Caminho completo para o arquivo

        Returns:
            bool: True se removido com sucesso, False caso contrário
        """
        try:
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            else:
                # Arquivo já não existe, considera como "removido"
                return True
        except Exception as e:
            # Log do erro mas não falha a operação
            print(f"Erro ao remover arquivo físico {file_path}: {e}")
            return False