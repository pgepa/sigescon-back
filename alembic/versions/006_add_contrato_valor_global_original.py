"""Adiciona valor_global_original e corrige valor_global acumulado por aditivos

Revision ID: 006
Revises: 005
Create Date: 2026-11-18 12:10:00.000000

contrato.valor_global passa a ser sempre recalculado como
    valor_global = valor_global_original + SUM(acréscimos) - SUM(supressões)
considerando apenas termos aditivos de Valor/Misto ativos.

Bug corrigido: a sincronização usava COALESCE(valor_anual, valor_global) como
base. Com valor_anual NULL, a base era o próprio valor_global já ajustado, e cada
execução (scheduler diário, edição do contrato, edição de aditivo) reaplicava os
aditivos. Ex.: 22/2025 (original R$ 39.702,00, supressão de R$ 9.552,00) chegou a
R$ -1.354.890,00.

Backfill seguro (mesmo critério de data_fim_original): só preenche
valor_global_original = valor_global para contratos que NUNCA tiveram aditivo de
Valor/Misto. Os demais ficam NULL para revisão manual — enquanto NULL, a
sincronização não mexe no valor_global deles.

As alterações ficam registradas em contrato_valor_historico (revision 005).
"""
from typing import Sequence, Union
from alembic import op


revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Valores originais conferidos no contrato assinado. (nr_contrato, valor)
# Aplicados só a contratos ativos que tenham aditivo de Valor/Misto OU que ainda
# estejam sem valor_global_original — assim um homônimo sem aditivo (ex.: o outro
# 22/2025, já com original preenchido) e duplicados inativados não são afetados.
# ACT 001/2025 não tem valor.
VALORES_ORIGINAIS_CONFERIDOS = [
    ('22/2025', '39702.00'),
    ('34/2024', '13760.00'),
    ('28/2024', '3916940.00'),
    ('27/2024', '75000.00'),
    ('28/2023', '6720.00'),
    ('42/2023', '435047.76'),
    ('TED 01/2024', '3925233.58'),
    ('11/2025', '68448.00'),
    ('17/2025', '90000.48'),
    ('2024.250101NE000142', '3970.00'),
    ('026/2022', '107971.05'),
]

# Aditivos financeiros desativados indevidamente que devem voltar a valer.
# (nr_contrato, numero_aditivo, valor_acrescimo, valor_supressao) — os valores
# servem de conferência: só reativa se o aditivo bater exatamente.
ADITIVOS_A_REATIVAR = [
    ('TED 01/2024', 1, 'NULL', '1206297.34'),
]


def _origem(origem: str, observacao: str) -> None:
    op.execute(f"SELECT set_config('app.origem_valor', '{origem}', true);")
    op.execute(f"SELECT set_config('app.observacao_valor', '{observacao}', true);")


def upgrade() -> None:
    op.execute("""
        ALTER TABLE contrato
            ADD COLUMN IF NOT EXISTS valor_global_original NUMERIC(15, 2);
    """)

    _origem('CARGA_ORIGINAL', 'Contrato sem aditivo financeiro - valor atual é o original')
    op.execute("""
        UPDATE contrato c
        SET valor_global_original = c.valor_global
        WHERE c.valor_global_original IS NULL
          AND c.valor_global IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM termo_aditivo ta
              WHERE ta.contrato_id = c.id AND ta.tipo_id IN (2, 3)
          );
    """)

    _origem('CORRECAO_MANUAL', 'Valor original conferido no contrato assinado')
    for nr_contrato, valor in VALORES_ORIGINAIS_CONFERIDOS:
        op.execute(f"""
            UPDATE contrato c
            SET valor_global_original = {valor}
            WHERE c.nr_contrato = '{nr_contrato}'
              AND c.ativo = TRUE
              AND c.valor_global_original IS DISTINCT FROM {valor}
              AND (c.valor_global_original IS NULL OR EXISTS (
                  SELECT 1 FROM termo_aditivo ta
                  WHERE ta.contrato_id = c.id AND ta.tipo_id IN (2, 3)
              ));
        """)

    # Aditivos financeiros desativados indevidamente (em lote, sem registro no
    # audit_log) que precisam voltar a contar no valor global.
    # (nr_contrato, numero_aditivo, valor_acrescimo, valor_supressao)
    for nr_contrato, numero, acrescimo, supressao in ADITIVOS_A_REATIVAR:
        op.execute(f"""
            UPDATE termo_aditivo ta
            SET ativo = TRUE,
                status = CASE WHEN c.data_fim < CURRENT_DATE THEN 'Vencido' ELSE 'Incorporado' END,
                updated_at = NOW()
            FROM contrato c
            WHERE c.id = ta.contrato_id
              AND c.ativo = TRUE
              AND c.nr_contrato = '{nr_contrato}'
              AND ta.numero_aditivo = {numero}
              AND ta.tipo_id IN (2, 3)
              AND ta.valor_acrescimo IS NOT DISTINCT FROM {acrescimo}
              AND ta.valor_supressao IS NOT DISTINCT FROM {supressao}
              AND ta.ativo = FALSE;
        """)

    _origem('CORRECAO_BUG_SOMA_REPETIDA', 'Recalculo = original + acrescimos - supressoes (aditivos ativos)')
    op.execute("""
        WITH totais AS (
            SELECT
                contrato_id,
                COALESCE(SUM(valor_acrescimo), 0) AS soma_acrescimo,
                COALESCE(SUM(valor_supressao), 0) AS soma_supressao
            FROM termo_aditivo
            WHERE ativo = TRUE AND tipo_id IN (2, 3)
            GROUP BY contrato_id
        ),
        calculo AS (
            SELECT
                c.id,
                c.valor_global_original
                    + COALESCE(t.soma_acrescimo, 0)
                    - COALESCE(t.soma_supressao, 0) AS novo_valor
            FROM contrato c
            LEFT JOIN totais t ON t.contrato_id = c.id
            WHERE c.valor_global_original IS NOT NULL
        )
        UPDATE contrato c
        SET valor_global = calc.novo_valor,
            updated_at = NOW()
        FROM calculo calc
        WHERE c.id = calc.id
          AND c.valor_global IS DISTINCT FROM calc.novo_valor;
    """)

    _origem('', '')

    op.execute("""
        COMMENT ON COLUMN contrato.valor_global_original IS
            'Valor global original do contrato, antes de aditivos de Valor/Misto. valor_global = valor_global_original + acrescimos - supressoes (aditivos ativos). NULL = ja tinha aditivo financeiro antes desta coluna existir; precisa de revisao manual.';
    """)


def downgrade() -> None:
    # A coluna é referenciada pelo trigger da 005; ela é removida no downgrade da 005.
    pass
