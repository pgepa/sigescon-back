-- Migration: Adicionar colunas faltantes na tabela termo_aditivo
--            e tipo_vinculo na tabela arquivo
-- Data: 2026-04-23
-- Descrição: Adiciona pae, valor_supressao, observacoes, arquivo_id e updated_at
--            em termo_aditivo; adiciona tipo_vinculo em arquivo para identificar
--            se o arquivo pertence a um contrato, tcd ermo aditivo ou relatório.

-- 1. Colunas faltantes em termo_aditivo
ALTER TABLE termo_aditivo
    ADD COLUMN IF NOT EXISTS pae TEXT,
    ADD COLUMN IF NOT EXISTS valor_supressao NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS observacoes TEXT,
    ADD COLUMN IF NOT EXISTS arquivo_id INTEGER REFERENCES arquivo(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

COMMENT ON COLUMN termo_aditivo.pae IS 'Número do PAE relacionado ao aditivo';
COMMENT ON COLUMN termo_aditivo.valor_supressao IS 'Valor de supressão do aditivo';
COMMENT ON COLUMN termo_aditivo.observacoes IS 'Observações adicionais do aditivo';
COMMENT ON COLUMN termo_aditivo.arquivo_id IS 'Arquivo anexado ao termo aditivo';
COMMENT ON COLUMN termo_aditivo.updated_at IS 'Data da última atualização';

-- 2. Identificação do tipo de vínculo na tabela arquivo
ALTER TABLE arquivo
    ADD COLUMN IF NOT EXISTS tipo_vinculo VARCHAR(20) DEFAULT 'contrato'
        CHECK (tipo_vinculo IN ('contrato', 'termo_aditivo', 'relatorio'));

-- Registros já existentes são arquivos de contrato
UPDATE arquivo SET tipo_vinculo = 'contrato' WHERE tipo_vinculo IS NULL;

COMMENT ON COLUMN arquivo.tipo_vinculo IS 'Origem do arquivo: contrato, termo_aditivo ou relatorio';
