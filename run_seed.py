import asyncio
import asyncpg
from app.core.config import settings
from app.seeder import seed_data

async def main():
    print("Conectando ao banco de dados...")
    conn = await asyncpg.connect(settings.DATABASE_URL)
    await seed_data(conn)
    await conn.close()
    print("Concluído!")

asyncio.run(main())