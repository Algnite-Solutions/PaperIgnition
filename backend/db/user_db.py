from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from typing import AsyncGenerator, Optional
from backend.configs.config import load_backend_config

# 加载配置
config = load_backend_config()
db_config = config['database']['main']  # 默认使用主数据库配置

# 从配置中获取数据库参数
DB_USER = os.getenv("DB_USER", db_config['user'])
DB_PASSWORD = os.getenv("DB_PASSWORD", db_config['password'])
DB_HOST = os.getenv("DB_HOST", db_config['host'])
DB_PORT = os.getenv("DB_PORT", db_config['port'])
DB_NAME = os.getenv("DB_NAME", db_config['name'])

DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

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

# 为测试提供的函数，使用测试数据库
def get_test_db_url() -> str:
    """
    获取测试数据库URL
    """
    test_config = config['database']['test']
    return (
        f"postgresql+asyncpg://{test_config['user']}:{test_config['password']}"
        f"@{test_config['host']}:{test_config['port']}/{test_config['name']}"
    )

# 创建测试数据库引擎
def create_test_engine():
    """
    创建测试数据库引擎
    """
    return create_async_engine(
        get_test_db_url(),
        echo=True,
        future=True
    )

# 创建测试会话工厂
def create_test_session_factory(engine):
    """
    创建测试会话工厂
    """
    return sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    ) 