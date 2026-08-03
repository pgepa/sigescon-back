-- Migration: Adicionar coluna data_inicio na tabela termo_aditivo
-- Data: 2026-07-30
-- Descrição: Adiciona a data de início da nova vigência gerada pelo aditivo,
--            complementando nova_data_fim (data de término).

ALTER TABLE termo_aditivo
    ADD COLUMN IF NOT EXISTS data_inicio DATE;

COMMENT ON COLUMN termo_aditivo.data_inicio IS 'Data de início da nova vigência do aditivo';
