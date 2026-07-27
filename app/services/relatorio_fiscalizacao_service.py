import os
import platform
import shutil
import subprocess
from tempfile import NamedTemporaryFile
from docxtpl import DocxTemplate
from app.repositories.relatorio_fiscalizacao_repo import RelatorioRepository
from app.schemas.relatorio_fiscalizacao_schema import RelatorioCreateSchema, RelatorioRevisarSchema
from app.services.email_service import EmailService


def _get_soffice_path() -> str:
    if platform.system() == "Windows":
        candidates = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        raise FileNotFoundError(
            "LibreOffice não encontrado. Instale em https://www.libreoffice.org/download/ "
            "e reinicie o servidor."
        )
    cmd = shutil.which("libreoffice") or shutil.which("soffice")
    if not cmd:
        raise FileNotFoundError("LibreOffice não encontrado no PATH.")
    return cmd


class RelatorioService:
    def __init__(self, relatorio_repo: RelatorioRepository):
        self.repo = relatorio_repo
        self.template_path = "templates/template_fiscalizacao.docx"

    def _x(self, condition) -> str:
        return "X" if condition else " "

    def _build_contexto(self, dados_banco, f: dict) -> dict:
        def fmt_date(dt):
            return dt.strftime('%d/%m/%Y') if dt else ""

        valor_global_fmt = ""
        if dados_banco['valor_global']:
            valor_global_fmt = (
                f"R$ {dados_banco['valor_global']:,.2f}"
                .replace(",", "X").replace(".", ",").replace("X", ".")
            )

        return {
            "nr_contrato": dados_banco['nr_contrato'],
            "pae": dados_banco['pae'],
            "objeto": dados_banco['objeto'],
            "data_inicio": fmt_date(dados_banco['data_inicio']),
            "data_fim": fmt_date(dados_banco['data_fim']),
            "valor_global": valor_global_fmt,
            "empresa_nome": dados_banco['empresa_nome'],
            "empresa_cnpj": dados_banco['empresa_cnpj'],
            "fiscal_nome": dados_banco['fiscal_nome'],
            "numero_matricula": dados_banco['numero_matricula'],

            "periodo_de": fmt_date(f.get('periodo_inicio')),
            "periodo_ate": fmt_date(f.get('periodo_fim')),
            "data_relatorio": fmt_date(f.get('data_relatorio')),

            "q1s": self._x(f.get('execucao_objeto_sim')),
            "q1n": self._x(not f.get('execucao_objeto_sim')),
            "execucao_objeto_d": f.get('execucao_objeto_detalhes', ''),

            "q2s": self._x(f.get('prazo_execucao_sim')),
            "q2n": self._x(not f.get('prazo_execucao_sim')),
            "prazo_execucao_d": f.get('prazo_execucao_detalhes', ''),

            "q3s": self._x(f.get('nivel_qualidade_sim')),
            "q3n": self._x(not f.get('nivel_qualidade_sim')),
            "nivel_qualidade_d": f.get('nivel_qualidade_detalhes', ''),

            "q4s": self._x(f.get('medicoes_servicos_sim')),
            "q4n": self._x(not f.get('medicoes_servicos_sim')),
            "medicoes_servicos_d": f.get('medicoes_servicos_detalhes', ''),

            "q5s": self._x(f.get('ocorrencias_sim')),
            "q5n": self._x(not f.get('ocorrencias_sim')),
            "ocorrencias_d": f.get('ocorrencias_detalhes', ''),

            "q6s": self._x(f.get('documentos_habilitacao_sim')),
            "q6n": self._x(not f.get('documentos_habilitacao_sim')),
            "documentos_habilitacao_d": f.get('documentos_habilitacao_detalhes', ''),

            "q7s": self._x(f.get('subcontratacao_sim')),
            "q7n": self._x(not f.get('subcontratacao_sim')),
            "subcontratacao_d": f.get('subcontratacao_detalhes', ''),

            "q8s": self._x(f.get('obrigacoes_empregados_resposta') == "sim"),
            "q8n": self._x(f.get('obrigacoes_empregados_resposta') == "nao"),
            "q8a": self._x(f.get('obrigacoes_empregados_resposta') == "na"),
            "obrigacoes_empregados_d": f.get('obrigacoes_empregados_detalhes', ''),

            "q9s": self._x(f.get('garantias_contratuais_resposta') == "sim"),
            "q9n": self._x(f.get('garantias_contratuais_resposta') == "nao"),
            "q9a": self._x(f.get('garantias_contratuais_resposta') == "na"),
            "garantias_contratuais_d": f.get('garantias_contratuais_detalhes', ''),

            "q10s": self._x(f.get('execucao_satisfatoria_sim')),
            "q10n": self._x(not f.get('execucao_satisfatoria_sim')),
            "execucao_satisfatoria_d": f.get('execucao_satisfatoria_detalhes', ''),
        }

    def _render_docx_to_pdf(self, contexto: dict):
        doc = DocxTemplate(self.template_path)
        doc.render(contexto)

        with NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
            doc.save(tmp_docx.name)
            tmp_docx_path = tmp_docx.name

        output_dir = os.path.dirname(tmp_docx_path)
        soffice = _get_soffice_path()
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", tmp_docx_path, "--outdir", output_dir],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Erro na conversão do LibreOffice: {e.stderr.decode()}")

        return tmp_docx_path.replace(".docx", ".pdf"), tmp_docx_path

    async def enviar_para_gestor(self, relatorio_id: int):
        """Fiscal envia o relatório. Notifica o gestor por email."""
        result = await self.repo.enviar_relatorio(relatorio_id)
        contrato_id = result["contrato_id"]

        # Busca dados do contrato para montar o email
        dados = await self.repo.db.fetchrow(
            """
            SELECT c.nr_contrato,
                   fiscal.nome  AS fiscal_nome,
                   gestor.email AS gestor_email,
                   gestor.nome  AS gestor_nome
              FROM contrato c
              LEFT JOIN usuario fiscal ON c.fiscal_id = fiscal.id
              LEFT JOIN usuario gestor ON c.gestor_id = gestor.id
             WHERE c.id = $1
            """,
            contrato_id,
        )

        if dados and dados["gestor_email"]:
            assunto = f"Novo Relatório de Fiscalização — Contrato {dados['nr_contrato']}"
            corpo = (
                f"Olá, {dados['gestor_nome'] or 'Gestor'},\n\n"
                f"O fiscal {dados['fiscal_nome']} enviou um relatório de fiscalização "
                f"do contrato {dados['nr_contrato']} para sua análise.\n\n"
                f"Acesse o sistema para revisar.\n\n"
                f"Sistema SIGESCON"
            )
            await EmailService.send_email(dados["gestor_email"], assunto, corpo)

        return result

    async def revisar_relatorio(self, relatorio_id: int, dados: RelatorioRevisarSchema):
        """Gestor aprova ou retorna como não conforme. Notifica o fiscal por email."""
        await self.repo.revisar_relatorio(relatorio_id, dados)

        info = await self.repo.db.fetchrow(
            """
            SELECT c.nr_contrato,
                   gestor.nome  AS gestor_nome,
                   fiscal.email AS fiscal_email,
                   fiscal.nome  AS fiscal_nome
              FROM relatorio_fiscalizacao rf
              JOIN contrato c ON rf.contrato_id = c.id
              LEFT JOIN usuario gestor ON c.gestor_id = gestor.id
              LEFT JOIN usuario fiscal ON c.fiscal_id = fiscal.id
             WHERE rf.id = $1
            """,
            relatorio_id,
        )

        if info and info["fiscal_email"]:
            if dados.status == "aprovado":
                assunto = f"Relatório Aprovado — Contrato {info['nr_contrato']}"
                corpo = (
                    f"Olá, {info['fiscal_nome'] or 'Fiscal'},\n\n"
                    f"O gestor {info['gestor_nome']} aprovou seu relatório de fiscalização "
                    f"do contrato {info['nr_contrato']}.\n\n"
                    f"A execução foi considerada conforme o contrato.\n\n"
                    f"Sistema SIGESCON"
                )
            else:
                corpo_obs = f"\n\nObservação do gestor:\n{dados.gestor_observacao}" if dados.gestor_observacao else ""
                assunto = f"Relatório Retornado — Contrato {info['nr_contrato']}"
                corpo = (
                    f"Olá, {info['fiscal_nome'] or 'Fiscal'},\n\n"
                    f"O gestor {info['gestor_nome']} identificou uma irregularidade no relatório "
                    f"do contrato {info['nr_contrato']} e o retornou para correção.{corpo_obs}\n\n"
                    f"Acesse o sistema para verificar e reenviar.\n\n"
                    f"Sistema SIGESCON"
                )
            await EmailService.send_email(info["fiscal_email"], assunto, corpo)

    async def gerar_pdf(self, nr_contrato: str, dados_form: RelatorioCreateSchema):
        dados_banco = await self.repo.get_dados_contrato_completo(nr_contrato)
        form_dict = dados_form.model_dump()
        contexto = self._build_contexto(dados_banco, form_dict)
        return self._render_docx_to_pdf(contexto)

    async def gerar_pdf_por_contrato_id(self, contrato_id: int, dados_form: RelatorioCreateSchema):
        dados_banco = await self.repo.get_dados_contrato_completo_by_id(contrato_id)
        form_dict = dados_form.model_dump()
        contexto = self._build_contexto(dados_banco, form_dict)
        return self._render_docx_to_pdf(contexto)

    async def gerar_pdf_por_id(self, relatorio_id: int):
        relatorio = await self.repo.get_relatorio_by_id(relatorio_id)
        dados_banco = await self.repo.get_dados_contrato_completo(relatorio['nr_contrato'])
        form_dict = dict(relatorio)
        contexto = self._build_contexto(dados_banco, form_dict)
        return self._render_docx_to_pdf(contexto)