from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from typing import AsyncGenerator

def load_config(config_path: str | None = None) -> dict:
    """Load database configuration from YAML file."""
    if not config_path:
        config_path = os.environ.get(
            "PAPERIGNITION_CONFIG",
            str(Path(__file__).resolve().parent.parent / "configs/app_config.yaml"),
        )

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)["USER_DB"]

    required = ["db_user", "db_password", "db_host", "db_port", "db_name"]
    for key in required:
        if key not in config:
            raise ValueError(f"Missing '{key}' in {config_path}")

    return config

config = load_config()
# 从环境变量读取配置（带默认值）
DB_USER = config.get("db_user", "postgres")
DB_PASSWORD = config.get("db_password", "")
DB_HOST = config.get("db_host", "localhost")
DB_PORT = config.get("db_port", "5432")
DB_NAME = config.get("db_name", "paperignition_user")

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