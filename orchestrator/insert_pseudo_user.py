import asyncio
from backend.app.db_utils import AsyncSessionLocal
from backend.app.models.users import User
from sqlalchemy import text

async def insert_pseudo_user():
    users = [
        {
            "username": "testuser1",
            "email": "testuser1@example.com",
            "interests_description": ["transformer models", "deep kernel learning", "federated Learning", "large language models"]
        },
        {
            "username": "testuser2",
            "email": "testuser2@example.com",
            "interests_description": ["graph neural networks", "reinforcement learning", "computer vision"]
        },
        {
            "username": "testuser3",
            "email": "testuser3@example.com",
            "interests_description": ["natural language processing", "speech recognition", "multimodal learning"]
        },
        {
            "username": "testuser4",
            "email": "testuser4@example.com",
            "interests_description": ["meta learning", "few-shot learning", "self-supervised learning"]
        },
        {
            "username": "testuser5",
            "email": "testuser5@example.com",
            "interests_description": ["generative models", "diffusion models", "GANs"]
        }
    ]
    async with AsyncSessionLocal() as db:
        for u in users:
            # 先删除推荐记录
            await db.execute(text("DELETE FROM paper_recommendations WHERE username=:u"), {"u": u["username"]})
            await db.commit()
            print(f"🗑️ 已删除 {u['username']} 的推荐记录")
            # 再删除同名用户，避免唯一性冲突
            await db.execute(text("DELETE FROM users WHERE username=:u"), {"u": u["username"]})
            await db.commit()
            print(f"🗑️ 已删除用户: {u['username']}")
            # 构造伪用户
            user = User(
                username=u["username"],
                email=u["email"],
                interests_description=u["interests_description"]
            )
            db.add(user)
            await db.commit()
            print(f"✅ Pseudo user inserted: {u['username']}")

if __name__ == "__main__":
    asyncio.run(insert_pseudo_user()) 