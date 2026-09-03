"""Gera o DDL completo do banco usando asyncpg."""
import asyncio
import asyncpg
import os

DB_URL = "postgresql://siscontrol_user:fafsgfsdfsdgdsgdafa@localhost:5432/contratos"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "database", "create_database_complete.sql")

HEADER = """-- =====================================================
-- SCRIPT COMPLETO DE CRIAÇÃO DO BANCO DE DADOS
-- Sistema de Gestão de Contratos (SIGESCON)
-- Gerado automaticamente via dump_schema.py
-- =====================================================

"""

async def main():
    conn = await asyncpg.connect(DB_URL)
    out = [HEADER]

    # Extensões
    exts = await conn.fetch(
        "SELECT extname FROM pg_extension WHERE extname != 'plpgsql' ORDER BY extname"
    )
    if exts:
        out.append("-- Extensões\n")
        for e in exts:
            out.append(f"CREATE EXTENSION IF NOT EXISTS \"{e['extname']}\";\n")
        out.append("\n")

    # Funções usadas em triggers
    funcs = await conn.fetch("""
        SELECT p.proname, pg_get_functiondef(p.oid) AS definition
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.prokind = 'f'
        ORDER BY p.proname
    """)
    if funcs:
        out.append("-- =====================================================\n")
        out.append("-- FUNÇÕES\n")
        out.append("-- =====================================================\n\n")
        for f in funcs:
            out.append(f["definition"].strip() + "\n\n")

    # Sequences standalone (não vinculadas a SERIAL/IDENTITY)
    seqs = await conn.fetch("""
        SELECT s.relname AS seqname,
               seq.seqstart, seq.seqincrement, seq.seqmin, seq.seqmax, seq.seqcache
        FROM pg_class s
        JOIN pg_namespace n ON n.oid = s.relnamespace
        JOIN pg_sequence seq ON seq.seqrelid = s.oid
        LEFT JOIN pg_depend d ON d.objid = s.oid AND d.deptype = 'a'
        WHERE n.nspname = 'public' AND s.relkind = 'S' AND d.objid IS NULL
        ORDER BY s.relname
    """)
    if seqs:
        out.append("-- =====================================================\n")
        out.append("-- SEQUENCES\n")
        out.append("-- =====================================================\n\n")
        for s in seqs:
            out.append(
                f"CREATE SEQUENCE IF NOT EXISTS {s['seqname']}\n"
                f"    START WITH {s['seqstart']}\n"
                f"    INCREMENT BY {s['seqincrement']}\n"
                f"    MINVALUE {s['seqmin']}\n"
                f"    MAXVALUE {s['seqmax']}\n"
                f"    CACHE {s['seqcache']};\n\n"
            )

    # Ordem das tabelas (respeitando FK)
    preferred_order = [
        'perfil', 'usuario', 'usuario_perfil', 'session_context',
        'modalidade', 'status', 'statusrelatorio', 'statuspendencia',
        'contratado', 'contrato', 'arquivo', 'termo_aditivo',
        'pendenciarelatorio', 'relatoriofiscal', 'relatorio_fiscalizacao',
        'configuracao_sistema', 'audit_log', 'notification_log',
        'password_reset_tokens', 'tipo_ocorrencia', 'ocorrencia',
    ]
    all_tables = [r['tablename'] for r in await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )]
    table_order = [t for t in preferred_order if t in all_tables]
    table_order += [t for t in all_tables if t not in table_order]

    out.append("-- =====================================================\n")
    out.append("-- TABELAS\n")
    out.append("-- =====================================================\n\n")

    for table in table_order:
        # Colunas
        cols = await conn.fetch("""
            SELECT
                a.attname AS col,
                pg_catalog.format_type(a.atttypid, a.atttypmod) AS datatype,
                a.attnotnull AS notnull,
                pg_get_expr(ad.adbin, ad.adrelid) AS defaultval,
                a.attidentity AS identity
            FROM pg_catalog.pg_attribute a
            LEFT JOIN pg_catalog.pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
            JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = $1 AND n.nspname = 'public'
              AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attnum
        """, table)

        col_defs = []
        for c in cols:
            line = f"    {c['col']} {c['datatype']}"
            if c['defaultval']:
                line += f" DEFAULT {c['defaultval']}"
            if c['notnull']:
                line += " NOT NULL"
            col_defs.append(line)

        out.append(f"-- =====================================================\n")
        out.append(f"-- TABELA: {table}\n")
        out.append(f"-- =====================================================\n")
        out.append(f"CREATE TABLE IF NOT EXISTS {table} (\n")
        out.append(",\n".join(col_defs) + "\n")
        out.append(");\n\n")

    # Constraints
    constraints = await conn.fetch("""
        SELECT tc.table_name, tc.constraint_name, tc.constraint_type,
               pg_get_constraintdef(pgc.oid, true) AS definition
        FROM information_schema.table_constraints tc
        JOIN pg_constraint pgc ON pgc.conname = tc.constraint_name
        JOIN pg_namespace pns ON pns.oid = pgc.connamespace AND pns.nspname = 'public'
        WHERE tc.table_schema = 'public'
          AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE', 'FOREIGN KEY', 'CHECK')
        ORDER BY tc.constraint_type DESC, tc.table_name, tc.constraint_name
    """)
    if constraints:
        out.append("-- =====================================================\n")
        out.append("-- CONSTRAINTS\n")
        out.append("-- =====================================================\n\n")
        for c in constraints:
            out.append(
                f"ALTER TABLE {c['table_name']} ADD CONSTRAINT {c['constraint_name']} "
                f"{c['definition']};\n"
            )
        out.append("\n")

    # Índices
    indexes = await conn.fetch("""
        SELECT i.relname AS indexname, t.relname AS tablename, ix.indisprimary,
               pg_get_indexdef(i.oid) AS indexdef
        FROM pg_index ix
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_class t ON t.oid = ix.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public' AND NOT ix.indisprimary
          AND NOT EXISTS (
              SELECT 1 FROM pg_constraint c WHERE c.conindid = ix.indexrelid
              AND c.contype IN ('p', 'u', 'f')
          )
        ORDER BY t.relname, i.relname
    """)
    if indexes:
        out.append("-- =====================================================\n")
        out.append("-- ÍNDICES\n")
        out.append("-- =====================================================\n\n")
        for idx in indexes:
            out.append(f"{idx['indexdef']};\n")
        out.append("\n")

    # Views
    views = await conn.fetch(
        "SELECT viewname, definition FROM pg_views WHERE schemaname='public' ORDER BY viewname"
    )
    if views:
        out.append("-- =====================================================\n")
        out.append("-- VIEWS\n")
        out.append("-- =====================================================\n\n")
        for v in views:
            out.append(f"CREATE OR REPLACE VIEW {v['viewname']} AS\n{v['definition'].strip()};\n\n")

    # Triggers
    triggers = await conn.fetch("""
        SELECT t.tgname, c.relname AS tablename,
               pg_get_triggerdef(t.oid, true) AS triggerdef
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND NOT t.tgisinternal
        ORDER BY c.relname, t.tgname
    """)
    if triggers:
        out.append("-- =====================================================\n")
        out.append("-- TRIGGERS\n")
        out.append("-- =====================================================\n\n")
        for t in triggers:
            out.append(f"{t['triggerdef']};\n\n")

    await conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(out)

    total_chars = sum(len(x) for x in out)
    print(f"Schema gerado: {OUTPUT_FILE} ({total_chars} bytes, {len(out)} blocos)")


if __name__ == "__main__":
    asyncio.run(main())
