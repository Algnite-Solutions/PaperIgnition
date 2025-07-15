from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from ..index_service.db_utils import load_config as load_index_service_config
from pathlib import Path
import yaml
import os
from typing import AsyncGenerator

def load_config(config_path: str | None = None) -> dict:
    """
    加载 USER_DB 和 INDEX_SERVICE 两部分配置，返回 {'USER_DB': ..., 'INDEX_SERVICE': ...}
    优先从 config_path 或环境变量指定的 app_config.yaml 读取
    """
    if not config_path:
        config_path = os.environ.get(
            "PAPERIGNITION_CONFIG",
            str(Path(__file__).resolve().parent.parent / "configs/app_config.yaml"),
        )
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    if "USER_DB" not in config:
        raise ValueError(f"Missing 'USER_DB' section in {config_path}")
    # 直接用 index_service 的 load_config 解析 INDEX_SERVICE 部分
    index_service_config = load_index_service_config(config_path)
    return {
        "USER_DB": config["USER_DB"],
        "INDEX_SERVICE": index_service_config,
        "APP_SERVICE": config["APP_SERVICE"]
    }

config = load_config()
# 从环境变量读取配置（带默认值）
DB_USER = config.get("db_user", "postgres")
DB_PASSWORD = config.get("db_password", "11111")
DB_HOST = config.get("db_host", "localhost")
DB_PORT = config.get("db_port", "5432")
DB_NAME = config.get("db_name", "paperignition_user")

INDEX_SERVICE_URL = config.get("INDEX_SERVICE", {}).get("host", "http://localhost:8002")

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