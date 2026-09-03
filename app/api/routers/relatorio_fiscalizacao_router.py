from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from asyncpg import Connection
import os

from app.core.database import get_connection
from app.schemas.relatorio_fiscalizacao_schema import RelatorioCreateSchema, RelatorioSalvarSchema
from app.repositories.relatorio_fiscalizacao_repo import RelatorioRepository
from app.services.relatorio_fiscalizacao_service import RelatorioService

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])

def cleanup_files(*file_paths):
    for path in file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


def _serializar_relatorio(r) -> dict:
    keys = set(r.keys())
    def _dt(val):
        return val.isoformat() if val else None
    return {
        "id": r["id"],
        "periodo_inicio": _dt(r["periodo_inicio"]),
        "periodo_fim": _dt(r["periodo_fim"]),
        "data_relatorio": _dt(r["data_relatorio"]),
        "status": r["status"],
        "gestor_observacao": r["gestor_observacao"] if "gestor_observacao" in keys else None,
        "created_at": _dt(r["created_at"]),
        "updated_at": _dt(r["updated_at"]) if "updated_at" in keys else None,
    }


@router.get("/listar/contrato/{contrato_id}")
async def listar_relatorios_por_contrato(
    contrato_id: int,
    db: Connection = Depends(get_connection),
):
    """Lista todos os relatórios do contrato — visão do fiscal (inclui rascunhos)."""
    try:
        repo = RelatorioRepository(db)
        rows = await repo.get_relatorios_por_contrato_id(contrato_id)
        return [_serializar_relatorio(r) for r in rows]
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar relatórios: {str(e)}")


@router.get("/gestor/contrato/{contrato_id}")
async def listar_relatorios_para_gestor(
    contrato_id: int,
    db: Connection = Depends(get_connection),
):
    """Lista relatórios visíveis ao gestor — inclui rascunhos para acompanhamento."""
    try:
        repo = RelatorioRepository(db)
        rows = await repo.get_relatorios_para_gestor(contrato_id)
        return [_serializar_relatorio(r) for r in rows]
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar relatórios para o gestor: {str(e)}")


@router.patch("/{relatorio_id}/finalizar")
async def finalizar_relatorio(
    relatorio_id: int,
    db: Connection = Depends(get_connection),
):
    """Fiscal finaliza o próprio relatório (Rascunho -> Salvo). Sem aprovação de
    gestor: a partir daqui o relatório deixa de ser editável."""
    try:
        repo = RelatorioRepository(db)
        service = RelatorioService(repo)
        result = await service.finalizar_relatorio(relatorio_id)
        return {"id": result["id"], "status": "salvo", "mensagem": "Relatório finalizado com sucesso."}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao finalizar relatório: {str(e)}")


@router.post("/enviar/{relatorio_id}")
async def enviar_relatorio_compat(
    relatorio_id: int,
    db: Connection = Depends(get_connection),
):
    """Alias de compatibilidade da rota antiga (POST /enviar/{id}), que existia
    quando havia aprovação do gestor. Mesma lógica de /finalizar — mantido só
    até o frontend trocar para PATCH /{relatorio_id}/finalizar; remover depois
    que o frontend estiver atualizado."""
    return await finalizar_relatorio(relatorio_id, db)


@router.get("/gerar-pdf-salvo/{relatorio_id}")
async def gerar_pdf_salvo(
    relatorio_id: int,
    background_tasks: BackgroundTasks,
    db: Connection = Depends(get_connection),
):
    """Gera PDF a partir de um relatório já salvo no banco."""
    try:
        repo = RelatorioRepository(db)
        service = RelatorioService(repo)
        pdf_path, docx_path = await service.gerar_pdf_por_id(relatorio_id)
        background_tasks.add_task(cleanup_files, pdf_path, docx_path)
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"Fiscalizacao_{relatorio_id}.pdf",
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")


@router.get("/visualizar/{relatorio_id}")
async def visualizar_relatorio(
    relatorio_id: int,
    background_tasks: BackgroundTasks,
    db: Connection = Depends(get_connection),
):
    """Mesmo PDF de /gerar-pdf-salvo, mas com Content-Disposition: inline —
    o navegador abre no visualizador de PDF embutido em vez de forçar
    download. Front-end: abrir essa URL em nova aba (target=_blank)."""
    try:
        repo = RelatorioRepository(db)
        service = RelatorioService(repo)
        pdf_path, docx_path = await service.gerar_pdf_por_id(relatorio_id)
        background_tasks.add_task(cleanup_files, pdf_path, docx_path)
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"Fiscalizacao_{relatorio_id}.pdf",
            content_disposition_type="inline",
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")


@router.get("/{relatorio_id}/dados")
async def get_dados_relatorio(
    relatorio_id: int,
    db: Connection = Depends(get_connection),
):
    """Retorna os dados completos de um relatório salvo para edição."""
    try:
        repo = RelatorioRepository(db)
        row = await repo.get_relatorio_by_id(relatorio_id)
        dados = dict(row)
        # Serializa datas para ISO string
        for campo in ("periodo_inicio", "periodo_fim", "data_relatorio", "created_at", "updated_at"):
            if dados.get(campo) and hasattr(dados[campo], "isoformat"):
                dados[campo] = dados[campo].isoformat()
        return dados
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar relatório: {str(e)}")


@router.patch("/{relatorio_id}")
async def atualizar_relatorio(
    relatorio_id: int,
    dados_form: RelatorioSalvarSchema,
    db: Connection = Depends(get_connection),
):
    """Atualiza um relatório existente (rascunho ou finalização)."""
    try:
        repo = RelatorioRepository(db)
        await repo.atualizar_relatorio(relatorio_id, dados_form)
        return {"id": relatorio_id, "status": dados_form.status, "mensagem": "Atualizado com sucesso."}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar relatório: {str(e)}")


@router.post("/salvar/{nr_contrato:path}")
async def salvar_relatorio(
    nr_contrato: str,
    dados_form: RelatorioSalvarSchema,
    db: Connection = Depends(get_connection),
):
    """Salva rascunho ou relatório final no banco sem gerar PDF."""
    try:
        repo = RelatorioRepository(db)
        dados_banco = await repo.get_dados_contrato_completo(nr_contrato)
        novo_id = await repo.salvar_relatorio(dados_banco["contrato_id"], dados_form)
        return {"id": novo_id, "status": dados_form.status, "mensagem": "Salvo com sucesso."}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar relatório: {str(e)}")


@router.post("/salvar-contrato/{contrato_id}")
async def salvar_relatorio_por_contrato_id(
    contrato_id: int,
    dados_form: RelatorioSalvarSchema,
    db: Connection = Depends(get_connection),
):
    """Mesmo que /salvar/{nr_contrato}, mas recebe o ID numérico do contrato.

    nr_contrato costuma conter uma barra (ex: "30/2025"), o que alguns proxies
    (Apache em produção) não repassam corretamente mesmo codificada como %2F.
    Usar o ID evita esse problema por completo — prefira esta rota no front-end.
    """
    try:
        repo = RelatorioRepository(db)
        await repo.get_dados_contrato_completo_by_id(contrato_id)
        novo_id = await repo.salvar_relatorio(contrato_id, dados_form)
        return {"id": novo_id, "status": dados_form.status, "mensagem": "Salvo com sucesso."}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar relatório: {str(e)}")


@router.post("/gerar-pdf/{nr_contrato:path}")
async def gerar_relatorio_pdf(
    nr_contrato: str,
    dados_form: RelatorioCreateSchema,
    background_tasks: BackgroundTasks,
    db: Connection = Depends(get_connection),
):
    """Gera o PDF do relatório sem salvar no banco."""
    try:
        repo = RelatorioRepository(db)
        service = RelatorioService(repo)

        pdf_path, docx_path = await service.gerar_pdf(nr_contrato, dados_form)
        background_tasks.add_task(cleanup_files, pdf_path, docx_path)

        nome_seguro = nr_contrato.replace("/", "-")
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"Fiscalizacao_{nome_seguro}.pdf",
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar o PDF: {str(e)}")


@router.post("/gerar-pdf-contrato/{contrato_id}")
async def gerar_relatorio_pdf_por_contrato_id(
    contrato_id: int,
    dados_form: RelatorioCreateSchema,
    background_tasks: BackgroundTasks,
    db: Connection = Depends(get_connection),
):
    """Mesmo que /gerar-pdf/{nr_contrato}, mas recebe o ID numérico do contrato
    (evita o problema de barra em nr_contrato via proxy/Apache — prefira esta rota)."""
    try:
        repo = RelatorioRepository(db)
        service = RelatorioService(repo)

        pdf_path, docx_path = await service.gerar_pdf_por_contrato_id(contrato_id, dados_form)
        background_tasks.add_task(cleanup_files, pdf_path, docx_path)

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"Fiscalizacao_Contrato_{contrato_id}.pdf",
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar o PDF: {str(e)}")