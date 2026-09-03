-- Migração: Workflow de envio do relatório de fiscalização
-- Fiscal salva rascunho → envia para gestor → gestor aprova ou retorna

ALTER TABLE relatorio_fiscalizacao
  ADD COLUMN IF NOT EXISTS gestor_observacao TEXT;

ALTER TABLE relatorio_fiscalizacao
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

-- Atualiza o default de status para rascunho (relatórios novos começam como rascunho)
ALTER TABLE relatorio_fiscalizacao
  ALTER COLUMN status SET DEFAULT 'rascunho';

-- Converte registros antigos 'finalizado' para 'enviado' (já eram visíveis ao gestor)
UPDATE relatorio_fiscalizacao
  SET status = 'enviado'
  WHERE status = 'finalizado';
