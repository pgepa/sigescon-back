from asyncpg import Connection
from fastapi import HTTPException
from app.schemas.relatorio_fiscalizacao_schema import RelatorioCreateSchema, RelatorioSalvarSchema

class RelatorioRepository:
    def __init__(self, db: Connection):
        self.db = db

    _DADOS_CONTRATO_QUERY = """
        SELECT
            c.id AS contrato_id,
            c.nr_contrato,
            c.pae,
            c.objeto,
            c.data_inicio,
            c.data_fim,
            c.valor_global,
            emp.nome AS empresa_nome,
            emp.cnpj AS empresa_cnpj,
            fiscal.nome AS fiscal_nome,
            fiscal.matricula AS numero_matricula,
            fiscal.email AS fiscal_email,
            gestor.nome AS gestor_nome,
            gestor.email AS gestor_email
        FROM contrato c
        LEFT JOIN contratado emp ON c.contratado_id = emp.id
        LEFT JOIN usuario fiscal ON c.fiscal_id = fiscal.id
        LEFT JOIN usuario gestor ON c.gestor_id = gestor.id
        WHERE {where}
    """

    async def get_dados_contrato_completo(self, nr_contrato: str):
        query = self._DADOS_CONTRATO_QUERY.format(where="c.nr_contrato = $1")
        resultado = await self.db.fetchrow(query, nr_contrato)
        if not resultado:
            raise HTTPException(status_code=404, detail="Contrato não encontrado no banco de dados.")
        return resultado

    async def get_dados_contrato_completo_by_id(self, contrato_id: int):
        """Mesma consulta acima, mas pelo ID numérico do contrato.

        nr_contrato costuma conter uma barra (ex: "30/2025"), o que quebra em
        proxies/Apache que não repassam "%2F" corretamente na URL. Usar o ID
        evita esse problema por completo.
        """
        query = self._DADOS_CONTRATO_QUERY.format(where="c.id = $1")
        resultado = await self.db.fetchrow(query, contrato_id)
        if not resultado:
            raise HTTPException(status_code=404, detail="Contrato não encontrado no banco de dados.")
        return resultado

    async def _colunas_existem(self, *colunas: str) -> dict[str, bool]:
        """Verifica quais colunas existem na tabela relatorio_fiscalizacao."""
        rows = await self.db.fetch(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'relatorio_fiscalizacao'
              AND column_name = ANY($1::text[])
            """,
            list(colunas),
        )
        encontradas = {r["column_name"] for r in rows}
        return {c: c in encontradas for c in colunas}

    async def get_relatorios_por_contrato_id(self, contrato_id: int):
        """Retorna todos os relatórios do fiscal (inclusive rascunhos)."""
        cols = await self._colunas_existem("updated_at", "gestor_observacao")
        extra = ""
        if cols["updated_at"]:
            extra += ", updated_at"
        if cols["gestor_observacao"]:
            extra += ", gestor_observacao"
        query = f"""
            SELECT id, periodo_inicio, periodo_fim, data_relatorio, status, created_at{extra}
            FROM relatorio_fiscalizacao
            WHERE contrato_id = $1
            ORDER BY created_at DESC
        """
        return await self.db.fetch(query, contrato_id)

    async def get_relatorios_para_gestor(self, contrato_id: int):
        """Retorna todos os relatórios do contrato, incluindo rascunhos, para acompanhamento do gestor/admin.
        Inclui os status antigos (enviado/aprovado/nao_conforme/finalizado) só para
        não esconder relatórios anteriores à migração para o fluxo Rascunho/Salvo."""
        cols = await self._colunas_existem("updated_at", "gestor_observacao")
        extra = ""
        if cols["updated_at"]:
            extra += ", updated_at"
        if cols["gestor_observacao"]:
            extra += ", gestor_observacao"
        query = f"""
            SELECT id, periodo_inicio, periodo_fim, data_relatorio, status, created_at{extra}
            FROM relatorio_fiscalizacao
            WHERE contrato_id = $1
              AND status IN ('rascunho', 'salvo', 'enviado', 'aprovado', 'nao_conforme', 'finalizado')
            ORDER BY created_at DESC
        """
        return await self.db.fetch(query, contrato_id)

    async def finalizar_relatorio(self, relatorio_id: int):
        """Fiscal finaliza o próprio relatório — muda status de rascunho para salvo.
        Sem aprovação de gestor: a partir daqui o relatório não é mais editável."""
        cols = await self._colunas_existem("updated_at")
        set_updated = ", updated_at = NOW()" if cols["updated_at"] else ""
        result = await self.db.fetchrow(
            f"""
            UPDATE relatorio_fiscalizacao
               SET status = 'salvo'{set_updated}
             WHERE id = $1 AND status = 'rascunho'
            RETURNING id, contrato_id
            """,
            relatorio_id,
        )
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Relatório não encontrado, ou não está em rascunho (já foi finalizado).",
            )
        return result

    async def get_relatorio_by_id(self, relatorio_id: int):
        query = """
            SELECT rf.*, c.nr_contrato
            FROM relatorio_fiscalizacao rf
            JOIN contrato c ON rf.contrato_id = c.id
            WHERE rf.id = $1
        """
        resultado = await self.db.fetchrow(query, relatorio_id)
        if not resultado:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")
        return resultado

    async def atualizar_relatorio(self, relatorio_id: int, dados: RelatorioSalvarSchema):
        status_atual = await self.db.fetchval(
            "SELECT status FROM relatorio_fiscalizacao WHERE id = $1", relatorio_id
        )
        if status_atual is None:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")
        if status_atual == "salvo":
            raise HTTPException(
                status_code=400,
                detail="Este relatório já foi finalizado (Salvo) e não pode mais ser editado.",
            )

        dados_dict = dados.model_dump(exclude_unset=True)
        if not dados_dict:
            return relatorio_id
        set_clauses = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(dados_dict.keys())])
        query = f"UPDATE relatorio_fiscalizacao SET {set_clauses} WHERE id = $1 RETURNING id"
        result = await self.db.fetchval(query, relatorio_id, *dados_dict.values())
        if not result:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")
        return result

    async def salvar_relatorio(self, contrato_id: int, dados: RelatorioSalvarSchema):
        try:
            # Criação: grava a linha inteira, inclusive perguntas ainda não
            # respondidas (usando os defaults do schema — False/"" para as
            # perguntas, None para as datas opcionais). NÃO usar exclude_unset
            # aqui — colunas booleanas são NOT NULL no banco, e um rascunho
            # parcial (fiscal salvou tendo respondido só as 3 primeiras
            # perguntas) tem que preencher as demais com o default, não deixar
            # a coluna de fora do INSERT.
            dados_dict = dados.model_dump()

            # Monta o INSERT dinamicamente para todos os itens do formulário
            colunas = ["contrato_id"] + list(dados_dict.keys())
            valores = [contrato_id] + list(dados_dict.values())
            
            # Gera os marcadores do asyncpg ($1, $2, $3...)
            marcadores = ", ".join([f"${i+1}" for i in range(len(valores))])
            nomes_colunas = ", ".join(colunas)
            
            query = f"INSERT INTO relatorio_fiscalizacao ({nomes_colunas}) VALUES ({marcadores}) RETURNING id"
            
            novo_id = await self.db.fetchval(query, *valores)
            return novo_id
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao salvar no banco: {str(e)}")