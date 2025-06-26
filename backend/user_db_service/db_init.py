import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.db.user_db import engine, Base, AsyncSessionLocal
from backend.models.user import ResearchDomain, UserPaperRecommendation

# AI领域初始数据
AI_DOMAINS = [
    {"name": "自然语言处理", "code": "NLP", "description": "自然语言处理技术，包括文本分析、生成、翻译等"},
    {"name": "计算机视觉", "code": "CV", "description": "计算机视觉技术，包括图像识别、目标检测等"},
    {"name": "大型语言模型", "code": "LLM", "description": "大型语言模型和相关研究"},
    {"name": "机器学习", "code": "ML", "description": "通用机器学习方法和技术"},
    {"name": "深度学习", "code": "DL", "description": "深度神经网络和相关技术"},
    {"name": "强化学习", "code": "RL", "description": "强化学习算法和应用"},
    {"name": "生成式AI", "code": "GAI", "description": "生成式AI技术，如GAN、扩散模型等"},
    {"name": "多模态学习", "code": "MM", "description": "多模态学习，结合不同类型的数据"},
    {"name": "语音识别", "code": "ASR", "description": "语音识别和语音处理技术"},
    {"name": "推荐系统", "code": "REC", "description": "推荐系统和个性化技术"},
    {"name": "图神经网络", "code": "GNN", "description": "图神经网络和图数据分析"},
    {"name": "联邦学习", "code": "FL", "description": "联邦学习和分布式AI技术"},
    {"name": "知识图谱", "code": "KG", "description": "知识图谱和知识表示学习"}
]

async def init_db():
    """初始化数据库，创建表和添加初始数据"""
    # 创建所有表
    async with engine.begin() as conn:
        # 删除现有表（如果需要重置）
        # await conn.run_sync(Base.metadata.drop_all)
        
        # 创建表
        await conn.run_sync(Base.metadata.create_all)
    
    # 添加初始数据
    async with AsyncSessionLocal() as session:
        # 检查是否已存在研究领域数据
        result = await session.execute(select(ResearchDomain).limit(1))
        domain_exists = result.scalars().first() is not None
        
        # 如果不存在，添加初始数据
        if not domain_exists:
            for domain_data in AI_DOMAINS:
                domain = ResearchDomain(**domain_data)
                session.add(domain)
            
            await session.commit()
            print("已添加初始研究领域数据")
        
        # 检查是否已存在论文推荐表
        result = await session.execute(select(UserPaperRecommendation).limit(1))
        recommendation_exists = result.scalars().first() is not None
        
        if not recommendation_exists:
            print("已创建论文推荐表")
            
    # 确保PostgreSQL支持数组类型
    async with AsyncSessionLocal() as session:
        try:
            await session.execute("SELECT ARRAY['test1', 'test2']::TEXT[]")
            print("数据库支持数组类型，表创建成功")
        except Exception as e:
            print(f"警告: 数据库可能不支持数组类型，请确保PostgreSQL版本 >= 9.4: {e}")

if __name__ == "__main__":
    # 当直接运行此脚本时，初始化数据库
    asyncio.run(init_db()) 