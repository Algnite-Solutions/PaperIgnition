from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.users import ResearchDomain

from backend.app.db_utils import get_db
from backend.app.routers import auth, users, papers, static

app = FastAPI(title="AIgnite API", description="学术论文推荐微信小程序API")

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