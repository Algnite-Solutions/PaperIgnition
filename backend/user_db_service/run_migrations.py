import asyncio

# from app.db.migrations import migrate_interests_to_array
from backend.app.db.migrations_paper_recommendation import create_paper_recommendation_table
from backend.app.db.migrations_datetime_timezone import update_datetime_columns_timezone

async def run_all_migrations():
    """按顺序运行所有迁移脚本"""
    print("开始执行数据库迁移...")
    
    # 1. 迁移用户兴趣字段为数组类型（如果需要）
    # await migrate_interests_to_array()
    
    # 2. 创建论文推荐表
    await create_paper_recommendation_table()
    
    # 3. 更新datetime列的时区支持
    await update_datetime_columns_timezone()
    
    print("所有迁移完成！")

if __name__ == "__main__":
    # 当直接运行此脚本时，执行所有迁移
    asyncio.run(run_all_migrations()) 