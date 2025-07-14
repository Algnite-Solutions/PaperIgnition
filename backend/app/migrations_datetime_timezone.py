"""
数据库迁移脚本 - 更新datetime字段添加时区支持
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import AsyncSessionLocal, engine

async def update_datetime_columns_timezone():
    """
    更新datetime列以支持时区
    """
    print("开始更新datetime列的时区支持...")
    
    async with AsyncSessionLocal() as session:
        # 更新users表中的datetime列
        await session.execute(text("""
            ALTER TABLE users 
            ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
            ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
        """))
        
        # 更新favorite_papers表中的datetime列
        await session.execute(text("""
            ALTER TABLE favorite_papers 
            ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        """))
        
        # 提交事务
        await session.commit()
        
        print("datetime列时区支持更新成功！")

async def main():
    """执行迁移操作"""
    await update_datetime_columns_timezone()

if __name__ == "__main__":
    # 当直接运行此脚本时，执行迁移
    asyncio.run(main()) 