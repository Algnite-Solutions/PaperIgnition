"""
数据库迁移脚本 - 用于将 interests_description 字段从 TEXT 转换为 TEXT[]
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import AsyncSessionLocal

async def migrate_interests_to_array():
    """
    将用户表的interests_description字段从TEXT转换为TEXT[]，
    并将已有的字符串数据转换为数组格式
    """
    print("开始迁移 interests_description 字段为数组类型...")
    
    async with AsyncSessionLocal() as session:
        # 1. 创建临时列存储旧数据
        await session.execute(text("ALTER TABLE users ADD COLUMN interests_description_old TEXT"))
        await session.execute(text("UPDATE users SET interests_description_old = interests_description"))
        await session.commit()
        
        # 2. 修改列类型为数组
        await session.execute(text("ALTER TABLE users ALTER COLUMN interests_description TYPE TEXT[] USING NULL"))
        await session.commit()
        
        # 3. 将旧数据转换为数组格式并更新
        # 分割字符串转为数组并去除空白
        await session.execute(text("""
            UPDATE users 
            SET interests_description = 
                ARRAY(
                    SELECT trim(x) 
                    FROM unnest(string_to_array(interests_description_old, ',')) AS x 
                    WHERE trim(x) <> ''
                )
            WHERE interests_description_old IS NOT NULL
        """))
        await session.commit()
        
        # 4. 删除临时列
        await session.execute(text("ALTER TABLE users DROP COLUMN interests_description_old"))
        await session.commit()
        
        print("迁移完成！")

async def main():
    """执行所有迁移操作"""
    await migrate_interests_to_array()

if __name__ == "__main__":
    # 当直接运行此脚本时，执行迁移
    asyncio.run(main()) 