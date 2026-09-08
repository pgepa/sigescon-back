"""Criação da tabela tipo_termo_aditivo e chave estrangeira tipo_id em termo_aditivo

Revision ID: 002
Revises: 001
Create Date: 2026-09-08 10:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criação da tabela de referência tipo_termo_aditivo
    op.execute("""
        CREATE TABLE IF NOT EXISTS tipo_termo_aditivo (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(50) NOT NULL UNIQUE,
            descricao TEXT,
            ativo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Inserção dos 4 tipos padrão
    op.execute("""
        INSERT INTO tipo_termo_aditivo (id, nome, descricao) VALUES
            (1, 'Prazo', 'Altera apenas a vigência (nova data fim) do contrato'),
            (2, 'Valor', 'Altera apenas valores financeiros (acréscimos, supressões e valor global)'),
            (3, 'Misto', 'Altera vigência e valor financeiro simultaneamente'),
            (4, 'Outros', 'Alterações administrativas, qualitativas ou de outras cláusulas contratuais')
        ON CONFLICT (id) DO UPDATE SET 
            nome = EXCLUDED.nome,
            descricao = EXCLUDED.descricao;

        SELECT setval('tipo_termo_aditivo_id_seq', (SELECT MAX(id) FROM tipo_termo_aditivo));
    """)

    # 3. Adicionar coluna tipo_id se não existir
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'termo_aditivo' AND column_name = 'tipo_id'
            ) THEN
                ALTER TABLE termo_aditivo ADD COLUMN tipo_id INTEGER;
            END IF;
        END $$;
    """)

    # 4. Migrar dados da coluna legada tipo para tipo_id (se a coluna tipo existir)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'termo_aditivo' AND column_name = 'tipo'
            ) THEN
                UPDATE termo_aditivo
                SET tipo_id = CASE
                    WHEN LOWER(tipo) LIKE '%prazo%' AND LOWER(tipo) NOT LIKE '%misto%' AND LOWER(tipo) NOT LIKE '%valor%' THEN 1
                    WHEN LOWER(tipo) LIKE '%valor%' AND LOWER(tipo) NOT LIKE '%misto%' AND LOWER(tipo) NOT LIKE '%prazo%' THEN 2
                    WHEN LOWER(tipo) LIKE '%misto%' OR (LOWER(tipo) LIKE '%prazo%' AND LOWER(tipo) LIKE '%valor%') THEN 3
                    ELSE 4
                END
                WHERE tipo_id IS NULL;
            ELSE
                UPDATE termo_aditivo SET tipo_id = 4 WHERE tipo_id IS NULL;
            END IF;
        END $$;
    """)

    # 5. Adicionar restrição NOT NULL, FK e índices
    op.execute("""
        ALTER TABLE termo_aditivo ALTER COLUMN tipo_id SET NOT NULL;

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
    """)

    # 6. Remover coluna legada de texto se existir
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'termo_aditivo' AND column_name = 'tipo'
            ) THEN
                ALTER TABLE termo_aditivo DROP COLUMN tipo;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE termo_aditivo ADD COLUMN IF NOT EXISTS tipo VARCHAR(50);
        UPDATE termo_aditivo ta
        SET tipo = tta.nome
        FROM tipo_termo_aditivo tta
        WHERE ta.tipo_id = tta.id;

        ALTER TABLE termo_aditivo DROP CONSTRAINT IF EXISTS fk_termo_aditivo_tipo;
        DROP TABLE IF EXISTS tipo_termo_aditivo;
    """)
