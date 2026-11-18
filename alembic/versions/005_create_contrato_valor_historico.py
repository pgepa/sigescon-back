"""Cria tabela contrato_valor_historico com trigger de registro automático

Revision ID: 005
Revises: 004
Create Date: 2026-11-18 12:00:00.000000

Toda mudança em contrato.valor_global ou contrato.valor_global_original é
registrada automaticamente por trigger — vale para qualquer caminho (scheduler,
edição pela tela, termo aditivo, UPDATE manual no banco).

A origem é deduzida pelo trigger:
    CRIACAO             -> INSERT do contrato
    ALTERACAO_ORIGINAL  -> valor_global_original mudou (edição do valor do contrato)
    RECALCULO_ADITIVOS  -> só valor_global mudou (aditivo criado/editado/inativado)
Pode ser sobrescrita na sessão/transação com:
    SELECT set_config('app.origem_valor', 'CORRECAO_MANUAL', true);
    SELECT set_config('app.observacao_valor', 'texto livre', true);
"""
from typing import Sequence, Union
from alembic import op


revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A coluna é criada de fato na 006; aqui só garante que exista porque o
    # trigger a referencia.
    op.execute("""
        ALTER TABLE contrato
            ADD COLUMN IF NOT EXISTS valor_global_original NUMERIC(15, 2);
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS contrato_valor_historico (
            id                 SERIAL PRIMARY KEY,
            contrato_id        INTEGER NOT NULL REFERENCES contrato(id),
            valor_anterior     NUMERIC(15, 2),
            valor_novo         NUMERIC(15, 2),
            original_anterior  NUMERIC(15, 2),
            original_novo      NUMERIC(15, 2),
            soma_acrescimo     NUMERIC(15, 2),
            soma_supressao     NUMERIC(15, 2),
            origem             VARCHAR(40) NOT NULL,
            observacao         TEXT,
            usuario_banco      VARCHAR(100) NOT NULL DEFAULT current_user,
            data_hora          TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_contrato_valor_historico_contrato
            ON contrato_valor_historico (contrato_id, data_hora);
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_contrato_valor_historico()
        RETURNS trigger AS $$
        DECLARE
            v_origem  TEXT := NULLIF(current_setting('app.origem_valor', true), '');
            v_obs     TEXT := NULLIF(current_setting('app.observacao_valor', true), '');
            v_acr     NUMERIC(15, 2);
            v_sup     NUMERIC(15, 2);
        BEGIN
            IF TG_OP = 'UPDATE'
               AND NEW.valor_global IS NOT DISTINCT FROM OLD.valor_global
               AND NEW.valor_global_original IS NOT DISTINCT FROM OLD.valor_global_original THEN
                RETURN NEW;
            END IF;

            IF TG_OP = 'INSERT' AND NEW.valor_global IS NULL AND NEW.valor_global_original IS NULL THEN
                RETURN NEW;
            END IF;

            SELECT COALESCE(SUM(valor_acrescimo), 0), COALESCE(SUM(valor_supressao), 0)
              INTO v_acr, v_sup
              FROM termo_aditivo
             WHERE contrato_id = NEW.id AND ativo = TRUE AND tipo_id IN (2, 3);

            IF v_origem IS NULL THEN
                v_origem := CASE
                    WHEN TG_OP = 'INSERT' THEN 'CRIACAO'
                    WHEN NEW.valor_global_original IS DISTINCT FROM OLD.valor_global_original THEN 'ALTERACAO_ORIGINAL'
                    ELSE 'RECALCULO_ADITIVOS'
                END;
            END IF;

            INSERT INTO contrato_valor_historico (
                contrato_id, valor_anterior, valor_novo,
                original_anterior, original_novo,
                soma_acrescimo, soma_supressao, origem, observacao
            ) VALUES (
                NEW.id,
                CASE WHEN TG_OP = 'UPDATE' THEN OLD.valor_global END,
                NEW.valor_global,
                CASE WHEN TG_OP = 'UPDATE' THEN OLD.valor_global_original END,
                NEW.valor_global_original,
                v_acr, v_sup, v_origem, v_obs
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_contrato_valor_historico ON contrato;")
    op.execute("""
        CREATE TRIGGER trg_contrato_valor_historico
        AFTER INSERT OR UPDATE OF valor_global, valor_global_original ON contrato
        FOR EACH ROW EXECUTE FUNCTION fn_contrato_valor_historico();
    """)

    # Fotografia do estado atual de todos os contratos (inclusive os valores
    # ainda errados), para que nada se perca antes das correções.
    op.execute("""
        INSERT INTO contrato_valor_historico (
            contrato_id, valor_anterior, valor_novo, original_anterior, original_novo,
            soma_acrescimo, soma_supressao, origem, observacao
        )
        SELECT
            c.id, NULL, c.valor_global, NULL, c.valor_global_original,
            COALESCE(t.acr, 0), COALESCE(t.sup, 0),
            'SNAPSHOT_INICIAL',
            'Estado do contrato no momento da criação do histórico'
        FROM contrato c
        LEFT JOIN (
            SELECT contrato_id, SUM(valor_acrescimo) AS acr, SUM(valor_supressao) AS sup
            FROM termo_aditivo
            WHERE ativo = TRUE AND tipo_id IN (2, 3)
            GROUP BY contrato_id
        ) t ON t.contrato_id = c.id;
    """)

    op.execute("""
        COMMENT ON TABLE contrato_valor_historico IS
            'Histórico de alterações de contrato.valor_global e valor_global_original, gravado pelo trigger trg_contrato_valor_historico.';
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_contrato_valor_historico ON contrato;")
    op.execute("DROP FUNCTION IF EXISTS fn_contrato_valor_historico();")
    op.execute("DROP TABLE IF EXISTS contrato_valor_historico;")
    op.execute("ALTER TABLE contrato DROP COLUMN IF EXISTS valor_global_original;")
