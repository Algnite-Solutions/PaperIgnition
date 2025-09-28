from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
import asyncio
import logging
from sqlalchemy import and_
import requests
import yaml
from pathlib import Path
import sys
import os
# 从utils目录导入index_utils
from ..utils.index_utils import get_openai_client, translate_text, search_papers_via_api

# 加载配置文件
def load_config():
    """加载应用配置文件"""
    config_path = Path(__file__).parent.parent.parent / "configs/app_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

# 设置日志
logger = logging.getLogger(__name__)

from ..models.users import User, ResearchDomain, user_domain_association, UserPaperRecommendation
from ..db_utils import get_db, INDEX_SERVICE_URL

from ..auth.schemas import UserOut, UserProfileUpdate
from ..auth.utils import get_current_user

# 请求模型
class UserInterestUpdate(BaseModel):
    research_domain_ids: List[int]
    interests_description: Optional[List[str]] = None

# Response model for research domains (assuming a simple list of id and name)
class ResearchDomainOut(BaseModel):
    id: int
    name: str

class RewriteInterestUpdate(BaseModel):
    username: str
    rewrite_interest: str

router = APIRouter(prefix="/users", tags=["users"])

def save_recommendations(username, papers, backend_api_url):
    """保存推荐论文到数据库"""
    for paper in papers:
        data = {
            "paper_id": paper.get("doc_id"),
            "title": paper.get("title", ""),
            "authors": paper.get("authors", ""),
            "abstract": paper.get("abstract", ""),
            "url": paper.get("url", ""),
            "content": paper.get("content", ""),
            "blog": paper.get("blog", ""),
            "recommendation_reason": paper.get("recommendation_reason", ""),
            "relevance_score": paper.get("score", 0.0)
        }
        try:
            resp = requests.post(
                f"{backend_api_url}/api/papers/recommend",
                params={"username": username},
                json=data,
                timeout=30.0
            )
            if resp.status_code == 201:
                logger.info(f"✅ 推荐写入成功: {paper.get('doc_id')}")
            else:
                logger.error(f"❌ 推荐写入失败: {paper.get('doc_id')}，原因: {resp.text}")
        except Exception as e:
            logger.error(f"❌ 推荐写入异常: {paper.get('doc_id')}，错误: {e}")

@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取当前用户信息（现在使用JWT验证）"""
    # 获取用户的研究领域ID
    research_domain_ids = []
    if current_user.research_domains:
        for domain in current_user.research_domains:
            research_domain_ids.append(domain.id)
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "interests_description": current_user.interests_description or [],
        "research_interests_text": current_user.research_interests_text,
        "research_domain_ids": research_domain_ids
    }

@router.post("/interests", response_model=UserOut)
async def update_interests(
    interests: UserInterestUpdate, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户研究兴趣"""
    user = current_user
    
    # 更新兴趣关键词数组
    if interests.interests_description is not None:
        user.interests_description = interests.interests_description
    
    # 获取研究领域对象
    result = await db.execute(
        select(ResearchDomain).where(ResearchDomain.id.in_(interests.research_domain_ids))
    )
    domains = result.scalars().all()
    
    # 检查所有ID是否有效
    if len(domains) != len(interests.research_domain_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="一个或多个研究领域ID无效"
        )
    
    # 更新用户的研究领域
    user.research_domains = domains
    
    await db.commit()
    await db.refresh(user)
    
    # 获取更新后的用户研究领域ID
    updated_domain_ids = [domain.id for domain in user.research_domains]
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "interests_description": user.interests_description or [],
        "research_interests_text": user.research_interests_text,
        "research_domain_ids": updated_domain_ids
    }

@router.get("/research_domains", response_model=List[ResearchDomainOut])
async def get_research_domains(db: AsyncSession = Depends(get_db)):
    """获取所有研究领域列表"""
    result = await db.execute(select(ResearchDomain))
    research_domains = result.scalars().all()
    return research_domains

# 创建一个后台任务函数
async def translate_and_update_in_background(user_id: int, text_to_translate: str, db_url: str):
    """
    后台任务：翻译文本并更新数据库
    此函数会在单独的任务中运行，不会阻塞主请求
    """
    try:
        logger.info(f"开始后台翻译任务: 用户ID={user_id}, 文本='{text_to_translate[:30]}...'")
        
        # 加载配置并初始化OpenAI客户端
        config = load_config()
        openai_config = config.get("OPENAI_SERVICE", {})
        client = get_openai_client(
            base_url=openai_config.get("base_url", "https://api.deepseek.com"), 
            api_key=openai_config.get("api_key", "")
        )
        logger.info(f"OpenAI客户端初始化成功")
        
        # 翻译文本
        logger.info(f"开始调用Qwen翻译")
        english_text = translate_text(client, text_to_translate)
        logger.info(f"翻译完成，结果: '{english_text[:50]}...'")
        
        if not english_text:
            logger.warning(f"翻译结果为空，用户ID: {user_id}")
            return
        
        # 创建新的数据库会话
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from ..models.users import User
        
        # 创建新的数据库引擎和会话
        logger.info(f"创建数据库连接: {db_url}")
        engine = create_async_engine(db_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        # 在新会话中更新数据库
        logger.info(f"开始更新数据库")
        async with async_session() as session:
            # 获取用户
            from sqlalchemy.future import select
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            
            if user:
                logger.info(f"找到用户: {user.username} (ID: {user_id})")
                user.rewrite_interest = english_text
                await session.commit()
                logger.info(f"后台任务：用户 {user.username} (ID: {user_id}) 的rewrite_interest已更新")
            else:
                logger.error(f"后台任务：找不到ID为 {user_id} 的用户")
                
    except Exception as e:
        logger.exception(f"后台翻译任务失败: {e}")

@router.put("/me/profile", response_model=UserOut)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户的个人资料"""
    # 检查research_interests_text是否有变化
    research_interests_changed = False
    new_research_interests_text = None
    logger.info(f"用户 {current_user.username} 的interests_description为: {current_user.interests_description}")
    
    if profile_data.research_interests_text is not None and profile_data.research_interests_text != current_user.research_interests_text:
        logger.info(f"更新用户 {current_user.username} 的research_interests_text")
        research_interests_changed = True
        new_research_interests_text = profile_data.research_interests_text
        current_user.research_interests_text = profile_data.research_interests_text
        logger.info(f"用户 {current_user.username} 的research_interests_text已更新: '{new_research_interests_text[:30]}...'")
        
    if profile_data.email is not None:
        logger.info(f"更新用户 {current_user.username} 的email")
        current_user.email = profile_data.email
    if profile_data.push_frequency is not None:
        logger.info(f"更新用户 {current_user.username} 的push_frequency")
        current_user.push_frequency = profile_data.push_frequency
    if profile_data.interests_description is not None:
        logger.info(f"更新用户 {current_user.username} 的interests_description")
         # 在这里增加一个推荐paper的逻辑
        if current_user.interests_description == [] or current_user.interests_description == None:
            logger.info(f"用户 {current_user.username} 的interests_description为空，更新为: {profile_data.interests_description}")
            current_user.interests_description = profile_data.interests_description
            try:
                # 1. 获取BlogBot@gmail.com用户的推荐论文
                blogbot_result = await db.execute(
                    select(UserPaperRecommendation).where(
                        UserPaperRecommendation.username == "BlogBot@gmail.com"
                    )
                )
                blogbot_recommendations = blogbot_result.scalars().all()
                
                if blogbot_recommendations:
                    logger.info(f"找到BlogBot用户推荐论文数量: {len(blogbot_recommendations)}")
                    
                    # 2. 使用用户的interests_description进行向量搜索
                    all_recommendations = []
                    
                    # 获取用户已有的论文ID，避免重复推荐
                    existing_rec_result = await db.execute(
                        select(UserPaperRecommendation.paper_id).where(
                            UserPaperRecommendation.username == current_user.username
                        )
                    )
                    existing_paper_ids = [rec.paper_id for rec in existing_rec_result.scalars().all()]
                    
                    # 获取BlogBot用户推荐记录中的论文ID列表
                    blogbot_paper_ids = [rec.paper_id for rec in blogbot_recommendations if rec.paper_id]
                    logger.info(f"BlogBot推荐论文ID数量: {len(blogbot_paper_ids)}")
                    
                    # 为每个兴趣关键词进行搜索
                    for interest in profile_data.interests_description:
                        logger.info(f"为用户兴趣 '{interest}' 搜索相关论文")
                        
                        # 构建过滤器：包含BlogBot推荐的论文ID，排除用户已有的论文ID
                        filter_params = {
                            "include": {
                                "doc_ids": blogbot_paper_ids
                            }
                        }
                        
                        if existing_paper_ids:
                            filter_params["exclude"] = {
                                "doc_ids": existing_paper_ids
                            }
                            logger.info(f"应用过滤器：包含 {len(blogbot_paper_ids)} 个BlogBot推荐论文，排除 {len(existing_paper_ids)} 个已有论文ID")
                        else:
                            logger.info(f"应用过滤器：包含 {len(blogbot_paper_ids)} 个BlogBot推荐论文")
                        
                        search_results = search_papers_via_api(
                            INDEX_SERVICE_URL, 
                            "llm", 
                            'tf-idf', 
                            0.1, 
                            filter_params
                        )
                        
                        # 将搜索结果添加到推荐列表
                        for result in search_results:
                            paper_id = result.get('doc_id')
                            
                            # 从BlogBot用户的推荐记录中获取对应的blog内容
                            blogbot_blog_result = await db.execute(
                                select(UserPaperRecommendation.blog).where(
                                    and_(
                                        UserPaperRecommendation.username == "BlogBot@gmail.com",
                                        UserPaperRecommendation.paper_id == paper_id
                                    )
                                )
                            )
                            blogbot_blog = blogbot_blog_result.scalar_one_or_none()
                            
                            # 检查是否已经存在相同的推荐
                            existing_rec = await db.execute(
                                select(UserPaperRecommendation).where(
                                    and_(
                                        UserPaperRecommendation.username == current_user.username,
                                        UserPaperRecommendation.paper_id == paper_id
                                    )
                                )
                            )
                            
                            if not existing_rec.scalar_one_or_none():
                                # 创建新的推荐记录
                                # 处理authors字段：如果是列表则转换为字符串
                                authors_data = result.get('authors', '')
                                if isinstance(authors_data, list):
                                    authors_data = ', '.join(authors_data)
                                elif authors_data is None:
                                    authors_data = ''
                                
                                new_recommendation = UserPaperRecommendation(
                                    username=current_user.username,
                                    paper_id=paper_id,
                                    title=result.get('title', ''),
                                    authors=authors_data,
                                    abstract=result.get('abstract', ''),
                                    url=result.get('url', ''),
                                    blog=blogbot_blog or '',  # 使用从BlogBot记录中获取的blog内容
                                    recommendation_reason=f"基于用户兴趣'{interest}'的向量搜索，从BlogBot推荐论文中筛选，相似度: {result.get('score', 0):.3f}",
                                    relevance_score=result.get('score', 0.0)
                                )
                                db.add(new_recommendation)
                                logger.info(f"为用户 {current_user.username} 添加推荐论文: {paper_id}")
                    
                    # 提交所有新的推荐记录
                    await db.commit()
                    logger.info(f"成功为用户 {current_user.username} 生成推荐论文")
                    
                else:
                    logger.info("未找到BlogBot用户的推荐论文")
                    
            except Exception as e:
                logger.error(f"生成推荐论文时出错: {e}")
                # 不抛出异常，避免影响主流程
        
        current_user.interests_description = profile_data.interests_description
        
    # 处理研究领域更新
    if profile_data.research_domain_ids is not None:
        logger.info(f"更新用户 {current_user.username} 的研究领域")
        result = await db.execute(select(ResearchDomain).where(ResearchDomain.id.in_(profile_data.research_domain_ids)))
        research_domains = result.scalars().all()
        if len(research_domains) != len(profile_data.research_domain_ids):
            raise HTTPException(status_code=400, detail="一个或多个提供的研究领域ID无效。")
        current_user.research_domains = research_domains
        
    # 提交用户信息更新
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    

    # 如果research_interests_text有变化，创建真正的后台任务进行翻译
    if research_interests_changed and new_research_interests_text:
        try:
            # 获取数据库连接URL
            from ..db_utils import DATABASE_URL
            logger.info(f"准备创建翻译后台任务，数据库URL: {DATABASE_URL}")
            
            # 创建后台任务，不等待其完成
            task = asyncio.create_task(
                translate_and_update_in_background(
                    current_user.id, 
                    new_research_interests_text,
                    DATABASE_URL
                )
            )
            # 添加任务完成回调
            task.add_done_callback(
                lambda t: logger.info(f"翻译任务完成状态: {'成功' if not t.exception() else f'失败: {t.exception()}'}")
            )
            logger.info(f"已为用户 {current_user.username} (ID: {current_user.id}) 创建翻译后台任务")
        except Exception as e:
            # 记录错误但不影响主流程
            logger.exception(f"创建翻译后台任务失败: {e}")
    
    return current_user

@router.get("/all", response_model=List[UserOut])
async def get_all_users_info(db: AsyncSession = Depends(get_db)):
    """获取所有用户信息（username 和 interests_description）"""
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    response_users = []
    for user in users:
        research_domain_ids = []
        # if user.research_domains:
        #     for domain in user.research_domains:
        #         research_domain_ids.append(domain.id)
        
        response_users.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "interests_description": user.interests_description or [],
            "research_interests_text": user.research_interests_text,
            "research_domain_ids": research_domain_ids
        })
    return response_users 

@router.get("/by_email/{username}", response_model=UserOut)
async def get_user_by_email(
    username: str, 
    db: AsyncSession = Depends(get_db)
):
    """获取指定邮箱用户的详细信息"""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {username} not found"
        )
    
    # 获取用户的研究领域ID (与 /me 和 /all 接口保持一致的返回结构)
    research_domain_ids = []
    # if user.research_domains:
    #     for domain in user.research_domains:
    #         research_domain_ids.append(domain.id)
            
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "interests_description": user.interests_description or [],
        "research_interests_text": user.research_interests_text,
        "research_domain_ids": research_domain_ids
    } 

@router.get("/rewrite_interest/empty", response_model=List[dict])
async def get_users_with_empty_rewrite_interest(db: AsyncSession = Depends(get_db)):
    """获取所有rewrite_interest为空且research_interests_text不为空的用户"""
    # 使用and_条件组合多个条件
    result = await db.execute(
        select(User).where(
            and_(
                User.rewrite_interest == None,  # rewrite_interest为空
                User.research_interests_text != None,  # research_interests_text不为空
                User.research_interests_text != ""  # research_interests_text不为空字符串
            )
        )
    )
    users = result.scalars().all()
    response = []
    for user in users:
        response.append({
            "username": user.username,
            "research_interests_text": user.research_interests_text,
            "interests_description": user.interests_description or []
        })
    return response 

@router.post("/rewrite_interest/batch_update")
async def batch_update_rewrite_interest(
    updates: List[RewriteInterestUpdate],
    db: AsyncSession = Depends(get_db)
):
    """批量根据username写入rewrite_interest字段"""
    updated = []
    for item in updates:
        result = await db.execute(select(User).where(User.username == item.username))
        user = result.scalars().first()
        if user:
            user.rewrite_interest = item.rewrite_interest
            updated.append(user.username)
    await db.commit()
    return {"updated": updated} 