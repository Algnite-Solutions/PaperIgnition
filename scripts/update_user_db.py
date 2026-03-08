import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.app.db_utils import engine, AsyncSessionLocal


async def update_db():
    """更新UserPaperRecommendation表，添加新的字段"""
    async with engine.begin() as conn:
        # 添加新字段
        try:
            # 添加title字段
            await conn.execute(
                text("ALTER TABLE paper_recommendations ADD COLUMN IF NOT EXISTS title VARCHAR(255);")
            )
            print("添加title字段成功")
            
            # 添加authors字段
            await conn.execute(
                text("ALTER TABLE paper_recommendations ADD COLUMN IF NOT EXISTS authors VARCHAR(255);")
            )
            print("添加authors字段成功")
            
            # 添加abstract字段
            await conn.execute(
                text("ALTER TABLE paper_recommendations ADD COLUMN IF NOT EXISTS abstract TEXT;")
            )
            print("添加abstract字段成功")
            
            # 添加url字段
            await conn.execute(
                text("ALTER TABLE paper_recommendations ADD COLUMN IF NOT EXISTS url VARCHAR(255);")
            )
            print("添加url字段成功")
            
            # 添加blog字段
            await conn.execute(
                text("ALTER TABLE paper_recommendations ADD COLUMN IF NOT EXISTS blog TEXT;")
            )
            print("添加blog字段成功")
            
            print("数据库更新完成！")
            
        except Exception as e:
            print(f"更新数据库时出错: {e}")
            await conn.rollback()
            raise


if __name__ == "__main__":
    # 当直接运行此脚本时，更新数据库
    asyncio.run(update_db())