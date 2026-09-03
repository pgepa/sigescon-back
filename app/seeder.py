# app/seeder.py
import asyncpg
from app.core.config import settings
from app.core.security import get_password_hash

# --- DADOS ESSENCIAIS A SEREM INSERIDOS ---
PERFIS = ['Administrador', 'Gestor', 'Fiscal']
MODALIDADES = [
    'Pregão', 'Concorrência', 'Concurso', 'Leilão', 'Diálogo Competitivo',
    'Dispensa de Licitação', 'Inexigibilidade de Licitação', 'Credenciamento'
]
STATUS_CONTRATO = ['Vigente', 'Encerrado', 'Rescindido', 'Suspenso', 'Aguardando Publicação']
STATUS_RELATORIO = ['Rascunho', 'Salvo', 'Pendente de Análise', 'Aprovado', 'Rejeitado com Pendência']
STATUS_PENDENCIA = ['Pendente', 'Concluída', 'Cancelada']


async def seed_data(conn: asyncpg.Connection):
    """
    Popula o banco com dados essenciais para a aplicação, se as tabelas estiverem vazias.
    """
    print("Iniciando o processo de seed do banco de dados...")

    # --- Função auxiliar para popular tabelas de lookup ---
    async def seed_table(table_name: str, data_list: list):
        # Verifica se a tabela já tem dados para evitar inserções duplicadas
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
        if count == 0:
            print(f"Populando tabela '{table_name}'...")
            # Prepara uma única query de inserção para todos os itens
            query = f"INSERT INTO {table_name} (nome) VALUES ($1)"
            await conn.executemany(query, [(item,) for item in data_list])
        else:
            print(f"Tabela '{table_name}' já populada. Pulando.")

    # --- Popula todas as tabelas de lookup ---
    await seed_table('perfil', PERFIS)
    await seed_table('modalidade', MODALIDADES)
    await seed_table('status', STATUS_CONTRATO)
    await seed_table('statusrelatorio', STATUS_RELATORIO)
    await seed_table('statuspendencia', STATUS_PENDENCIA)


    # --- Garante a existência do usuário Administrador ---
    admin_email = settings.ADMIN_EMAIL
    if admin_email:
        admin_user = await conn.fetchrow("SELECT id FROM usuario WHERE email = $1", admin_email)

        if not admin_user:
            print(f"Criando usuário Administrador ({admin_email})...")
            admin_pass_hash = get_password_hash(settings.ADMIN_PASSWORD)
            perfil_admin_id = await conn.fetchval("SELECT id FROM perfil WHERE nome = 'Administrador'")

            if perfil_admin_id:
                # Cria o usuário sem perfil_id (campo legacy)
                admin_user_id = await conn.fetchval(
                    """
                    INSERT INTO usuario (nome, email, cpf, senha_hash)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    """,
                    'Administrador do Sistema', admin_email, '00000000000', admin_pass_hash
                )

                # Associa o perfil através da tabela usuario_perfil
                await conn.execute(
                    """
                    INSERT INTO usuario_perfil (usuario_id, perfil_id, concedido_por_usuario_id, ativo)
                    VALUES ($1, $2, $1, TRUE)
                    """,
                    admin_user_id, perfil_admin_id
                )

                print(f"- Usuário Administrador '{admin_email}' criado com sucesso.")
                print(f"- Perfil 'Administrador' concedido com sucesso.")
            else:
                print("ERRO: Perfil 'Administrador' não encontrado. Não foi possível criar o usuário admin.")
        else:
            # Verifica se o admin já tem o perfil na nova tabela
            admin_profile = await conn.fetchrow(
                """
                SELECT up.id FROM usuario_perfil up
                JOIN perfil p ON up.perfil_id = p.id
                WHERE up.usuario_id = $1 AND p.nome = 'Administrador' AND up.ativo = TRUE
                """,
                admin_user['id']
            )

            if not admin_profile:
                print(f"Concedendo perfil 'Administrador' para usuário existente ({admin_email})...")
                perfil_admin_id = await conn.fetchval("SELECT id FROM perfil WHERE nome = 'Administrador'")

                if perfil_admin_id:
                    await conn.execute(
                        """
                        INSERT INTO usuario_perfil (usuario_id, perfil_id, concedido_por_usuario_id, ativo)
                        VALUES ($1, $2, $1, TRUE)
                        """,
                        admin_user['id'], perfil_admin_id
                    )
                    print(f"- Perfil 'Administrador' concedido com sucesso.")
                else:
                    print("ERRO: Perfil 'Administrador' não encontrado.")
            else:
                print(f"Usuário Administrador ({admin_email}) já existe e tem perfil ativo. Pulando.")
    
    print("Seed do banco de dados concluído.")