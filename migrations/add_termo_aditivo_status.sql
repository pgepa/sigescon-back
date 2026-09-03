-- Migration: Adicionar coluna status na tabela termo_aditivo
-- Data: 2026-08-26
-- Descrição: Guarda o status calculado do termo aditivo ('Ativo', 'Vencido',
--            'Inativo') como coluna própria, em vez de ser recalculado toda vez
--            na consulta. Mesma lógica que já existia calculada na hora:
--              ativo = FALSE                                   -> 'Inativo'
--              ativo = TRUE  E nova_data_fim < hoje             -> 'Vencido'
--              ativo = TRUE  E (nova_data_fim >= hoje ou nulo)  -> 'Ativo'
--
-- Mantida em sincronia em dois pontos: na hora (criar/editar/inativar um termo
-- aditivo) e por um job diário à 00:02 (cobre o caso de um aditivo vencer só
-- pela passagem do tempo, sem ninguém editar nada).

ALTER TABLE termo_aditivo
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Ativo';

UPDATE termo_aditivo
SET status = CASE
    WHEN ativo = FALSE THEN 'Inativo'
    WHEN nova_data_fim IS NOT NULL AND nova_data_fim < CURRENT_DATE THEN 'Vencido'
    ELSE 'Ativo'
END
WHERE status IS NULL OR status <> CASE
    WHEN ativo = FALSE THEN 'Inativo'
    WHEN nova_data_fim IS NOT NULL AND nova_data_fim < CURRENT_DATE THEN 'Vencido'
    ELSE 'Ativo'
END;

COMMENT ON COLUMN termo_aditivo.status IS
    'Status calculado do termo aditivo: Ativo, Vencido ou Inativo. Sincronizado ao criar/editar/inativar e por job diário (00:02).';
