# app/repositories/contrato_repo.py
import asyncpg
import logging
from typing import List, Optional, Dict, Tuple

from app.schemas.contrato_schema import ContratoCreate, ContratoUpdate

logger = logging.getLogger(__name__)

class ContratoRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create_contrato(self, contrato: ContratoCreate) -> Dict:
        # Usar campos específicos para evitar problemas de tipo
        query = """
            INSERT INTO contrato (
                nr_contrato, objeto, data_inicio, data_fim, contratado_id,
                modalidade_id, status_id, gestor_id, fiscal_id,
                valor_anual, valor_global, base_legal, termos_contratuais,
                fiscal_substituto_id, pae, doe, data_doe, garantia,
                portaria_fiscal, nr_adesao_ata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
            RETURNING id
        """

        new_contrato_id = await self.conn.fetchval(
            query,
            str(contrato.nr_contrato),
            str(contrato.objeto),
            contrato.data_inicio,
            contrato.data_fim,
            int(contrato.contratado_id),
            int(contrato.modalidade_id),
            int(contrato.status_id),
            int(contrato.gestor_id) if contrato.gestor_id is not None else None,
            int(contrato.fiscal_id) if contrato.fiscal_id is not None else None,
            float(contrato.valor_anual) if contrato.valor_anual is not None else None,
            float(contrato.valor_global) if contrato.valor_global is not None else None,
            str(contrato.base_legal) if contrato.base_legal is not None else None,
            str(contrato.termos_contratuais) if contrato.termos_contratuais is not None else None,
            int(contrato.fiscal_substituto_id) if contrato.fiscal_substituto_id is not None else None,
            str(contrato.pae) if contrato.pae is not None else None,
            str(contrato.doe) if contrato.doe is not None else None,
            contrato.data_doe,
            contrato.garantia,
            str(contrato.portaria_fiscal) if contrato.portaria_fiscal is not None else None,
            str(contrato.nr_adesao_ata) if contrato.nr_adesao_ata is not None else None,
        )
        return await self.find_contrato_by_id(new_contrato_id)


    # --- QUERY CORRIGIDA ---
    async def find_contrato_by_id(self, contrato_id: int, user_context: Optional[Dict] = None) -> Optional[Dict]:
        # Garante que contrato_id seja um inteiro
        contrato_id = int(contrato_id)
        
        query = """
            SELECT
                c.*,
                ct.nome AS contratado_nome,
                m.nome AS modalidade_nome,
                s.nome AS status_nome,
                gestor.nome AS gestor_nome,
                fiscal.nome AS fiscal_nome,
                fiscal_sub.nome AS fiscal_substituto_nome
            FROM contrato c
            LEFT JOIN contratado ct ON c.contratado_id = ct.id
            LEFT JOIN modalidade m ON c.modalidade_id = m.id
            LEFT JOIN status s ON c.status_id = s.id
            LEFT JOIN usuario gestor ON c.gestor_id = gestor.id
            LEFT JOIN usuario fiscal ON c.fiscal_id = fiscal.id
            LEFT JOIN usuario fiscal_sub ON c.fiscal_substituto_id = fiscal_sub.id
            WHERE c.id = $1 AND c.ativo = TRUE
        """
        params = [contrato_id]

        # Aplicar isolamento por perfil
        if user_context:
            usuario_id = user_context.get('usuario_id')
            perfil_ativo = user_context.get('perfil_ativo_nome')
            
            # Garante que usuario_id seja um inteiro
            if usuario_id is not None:
                usuario_id = int(usuario_id)
            
            if perfil_ativo == 'Fiscal' and usuario_id is not None:
                # Fiscal vê apenas contratos onde é fiscal ou fiscal substituto
                query += " AND (c.fiscal_id = $2 OR c.fiscal_substituto_id = $2)"
                params.append(usuario_id)
            elif perfil_ativo == 'Gestor' and usuario_id is not None:
                # Gestor vê apenas contratos onde é gestor
                query += " AND c.gestor_id = $2"
                params.append(usuario_id)
            # Administrador vê todos (sem filtro adicional)

        contrato = await self.conn.fetchrow(query, *params)
        return dict(contrato) if contrato else None


    async def get_all_contratos(
        self,
        filters: Optional[Dict] = None,
        order_by: str = 'c.data_fim DESC',
        limit: int = 10,
        offset: int = 0,
        user_context: Optional[Dict] = None
    ) -> Tuple[List[Dict], int]:
        
        base_query = """
            FROM contrato c
            LEFT JOIN contratado ct ON c.contratado_id = ct.id
            LEFT JOIN modalidade m ON c.modalidade_id = m.id
            LEFT JOIN status s ON c.status_id = s.id
        """
        where_clauses = ["c.ativo = TRUE"]
        params = []
        param_idx = 1

        # Aplicar isolamento por perfil
        if user_context:
            usuario_id = user_context.get('usuario_id')
            perfil_ativo = user_context.get('perfil_ativo_nome')

            if perfil_ativo == 'Fiscal':
                # Fiscal vê apenas contratos onde é fiscal ou fiscal substituto
                where_clauses.append(f"(c.fiscal_id = ${param_idx} OR c.fiscal_substituto_id = ${param_idx})")
                params.append(usuario_id)
                param_idx += 1
            elif perfil_ativo == 'Gestor':
                # Gestor vê apenas contratos onde é gestor
                where_clauses.append(f"c.gestor_id = ${param_idx}")
                params.append(usuario_id)
                param_idx += 1
            # Administrador vê todos (sem filtro adicional)

        if filters:
            for key, value in filters.items():
                if value is None:
                    continue
                column_map = {'gestor_id': 'c.gestor_id', 'fiscal_id': 'c.fiscal_id', 'contratado_id': 'c.contratado_id', 'modalidade_id': 'c.modalidade_id', 'status_id': 'c.status_id', 'ano': 'EXTRACT(YEAR FROM c.data_inicio)'}
                if key in column_map:
                    where_clauses.append(f"{column_map[key]} = ${param_idx}")
                    params.append(value)
                    param_idx += 1
                elif key in ['objeto', 'nr_contrato', 'pae']:
                    where_clauses.append(f"c.{key} ILIKE ${param_idx}")
                    params.append(f"%{value}%")
                    param_idx += 1
                elif key == 'contratado_nome':
                    where_clauses.append(f"ct.nome ILIKE ${param_idx}")
                    params.append(f"%{value}%")
                    param_idx += 1
                elif key == 'search':
                    # Busca livre: bate em número do contrato, objeto ou nome do contratado
                    where_clauses.append(
                        f"(c.nr_contrato ILIKE ${param_idx} OR c.objeto ILIKE ${param_idx} OR ct.nome ILIKE ${param_idx})"
                    )
                    params.append(f"%{value}%")
                    param_idx += 1
                elif key == 'data_inicio':
                    # Contratos cuja vigência começa em ou após essa data
                    where_clauses.append(f"c.data_inicio >= ${param_idx}")
                    params.append(value)
                    param_idx += 1
                elif key == 'data_fim':
                    # Contratos cuja vigência termina em ou antes dessa data
                    where_clauses.append(f"c.data_fim <= ${param_idx}")
                    params.append(value)
                    param_idx += 1
                elif key == 'vencimento_dias':
                    # Filtro por proximidade de vencimento (cumulativo - "ou menos")
                    # Considera apenas contratos com status "Ativo"
                    print(f"🔍 REPO: Processando filtro vencimento_dias: {value}")
                    dias_list = [int(d.strip()) for d in value.split(',') if d.strip().isdigit()]
                    print(f"🔍 REPO: Dias extraídos: {dias_list}")
                    if dias_list:
                        # Pegar o maior valor para filtro cumulativo
                        max_dias = max(dias_list)
                        print(f"🔍 REPO: Aplicando filtro para {max_dias} dias ou menos (apenas contratos ativos)")
                        where_clauses.append(f"c.data_fim IS NOT NULL")
                        where_clauses.append(f"c.data_fim > CURRENT_DATE")
                        where_clauses.append(f"(c.data_fim - CURRENT_DATE) <= {max_dias}")
                        where_clauses.append(f"s.nome = 'Ativo'")
                elif key == 'tem_garantia':
                    # Filtro para contratos que possuem garantia
                    print(f"🛡️ REPO: Processando filtro tem_garantia: {value}")
                    if value is True:
                        print(f"🛡️ REPO: Aplicando filtro para contratos COM garantia")
                        where_clauses.append(f"c.garantia IS NOT NULL")
                    elif value is False:
                        print(f"🛡️ REPO: Aplicando filtro para contratos SEM garantia")
                        where_clauses.append(f"c.garantia IS NULL")
                elif key == 'garantia_prazo_dias':
                    # Filtro por prazo de vencimento da garantia (apenas se tem_garantia=True)
                    print(f"🛡️ REPO: Processando filtro garantia_prazo_dias: {value}")
                    if value and value.strip().isdigit():
                        dias = int(value.strip())
                        print(f"🛡️ REPO: Aplicando filtro para garantias que vencem em até {dias} dias")
                        where_clauses.append(f"c.garantia IS NOT NULL")
                        where_clauses.append(f"c.garantia > CURRENT_DATE")
                        where_clauses.append(f"(c.garantia - CURRENT_DATE) <= {dias}")
                    elif value and value.strip():
                        # Se não for um número válido, ignorar o filtro mas logar
                        print(f"🛡️ REPO: AVISO - Valor inválido para garantia_prazo_dias: {value}")
        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        count_query = f"SELECT COUNT(c.id) AS total {base_query}{where_sql}"
        total_items = await self.conn.fetchval(count_query, *params)
        data_query = f"""
            SELECT
                c.id, c.nr_contrato, c.objeto, c.data_fim,
                c.fiscal_id, c.gestor_id,
                ct.nome as contratado_nome,
                s.nome as status_nome,
                fiscal.nome as fiscal_nome,
                gestor.nome as gestor_nome,
                (SELECT COUNT(*) FROM termo_aditivo ta WHERE ta.contrato_id = c.id AND ta.ativo = TRUE) as total_aditivos
            {base_query}
            LEFT JOIN usuario fiscal ON c.fiscal_id = fiscal.id
            LEFT JOIN usuario gestor ON c.gestor_id = gestor.id
            {where_sql}
            ORDER BY {order_by}
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        paginated_params = params + [limit, offset]
        contratos = await self.conn.fetch(data_query, *paginated_params)
        return [dict(c) for c in contratos], total_items if total_items is not None else 0


    async def update_contrato(self, contrato_id: int, contrato: ContratoUpdate) -> Optional[Dict]:
        try:
            # Debug inicial
            print(f"\n=== DEBUG CONTRATO UPDATE ===")
            print(f"Contrato ID: {contrato_id} (tipo: {type(contrato_id)})")
            print(f"Objeto ContratoUpdate: {contrato}")
            
            # Usar abordagem simples - deixar Pydantic e asyncpg lidarem com os tipos
            update_data = contrato.model_dump(exclude_unset=True)
            print(f"Model dump result: {update_data}")
            print(f"Model dump types: {[(k, type(v).__name__) for k, v in update_data.items()]}")
            
            if not update_data:
                print("Nenhum dado para atualizar - retornando contrato existente")
                return await self.find_contrato_by_id(contrato_id)

            # Construir UPDATE de forma simples
            set_clauses = []
            values = []
            param_index = 1

            print(f"Construindo query...")
            for field, value in update_data.items():
                print(f"  Campo {field}: {value} (tipo: {type(value).__name__})")
                set_clauses.append(f"{field} = ${param_index}")
                values.append(value)
                param_index += 1

            # Adicionar contrato_id para WHERE
            values.append(contrato_id)
            where_param = param_index
            print(f"Adicionado contrato_id para WHERE: {contrato_id} (tipo: {type(contrato_id).__name__})")

            query = f"""
                UPDATE contrato
                SET {', '.join(set_clauses)}, updated_at = NOW()
                WHERE id = ${where_param} AND ativo = TRUE
                RETURNING id
            """

            print(f"Query final: {query}")
            print(f"Valores finais: {values}")
            print(f"Tipos finais: {[type(v).__name__ for v in values]}")
            print(f"=== FIM DEBUG ===\n")
            
            # Executar query
            updated_id = await self.conn.fetchval(query, *values)
            
            if updated_id:
                logger.info(f"Contrato {contrato_id} atualizado com sucesso")
                return await self.find_contrato_by_id(updated_id)
            else:
                logger.warning(f"Contrato {contrato_id} não encontrado para atualização")
                return None
                
        except Exception as e:
            print(f"\n=== ERRO CRÍTICO ===")
            print(f"Erro: {e}")
            print(f"Tipo do erro: {type(e).__name__}")
            print(f"Contrato ID: {contrato_id}")
            if 'update_data' in locals():
                print(f"Update data: {update_data}")
            if 'query' in locals():
                print(f"Query: {query}")
            if 'values' in locals():
                print(f"Values: {values}")
                print(f"Types: {[type(v).__name__ for v in values]}")
            print(f"=== FIM ERRO ===\n")
            
            logger.error(f"ERRO CRÍTICO - Contrato {contrato_id}: {e}")
            raise


    async def atualizar_vigencia_por_aditivo(self, contrato_id: int, nova_data_fim) -> None:
        """
        Reflete no contrato a extensão de vigência de um termo aditivo de Prazo/Misto.
        Só estende data_fim (nunca reduz, para não sobrescrever com um aditivo mais
        antigo/menor por engano) e, se o contrato estava "Encerrado" e a nova data
        ainda não venceu, reabre automaticamente para "Ativo". Não mexe em contratos
        "Suspenso"/"Cancelado" — esses continuam sendo decisão manual.
        """
        query = """
            UPDATE contrato
            SET
                data_fim = $2,
                status_id = CASE
                    WHEN status_id = (SELECT id FROM status WHERE nome = 'Encerrado')
                         AND $2::date >= CURRENT_DATE
                    THEN (SELECT id FROM status WHERE nome = 'Ativo')
                    ELSE status_id
                END,
                updated_at = NOW()
            WHERE id = $1 AND $2::date > data_fim
        """
        await self.conn.execute(query, contrato_id, nova_data_fim)

    async def delete_contrato(self, contrato_id: int) -> bool:
        """
        Soft delete do contrato e de todos os relacionamentos em cascata:
        - Marca o contrato como ativo = FALSE
        - Marca todas as pendências do contrato como ativo = FALSE
        - Marca todos os relatórios fiscais do contrato como ativo = FALSE
        """
        try:
            # 1. Soft delete das pendências relacionadas ao contrato
            await self.conn.execute(
                "UPDATE pendenciarelatorio SET ativo = FALSE, updated_at = NOW() WHERE contrato_id = $1 AND ativo = TRUE",
                contrato_id
            )

            # 2. Soft delete dos relatórios fiscais relacionados ao contrato
            await self.conn.execute(
                "UPDATE relatoriofiscal SET ativo = FALSE, updated_at = NOW() WHERE contrato_id = $1 AND ativo = TRUE",
                contrato_id
            )

            # 3. Soft delete do contrato
            query = "UPDATE contrato SET ativo = FALSE, updated_at = NOW() WHERE id = $1 AND ativo = TRUE"
            status = await self.conn.execute(query, contrato_id)

            return status.endswith('1')
        except Exception as e:
            logger.error(f"Erro ao fazer soft delete do contrato {contrato_id}: {e}")
            raise
    
    async def get_by_id(self, contrato_id: int) -> Optional[Dict]:
        """Alias para find_contrato_by_id para manter consistência com outros repositories"""
        return await self.find_contrato_by_id(contrato_id)
    
    async def get_contrato_by_id(self, contrato_id: int) -> Optional[Dict]:
        """Alias adicional para compatibilidade"""
        return await self.find_contrato_by_id(contrato_id)

    # Métodos para gerenciamento de arquivos do contrato
    async def get_arquivos_contrato(self, contrato_id: int) -> List[Dict]:
        """Busca todos os arquivos vinculados ao contrato (contrato, portaria, termo_aditivo)"""
        query = """
            SELECT
                a.id,
                a.nome_arquivo,
                a.tipo_mime as tipo_arquivo,
                a.tamanho_bytes,
                a.contrato_id,
                a.tipo_vinculo,
                a.created_at::text as created_at,
                a.termo_aditivo_id,
                ta.numero_aditivo as termo_aditivo_numero
            FROM arquivo a
            LEFT JOIN termo_aditivo ta ON a.termo_aditivo_id = ta.id AND ta.ativo = TRUE
            WHERE a.contrato_id = $1
              AND a.tipo_vinculo IN ('contrato', 'portaria', 'ata', 'termo_aditivo')
              AND a.ativo = TRUE
            ORDER BY a.tipo_vinculo, a.created_at DESC
        """
        rows = await self.conn.fetch(query, contrato_id)
        return [dict(row) for row in rows]

    async def get_arquivo_by_id(self, arquivo_id: int, contrato_id: int) -> Optional[Dict]:
        """Busca um arquivo específico pelo id e contrato (qualquer tipo_vinculo)"""
        query = """
            SELECT
                id,
                nome_arquivo,
                caminho_arquivo as path_armazenamento,
                tipo_mime as tipo_arquivo,
                tamanho_bytes,
                contrato_id,
                tipo_vinculo,
                created_at::text as created_at
            FROM arquivo
            WHERE id = $1 AND contrato_id = $2 AND ativo = TRUE
        """
        row = await self.conn.fetchrow(query, arquivo_id, contrato_id)
        return dict(row) if row else None

    async def is_arquivo_de_relatorio(self, arquivo_id: int) -> bool:
        """Verifica se um arquivo é de relatório fiscal (está na tabela relatoriofiscal)"""
        query = """
            SELECT 1 FROM relatoriofiscal
            WHERE arquivo_id = $1
            LIMIT 1
        """
        try:
            result = await self.conn.fetchval(query, arquivo_id)
            return bool(result)
        except Exception as e:
            print(f"Erro ao verificar se arquivo {arquivo_id} é de relatório: {e}")
            return False

    async def check_arquivo_used_in_relatorios(self, arquivo_id: int) -> List[Dict]:
        """Verifica se um arquivo está sendo usado por relatórios fiscais"""
        query = """
            SELECT rf.id, rf.mes_competencia, rf.observacoes_fiscal,
                   rf.contrato_id, c.nr_contrato
            FROM relatoriofiscal rf
            JOIN contrato c ON rf.contrato_id = c.id
            WHERE rf.arquivo_id = $1
        """
        try:
            rows = await self.conn.fetch(query, arquivo_id)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Erro ao verificar relatórios vinculados ao arquivo {arquivo_id}: {e}")
            return []

    async def delete_arquivo(self, arquivo_id: int, contrato_id: int) -> bool:
        """Remove um arquivo específico de um contrato"""
        query = "DELETE FROM arquivo WHERE id = $1 AND contrato_id = $2"
        status = await self.conn.execute(query, arquivo_id, contrato_id)
        return status.endswith('1')

    async def count_arquivos_contrato(self, contrato_id: int) -> int:
        """Conta o número total de arquivos de um contrato"""
        query = "SELECT COUNT(*) FROM arquivo WHERE contrato_id = $1"
        return await self.conn.fetchval(query, contrato_id)
    
    async def exists_nr_contrato(self, nr_contrato: str, exclude_id: Optional[int] = None) -> bool:
        """Verifica se um número de contrato já existe (apenas contratos ativos)"""
        print(f"\n=== DEBUG exists_nr_contrato ===")
        print(f"nr_contrato: {nr_contrato} (tipo: {type(nr_contrato).__name__})")
        print(f"exclude_id: {exclude_id} (tipo: {type(exclude_id).__name__})")
        
        # Garante que nr_contrato seja sempre uma string
        nr_contrato_str = str(nr_contrato)
        print(f"nr_contrato_str: {nr_contrato_str} (tipo: {type(nr_contrato_str).__name__})")
        
        try:
            if exclude_id:
                query = "SELECT EXISTS(SELECT 1 FROM contrato WHERE nr_contrato = $1 AND ativo = TRUE AND id != $2)"
                print(f"Query: {query}")
                print(f"Parâmetros: [{nr_contrato_str}, {exclude_id}]")
                print(f"Tipos: [{type(nr_contrato_str).__name__}, {type(exclude_id).__name__}]")
                result = await self.conn.fetchval(query, nr_contrato_str, exclude_id)
                print(f"Resultado: {result}")
                return result
            else:
                query = "SELECT EXISTS(SELECT 1 FROM contrato WHERE nr_contrato = $1 AND ativo = TRUE)"
                print(f"Query: {query}")
                print(f"Parâmetros: [{nr_contrato_str}]")
                result = await self.conn.fetchval(query, nr_contrato_str)
                print(f"Resultado: {result}")
                return result
        except Exception as e:
            print(f"ERRO em exists_nr_contrato: {e}")
            print(f"=== FIM DEBUG exists_nr_contrato ===\n")
            raise
    
    async def get_next_available_nr_contrato(self) -> str:
        """Retorna o próximo número de contrato disponível"""
        query = """
            SELECT COALESCE(MAX(CAST(nr_contrato AS INTEGER)), 0) + 1
            FROM contrato 
            WHERE ativo = TRUE 
            AND nr_contrato ~ '^[0-9]+$'
        """
        next_number = await self.conn.fetchval(query)
        return str(next_number)