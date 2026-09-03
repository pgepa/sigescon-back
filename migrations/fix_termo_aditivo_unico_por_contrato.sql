-- Migration: Garantir no máximo 1 termo aditivo ativo por contrato
-- Data: 2026-05-04
-- Descrição: Soft-delete dos termos aditivos duplicados (ativo=TRUE),
--            preservando apenas o de maior numero_aditivo por contrato.
--            Os registros excluídos permanecem no banco com ativo=FALSE.

-- Visualizar o que será afetado antes de executar
SELECT
    ta.id,
    ta.contrato_id,
    ta.numero_aditivo,
    ta.tipo,
    ta.data_assinatura,
    ta.ativo,
    'SERÁ SOFT-DELETADO' AS acao
FROM termo_aditivo ta
WHERE ta.ativo = TRUE
  AND ta.id NOT IN (
    SELECT DISTINCT ON (contrato_id) id
    FROM termo_aditivo
    WHERE ativo = TRUE
    ORDER BY contrato_id, numero_aditivo DESC
  )
ORDER BY ta.contrato_id, ta.numero_aditivo;

-- Executar o soft-delete dos duplicados
-- (descomente quando confirmar o SELECT acima)
/*
UPDATE termo_aditivo
SET ativo = FALSE,
    updated_at = NOW()
WHERE ativo = TRUE
  AND id NOT IN (
    SELECT DISTINCT ON (contrato_id) id
    FROM termo_aditivo
    WHERE ativo = TRUE
    ORDER BY contrato_id, numero_aditivo DESC
  );
*/
