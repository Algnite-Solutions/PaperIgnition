import pytest
import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.db.user_db import create_test_engine, create_test_session_factory, Base

# 创建测试引擎
test_engine = create_test_engine()
TestingSessionLocal = create_test_session_factory(test_engine)

@pytest.fixture
async def setup_database():
    """
    设置测试数据库
    """
    # 创建所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # 清理数据库
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session():
    """
    创建测试数据库会话
    """
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@pytest.mark.asyncio
async def test_database_connection(setup_database, db_session):
    """
    测试数据库连接
    """
    # 执行简单的SQL查询
    result = await db_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1, "数据库连接测试失败"
    print("✅ 数据库连接测试通过")

@pytest.mark.asyncio
async def test_create_tables(setup_database, db_session):
    """
    测试创建表
    """
    # 检查表是否已创建
    result = await db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
    )
    tables = [row[0] for row in result.all()]
    
    # 验证至少有一些表被创建
    assert len(tables) > 0, "没有表被创建"
    print(f"✅ 表创建测试通过，找到 {len(tables)} 个表")
    for table in tables:
        print(f"  - {table}")

async def run_tests():
    """
    运行所有数据库测试
    """
    print("\n===== 运行数据库测试 =====")
    
    try:
        # 设置数据库
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        # 创建会话
        async with TestingSessionLocal() as session:
            # 测试数据库连接
            await test_database_connection(None, session)
            
            # 测试创建表
            await test_create_tables(None, session)
        
        print("\n✅ 所有数据库测试通过!")
        
    except Exception as e:
        print(f"\n❌ 数据库测试失败: {str(e)}")
    finally:
        # 清理数据库
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

if __name__ == "__main__":
    asyncio.run(run_tests()) 