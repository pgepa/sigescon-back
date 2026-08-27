-- Migration: Adicionar coluna data_fim_original na tabela contrato
-- Data: 2026-08-20 (backfill revisado em 2026-08-27)
-- Descrição: Guarda a vigência original do contrato (antes de qualquer aditivo de
--            prazo), usada como base para recalcular contrato.data_fim quando não
--            sobra nenhum aditivo de Prazo/Misto ativo (ex.: o único foi inativado
--            ou excluído). Sem essa coluna, depois que um aditivo de prazo altera
--            data_fim, não há como recuperar a vigência original do contrato.
--
-- Backfill seguro: só preenche data_fim_original = data_fim para contratos que
-- NUNCA tiveram nenhum termo aditivo de Prazo ou Misto (nem ativo, nem inativado)
-- — nesse caso o data_fim atual é garantidamente igual à vigência original, porque
-- nada nunca mudou ele. Contratos que já tiveram algum aditivo de Prazo/Misto
-- (mesmo que hoje inativo/excluído) ficam com data_fim_original = NULL: o valor
-- histórico verdadeiro pode já ter sido sobrescrito por esse aditivo antes dessa
-- coluna existir, e não tem como recuperar com certeza — melhor deixar em branco
-- pra revisão manual do que gravar um valor errado.

ALTER TABLE contrato
    ADD COLUMN IF NOT EXISTS data_fim_original DATE;

UPDATE contrato c
SET data_fim_original = c.data_fim
WHERE c.data_fim_original IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM termo_aditivo ta
      WHERE ta.contrato_id = c.id
        AND ta.tipo IN ('Prazo', 'Misto')
  );

COMMENT ON COLUMN contrato.data_fim_original IS
    'Vigência original do contrato, antes de qualquer aditivo de prazo — usada como base quando não há aditivo de Prazo/Misto ativo. NULL = contrato já teve aditivo de Prazo/Misto antes dessa coluna existir; precisa de revisão manual.';
