import asyncio
from app.db.migrations import main as run_migrations

if __name__ == "__main__":
    asyncio.run(run_migrations())
    print("数据库迁移完成!") 