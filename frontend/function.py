from AIgnite.generation.generator import GeminiBlogGenerator
import httpx
import asyncio
import json
from typing import List, Dict, Any, Optional

# API基础URL
BASE_URL = "http://localhost:8000"

# 异步获取所有用户 - 目前后端没有提供这个API，因此使用模拟数据
async def get_all_users() -> List[Dict[str, Any]]:
    """
    获取所有用户信息
    由于后端目前没有/api/users接口，这里提供两种替代方案:
    1. 使用模拟数据（当前实现）
    2. 直接从数据库查询（需要数据库访问权限，注释提供示例）
    返回: 包含用户ID列表
    """
    # 方案1: 使用模拟数据
    mock_users = [
        {"id": "user1", "username": "researcher1"},
        {"id": "user2", "username": "researcher2"},
        {"id": "user3", "username": "researcher3"},
    ]
    return mock_users
    
    # 方案2: 如果有权限直接访问数据库，可以使用以下代码（需要取消注释）
    """
    # 需要导入必要的模块
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.future import select
    from ..models.user import User
    from ..db.database import DATABASE_URL
    
    try:
        # 创建数据库连接
        engine = create_async_engine(DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # 查询所有活跃用户
            result = await session.execute(select(User).where(User.is_active == True))
            users = result.scalars().all()
            
            # 转换为字典格式
            return [{"id": str(user.id), "username": user.username} for user in users]
    except Exception as e:
        print(f"从数据库获取用户出错: {str(e)}")
        return []
    """

# 异步获取用户兴趣
async def get_user_interest(user_id: str) -> Dict[str, Any]:
    """
    获取指定用户的研究兴趣
    参数:
        user_id: 用户ID
    返回: 
        包含用户兴趣描述和研究领域的字典
    """
    async with httpx.AsyncClient() as client:
        try:
            # 使用/api/users/me接口，通过传递用户名参数
            # 注意：这里假设user_id可以作为username参数使用
            response = await client.get(f"{BASE_URL}/api/users/me", params={"username": user_id})
            
            if response.status_code == 200:
                user_data = response.json()
                # 提取兴趣描述
                interests_list = user_data.get("interests_description", [])
                interest_text = ", ".join(interests_list)
                
                # 获取研究领域名称
                domain_ids = user_data.get("research_domain_ids", [])
                if domain_ids:
                    domains_response = await client.get(f"{BASE_URL}/api/users/research_domains")
                    if domains_response.status_code == 200:
                        domains = domains_response.json()
                        domain_map = {d["id"]: d["name"] for d in domains}
                        domain_names = [domain_map.get(did, "") for did in domain_ids]
                        domain_text = ", ".join(filter(None, domain_names))
                        if domain_text and interest_text:
                            interest_text += ", " + domain_text
                        elif domain_text:
                            interest_text = domain_text
                
                return {"id": user_id, "interests": interest_text}
            else:
                print(f"获取用户兴趣失败: {response.status_code} - {response.text}")
                # 使用模拟数据作为后备
                mock_interests = {
                    "user1": "large language models, deep learning, NLP",
                    "user2": "computer vision, image generation, CV",
                    "user3": "reinforcement learning, multi-agent systems"
                }
                return {"id": user_id, "interests": mock_interests.get(user_id, "")}
        except Exception as e:
            print(f"获取用户兴趣出错: {str(e)}")
            return {"id": user_id, "interests": ""}

# 异步获取与兴趣相似的论文
async def find_similar(interests: str, top_k: int = 5, cutoff: float = 0.0) -> List[Dict[str, Any]]:
    """
    查找与用户兴趣相似的论文
    参数:
        interests: 用户兴趣描述
        top_k: 返回的最大论文数量
        cutoff: 最小相似度阈值
    返回:
        相似论文列表
    """
    async with httpx.AsyncClient() as client:
        try:
            # 目前后端可能没有实现论文推荐API，直接使用现有的论文API
            response = await client.get(f"{BASE_URL}/api/papers", params={"domain_id": None})
            
            if response.status_code == 200:
                papers = response.json()
                # 简单筛选：如果论文标题或摘要包含兴趣关键词，认为相关
                interest_keywords = [k.strip().lower() for k in interests.split(",")]
                filtered_papers = []
                
                for paper in papers:
                    paper_text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
                    relevance = sum(1 for keyword in interest_keywords if keyword and keyword in paper_text)
                    if relevance > 0 or not interest_keywords:
                        filtered_papers.append(paper)
                        if len(filtered_papers) >= top_k:
                            break
                
                return filtered_papers[:top_k]
            else:
                print(f"获取论文失败: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"获取相似论文出错: {str(e)}")
            return []

generator = GeminiBlogGenerator(data_path="../imgs/", output_path="./orchestrator/blogs/")

async def run_batch_generation():
    """异步批量生成论文摘要"""
    users = await get_all_users()
    for user in users:
        user_id = user.get("id")
        user_with_interests = await get_user_interest(user_id)
        interests = user_with_interests["interests"]
        papers = await find_similar(interests, top_k=5, cutoff=0.0)
        if papers:
        blog = generator.generate_digest(papers)
            print(f"Blog for {user_id}:\n{blog}\n")
        else:
            print(f"没有找到与用户 {user_id} 兴趣相关的论文")

def run_dummy_blog_generation(papers):
    """使用提供的论文生成摘要（测试用）"""
    blog = generator.generate_digest(papers)
    return blog

# 如果直接运行此文件
if __name__ == "__main__":
    asyncio.run(run_batch_generation())