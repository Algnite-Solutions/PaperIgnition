import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.users import ResearchDomain

from backend.app.db_utils import get_db, DatabaseManager, set_database_manager
from backend.app.routers.papers import file_router
from backend.app.routers import auth, users, papers, static
from backend.app.routers import favorites


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup/shutdown events"""
    # Startup: Initialize database manager

    # Determine config path based on environment
    local_mode = os.getenv("PAPERIGNITION_LOCAL_MODE", "false").lower() == "true"
    config_file = "test_config.yaml" if local_mode else "app_config.yaml"
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", config_file)

    print(f"🚀 Starting FastAPI app with config: {config_path} (LOCAL_MODE: {local_mode})")

    # Create and initialize database manager
    db_manager = DatabaseManager(config_path=config_path)
    await db_manager.initialize()

    # Set global database manager
    set_database_manager(db_manager)

    # Store in app state for additional access if needed
    app.state.db_manager = db_manager

    print("✅ FastAPI app startup complete")

    yield

    # Shutdown: Clean up resources
    print("🛑 FastAPI app shutting down...")
    await db_manager.close()
    print("✅ FastAPI app shutdown complete")


app = FastAPI(
    title="AIgnite API",
    description="学术论文推荐微信小程序API",
    lifespan=lifespan
)

# 配置CORS以允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(papers.router, prefix="/api")
# 文件服务路由不需要/api前缀，直接注册
app.include_router(file_router)
app.include_router(favorites.router, prefix="/api")
app.include_router(static.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "欢迎使用AIgnite学术论文推荐系统API"}

@app.get("/api/domains")
async def get_research_domains(db: AsyncSession = Depends(get_db)):
    """获取所有研究领域"""
    from sqlalchemy import select
    result = await db.execute(select(ResearchDomain))
    domains = result.scalars().all()
    return [{"id": domain.id, "name": domain.name, "code": domain.code} for domain in domains]

@app.get("/api/health")
async def health_check():
    """API健康检查"""
    return {"status": "ok", "message": "服务正常运行"} 