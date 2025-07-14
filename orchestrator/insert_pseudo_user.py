import asyncio
from backend.app.db_utils import AsyncSessionLocal
from backend.app.models.users import User
from sqlalchemy import text

async def insert_pseudo_user():
    async with AsyncSessionLocal() as db:
        # 删除同名用户，避免唯一性冲突
        await db.execute(text("DELETE FROM users WHERE username=:u"), {"u": "testuser1"})
        await db.commit()
        # 构造伪用户
        user = User(
            username="testuser1",
            email="testuser1@example.com",
            interests_description=["transformer models","deep kernel learning","federated Learning","large language models"]
        )
        db.add(user)
        await db.commit()
        print("✅ Pseudo user inserted.")

if __name__ == "__main__":
    asyncio.run(insert_pseudo_user()) 