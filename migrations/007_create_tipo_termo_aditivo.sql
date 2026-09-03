-- sigescon-back/migrations/007_create_tipo_termo_aditivo.sql
-- Criação da tabela tipo_termo_aditivo e migração de tipo para tipo_id (FK)

BEGIN;

-- 1. Criação da tabela de referência
CREATE TABLE IF NOT EXISTS tipo_termo_aditivo (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Inserção dos 4 tipos padrão
INSERT INTO tipo_termo_aditivo (id, nome, descricao) VALUES
    (1, 'Prazo', 'Altera apenas a vigência (nova data fim) do contrato'),
    (2, 'Valor', 'Altera apenas valores financeiros (acréscimos, supressões e valor global)'),
    (3, 'Misto', 'Altera vigência e valor financeiro simultaneamente'),
    (4, 'Outros', 'Alterações administrativas, qualitativas ou de outras cláusulas contratuais')
ON CONFLICT (id) DO UPDATE SET 
    nome = EXCLUDED.nome,
    descricao = EXCLUDED.descricao;

SELECT setval('tipo_termo_aditivo_id_seq', (SELECT MAX(id) FROM tipo_termo_aditivo));

-- 3. Adicionar coluna tipo_id na tabela termo_aditivo se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'termo_aditivo' AND column_name = 'tipo_id'
    ) THEN
        ALTER TABLE termo_aditivo ADD COLUMN tipo_id INTEGER;
    END IF;
END $$;

-- 4. Migrar os registros existentes da coluna texto tipo para tipo_id
UPDATE termo_aditivo
SET tipo_id = CASE
    WHEN LOWER(tipo) LIKE '%prazo%' AND LOWER(tipo) NOT LIKE '%misto%' AND LOWER(tipo) NOT LIKE '%valor%' THEN 1
    WHEN LOWER(tipo) LIKE '%valor%' AND LOWER(tipo) NOT LIKE '%misto%' AND LOWER(tipo) NOT LIKE '%prazo%' THEN 2
    WHEN LOWER(tipo) LIKE '%misto%' OR (LOWER(tipo) LIKE '%prazo%' AND LOWER(tipo) LIKE '%valor%') THEN 3
    ELSE 4
END
WHERE tipo_id IS NULL;

-- 5. Adicionar restrição NOT NULL, FK e índices
ALTER TABLE termo_aditivo 
    ALTER COLUMN tipo_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_termo_aditivo_tipo'
    ) THEN
        ALTER TABLE termo_aditivo 
            ADD CONSTRAINT fk_termo_aditivo_tipo 
            FOREIGN KEY (tipo_id) REFERENCES tipo_termo_aditivo(id) ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_termo_aditivo_tipo_id ON termo_aditivo(tipo_id);
CREATE INDEX IF NOT EXISTS idx_termo_aditivo_contrato_id ON termo_aditivo(contrato_id);
CREATE INDEX IF NOT EXISTS idx_termo_aditivo_status ON termo_aditivo(status);

-- 6. Remover coluna legada de texto se existir
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'termo_aditivo' AND column_name = 'tipo'
    ) THEN
        ALTER TABLE termo_aditivo DROP COLUMN tipo;
    END IF;
END $$;

COMMIT;
