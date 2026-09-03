-- Adiciona coluna de status para rascunho/finalizado
ALTER TABLE relatorio_fiscalizacao
  ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'finalizado' NOT NULL;

-- Permite datas nulas para suporte a rascunhos incompletos
ALTER TABLE relatorio_fiscalizacao ALTER COLUMN periodo_inicio DROP NOT NULL;
ALTER TABLE relatorio_fiscalizacao ALTER COLUMN periodo_fim DROP NOT NULL;
ALTER TABLE relatorio_fiscalizacao ALTER COLUMN data_relatorio DROP NOT NULL;
