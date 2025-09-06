import asyncio
import aiosqlite

async def check_tables():
    async with aiosqlite.connect('/tmp/test_check_new.db') as db:
        cursor = await db.execute('SELECT name FROM sqlite_master WHERE type="table" AND name IN ("code_repositories", "agent_sessions") ORDER BY name')
        tables = await cursor.fetchall()
        print('Required tables:', [t[0] for t in tables])
        return tables

if __name__ == '__main__':
    asyncio.run(check_tables())