#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加博客反馈字段
为 paper_recommendations 表添加 blog_liked 和 blog_feedback_date 字段
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# 你需要根据实际配置修改数据库URL
DATABASE_URL = "postgresql+asyncpg://postgres:11111@localhost:5432/paperignition"

async def migrate_database():
    """执行数据库迁移"""
    print("🔧 开始数据库迁移...")
    
    engine = create_async_engine(DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            # 检查字段是否已存在
            print("📋 检查字段是否已存在...")
            
            check_blog_liked = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'paper_recommendations' 
                AND column_name = 'blog_liked'
            """)
            
            result = await conn.execute(check_blog_liked)
            blog_liked_exists = result.fetchone() is not None
            
            check_blog_feedback_date = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'paper_recommendations' 
                AND column_name = 'blog_feedback_date'
            """)
            
            result = await conn.execute(check_blog_feedback_date)
            blog_feedback_date_exists = result.fetchone() is not None
            
            # 添加 blog_liked 字段
            if not blog_liked_exists:
                print("➕ 添加 blog_liked 字段...")
                await conn.execute(text("""
                    ALTER TABLE paper_recommendations 
                    ADD COLUMN blog_liked BOOLEAN
                """))
                print("✅ blog_liked 字段添加成功")
            else:
                print("⏩ blog_liked 字段已存在，跳过")
            
            # 添加 blog_feedback_date 字段
            if not blog_feedback_date_exists:
                print("➕ 添加 blog_feedback_date 字段...")
                await conn.execute(text("""
                    ALTER TABLE paper_recommendations 
                    ADD COLUMN blog_feedback_date TIMESTAMP WITH TIME ZONE
                """))
                print("✅ blog_feedback_date 字段添加成功")
            else:
                print("⏩ blog_feedback_date 字段已存在，跳过")
        
        print("🎉 数据库迁移完成！")
        
        # 验证字段
        print("🔍 验证字段...")
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'paper_recommendations' 
                AND column_name IN ('blog_liked', 'blog_feedback_date')
                ORDER BY column_name
            """))
            
            columns = result.fetchall()
            for col in columns:
                print(f"📋 {col[0]}: {col[1]} (nullable: {col[2]})")
                
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

async def main():
    """主函数"""
    print("=" * 50)
    print("📊 PaperIgnition 数据库迁移工具")
    print("添加博客反馈相关字段")
    print("=" * 50)
    
    # 确认操作
    response = input("是否继续执行迁移？(y/N): ")
    if response.lower() != 'y':
        print("❌ 迁移已取消")
        return
    
    await migrate_database()

if __name__ == "__main__":
    asyncio.run(main()) 