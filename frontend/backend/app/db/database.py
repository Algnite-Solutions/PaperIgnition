from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from typing import AsyncGenerator

# 数据库URL（从环境变量读取或使用默认值）
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:ch20031021@localhost/AIgnite")

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # 设置为True时会打印SQL语句，生产环境可设为False
    future=True
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 声明基类
Base = declarative_base()

# 获取数据库会话的依赖函数
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖函数，用于FastAPI依赖注入
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise 