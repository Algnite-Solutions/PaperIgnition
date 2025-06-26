"""
数据库迁移脚本 - 添加 paper_recommendations 表
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import AsyncSessionLocal, engine
from ..models.user import Base, PaperRecommendation

async def create_paper_recommendation_table():
    """
    创建论文推荐表，如果表不存在
    """
    print("开始创建论文推荐表...")
    
    async with AsyncSessionLocal() as session:
        # 检查表是否存在
        result = await session.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'paper_recommendations')"
        ))
        table_exists = result.scalar()
        
        if table_exists:
            print("论文推荐表已存在，跳过创建")
            return
        
        # 创建表
        async with engine.begin() as conn:
            # 只创建 PaperRecommendation 表
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
                sync_conn, 
                tables=[PaperRecommendation.__table__]
            ))
        
        print("论文推荐表创建成功！")

async def main():
    """执行迁移操作"""
    await create_paper_recommendation_table()

if __name__ == "__main__":
    # 当直接运行此脚本时，执行迁移
    asyncio.run(main()) 