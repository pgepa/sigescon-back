-- Migration: Novo fluxo de relatório fiscal sem aprovação de admin
-- Data: 2026-08-31
-- Descrição: Adiciona os status 'Rascunho' e 'Salvo' em statusrelatorio.
--            O fiscal agora salva o relatório como Rascunho (editável) e
--            depois finaliza como Salvo — sem etapa de análise/aprovação
--            do Administrador. Os status antigos (Pendente de Análise,
--            Aprovado, Rejeitado com Pendência) são mantidos só para
--            preservar o histórico de relatórios já analisados.

INSERT INTO statusrelatorio (nome, ativo)
SELECT 'Rascunho', TRUE
WHERE NOT EXISTS (SELECT 1 FROM statusrelatorio WHERE nome = 'Rascunho');

INSERT INTO statusrelatorio (nome, ativo)
SELECT 'Salvo', TRUE
WHERE NOT EXISTS (SELECT 1 FROM statusrelatorio WHERE nome = 'Salvo');
