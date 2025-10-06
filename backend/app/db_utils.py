import yaml
from pathlib import Path
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from ..index_service.db_utils import load_config as load_index_service_config
from typing import AsyncGenerator


def load_config(config_path: str | None = None) -> dict:
    """
    加载 USER_DB 和 INDEX_SERVICE 两部分配置，返回 {'USER_DB': ..., 'INDEX_SERVICE': ...}
    优先从 config_path 或环境变量指定的 app_config.yaml 读取
    """
    LOCAL_MODE = os.getenv("PAPERIGNITION_LOCAL_MODE", "false").lower() == "true"
    if not config_path:
        config = "configs/test_config.yaml" if LOCAL_MODE else "configs/app_config.yaml"
        config_path = os.environ.get(
            "PAPERIGNITION_CONFIG",
            str(Path(__file__).resolve().parent.parent / config),
        )
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    if "USER_DB" not in config:
        raise ValueError(f"Missing 'USER_DB' section in {config_path}")
    if "INDEX_SERVICE" not in config:
        raise ValueError(f"Missing 'INDEX_SERVICE' section in {config_path}")
    return {
        "USER_DB": config["USER_DB"],
        "INDEX_SERVICE": config["INDEX_SERVICE"],
        "APP_SERVICE": config["APP_SERVICE"],
        "OPENAI_SERVICE": config.get("OPENAI_SERVICE", {}),
    }

# 声明基类
Base = declarative_base()


class DatabaseManager:
    """Database manager for handling engine and session lifecycle"""

    def __init__(self, config_path: str = None):
        """Initialize DatabaseManager with configuration"""
        self.config_path = config_path
        self.config = None
        self._engine = None
        self._session_factory = None
        self._initialized = False

    async def initialize(self):
        """Initialize database engine and session factory"""
        if self._initialized:
            return

        # Load configuration
        self.config = load_config(self.config_path)
        user_db_config = self.config.get("USER_DB", {})

        # Extract database connection parameters
        db_user = user_db_config.get("db_user", "postgres")
        db_password = user_db_config.get("db_password", "11111")
        db_host = user_db_config.get("db_host", "localhost")
        db_port = user_db_config.get("db_port", "5432")
        db_name = user_db_config.get("db_name", "paperignition_user")

        # Build database URL
        database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print(f"🔗 DatabaseManager connecting to: {database_url}")

        # Create engine
        self._engine = create_async_engine(
            database_url,
            echo=True,  # Set to False for production
            future=True
        )

        # Create session factory
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        self._initialized = True
        print("✅ DatabaseManager initialized successfully")

    def get_session(self) -> AsyncSession:
        """Get a database session (synchronous - returns session factory call)"""
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        return self._session_factory()

    async def get_session_async(self) -> AsyncSession:
        """Get a database session (async - ensures initialization)"""
        if not self._initialized:
            await self.initialize()
        return self._session_factory()

    async def close(self):
        """Close database connections"""
        if self._engine:
            await self._engine.dispose()
            print("✅ DatabaseManager connections closed")
        self._initialized = False

    @property
    def index_service_url(self) -> str:
        """Get INDEX_SERVICE URL from config"""
        if not self.config:
            return "http://localhost:8002"
        return self.config.get("INDEX_SERVICE", {}).get("host", "http://localhost:8002")


# Global database manager instance (will be set by FastAPI lifespan)
_db_manager: DatabaseManager = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    return _db_manager


def set_database_manager(db_manager: DatabaseManager):
    """Set the global database manager instance"""
    global _db_manager
    _db_manager = db_manager


# 获取数据库会话的依赖函数
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖函数，用于FastAPI依赖注入
    """
    db_manager = get_database_manager()
    if not db_manager:
        raise RuntimeError("DatabaseManager not initialized. Make sure FastAPI app uses lifespan context manager.")

    async with db_manager.get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


from fastapi import Request, HTTPException

# Dependency function for getting INDEX_SERVICE_URL
def get_index_service_url(request: Request) -> str:
    """Get INDEX_SERVICE_URL from app state"""
    if not hasattr(request.app, 'state') or not hasattr(request.app.state, 'db_manager'):
        raise HTTPException(
            status_code=500,
            detail="Application not properly initialized. DatabaseManager not found in app state."
        )

    return request.app.state.db_manager.index_service_url
