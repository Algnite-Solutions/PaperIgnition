from typing import List
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime, timezone

from ..models.users import User, UserPaperRecommendation
from ..models.papers import PaperBase, PaperRecommendation
from ..db_utils import get_db
from ..auth.utils import get_current_user

router = APIRouter(prefix="/papers", tags=["papers"])

@router.get("/recommendations/{username}", response_model=List[PaperBase])
async def get_recommended_papers_info(username: str, db: AsyncSession = Depends(get_db)):
    """根据username查询UserPaperRecommendation表中对应的paper基础信息列表"""
    # 直接从UserPaperRecommendation表获取论文信息
    result = await db.execute(
        select(
            UserPaperRecommendation.paper_id,
            UserPaperRecommendation.title,
            UserPaperRecommendation.authors,
            UserPaperRecommendation.abstract,
            UserPaperRecommendation.url
        ).where(UserPaperRecommendation.username == username)
    )
    recommendations = result.all()
    
    papers = []
    for rec in recommendations:
        # 确保所有字段都有值，避免None值导致验证错误
        paper_id = rec[0] or ""
        title = rec[1] or ""
        authors = rec[2] or ""
        abstract = rec[3] or ""
        url = rec[4]  # url允许为None
        
        # 构建符合PaperBase模型的数据
        paper_data = {
            "id": paper_id,
            "title": title,
            "authors": authors,
            "abstract": abstract
        }
        
        # 只有当url不为None时才添加到字典
        if url is not None:
            paper_data["url"] = url
            
        papers.append(PaperBase(**paper_data))
    
    return papers

@router.get("/paper_content/{paper_id}")
async def get_paper_markdown_content(paper_id: str, db: AsyncSession = Depends(get_db)):
    """根据paper_id返回论文的markdown内容"""
    # 直接从UserPaperRecommendation表获取blog内容
    result = await db.execute(select(UserPaperRecommendation.blog).where(UserPaperRecommendation.paper_id == paper_id))
    paper = result.first()
    
    if not paper or not paper[0]:
        raise HTTPException(status_code=404, detail="Paper content not found")
    
    return paper[0]

# 这个接口应该为后端使用，插入对任意用户的推荐，应当受到保护
# 接口为{backend_url}/api/papers/recommend
# TODO(@Hui Chen): 需要添加安全验证
@router.post("/recommend", status_code=status.HTTP_201_CREATED)
async def add_paper_recommendation(username:str, rec: PaperRecommendation, db: AsyncSession = Depends(get_db)):
    """根据username和paper详细信息插入推荐记录到UserPaperRecommendation表中"""
    try:
        # 验证用户是否存在
        user_result = await db.execute(
            select(User).where(User.username == username)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")

        # 创建推荐记录（直接使用传入的数据）
        new_rec = UserPaperRecommendation(
            username=username,
            paper_id=rec.paper_id,
            title=rec.title,
            authors=rec.authors,
            abstract=rec.abstract,
            url=rec.url,
            blog=rec.blog,
            blog_abs=rec.blog_abs,
            blog_title=rec.blog_title,
            recommendation_reason=rec.recommendation_reason,
            relevance_score=rec.relevance_score,
            submitted=rec.submitted,  
            comment=rec.comment
        )
        db.add(new_rec)
        await db.commit()
        await db.refresh(new_rec)
        return {"message": "推荐记录添加成功", "id": new_rec.id}
    except Exception as e:
        await db.rollback()
        print(f"添加推荐记录时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="添加推荐记录失败")

# 博客反馈相关接口
class BlogFeedbackRequest(BaseModel):
    paper_id: str
    liked: bool  # True=喜欢, False=不喜欢

@router.post("/blog-feedback", status_code=status.HTTP_200_OK)
async def submit_blog_feedback(
    feedback: BlogFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提交博客反馈（喜欢/不喜欢）"""
    try:
        # 查找对应的推荐记录
        result = await db.execute(
            select(UserPaperRecommendation).where(
                UserPaperRecommendation.username == current_user.username,
                UserPaperRecommendation.paper_id == feedback.paper_id
            )
        )
        recommendation = result.scalar_one_or_none()
        
        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail="推荐记录不存在"
            )
        
        # 更新博客反馈
        recommendation.blog_liked = feedback.liked
        recommendation.blog_feedback_date = datetime.now(timezone.utc)
        
        await db.commit()
        
        return {
            "message": "博客反馈提交成功",
            "liked": feedback.liked
        }
        
    except Exception as e:
        await db.rollback()
        print(f"提交博客反馈时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="提交博客反馈失败")

@router.get("/blog-feedback/{paper_id}")
async def get_blog_feedback(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户对特定论文博客的反馈状态"""
    try:
        result = await db.execute(
            select(UserPaperRecommendation.blog_liked).where(
                UserPaperRecommendation.username == current_user.username,
                UserPaperRecommendation.paper_id == paper_id
            )
        )
        blog_liked = result.scalar_one_or_none()
        
        return {
            "paper_id": paper_id,
            "blog_liked": blog_liked  # None=未评价, True=喜欢, False=不喜欢
        }
        
    except Exception as e:
        print(f"获取博客反馈时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取博客反馈失败")