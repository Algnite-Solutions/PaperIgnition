from typing import List
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.users import User, UserPaperRecommendation
from ..models.papers import PaperBase, PaperRecommendation
from ..db_utils import get_db

router = APIRouter(prefix="/papers", tags=["papers"])

@router.get("/recommendations/{username}", response_model=List[PaperBase])
async def get_recommended_papers_info(username: str, db: AsyncSession = Depends(get_db)):
    """
    检索UserPaperRecommendation表，返回指定用户的推荐论文基础信息列表（paper_info）
    """
    result = await db.execute(
        select(UserPaperRecommendation).where(UserPaperRecommendation.username == username)
    )
    recs = result.scalars().all()
    papers = []
    for rec in recs:
        papers.append(PaperBase(
            id=rec.paper_id,
            title=rec.title,
            authors=rec.authors,
            abstract=rec.abstract,
            url=rec.url
        ))
    return papers

@router.get("/paper_content/{paper_id}")
async def get_paper_markdown_content(paper_id: str, db: AsyncSession = Depends(get_db)):
    """
    检索UserPaperRecommendation表，返回指定论文的 markdown、blog 及推荐理由（blog, reason）
    """
    result = await db.execute(
        select(UserPaperRecommendation).where(UserPaperRecommendation.paper_id == paper_id)
    )
    rec = result.scalars().first()
    if not rec:
        raise HTTPException(status_code=404, detail="Paper content not found")
    return {
        "paper_content": rec.content,
        "blog": rec.blog,
        "recommendation_reason": rec.recommendation_reason
    }

@router.post("/recommend", status_code=status.HTTP_201_CREATED)
async def add_paper_recommendation(username: str, rec: PaperRecommendation, db: AsyncSession = Depends(get_db)):
    """
    保存推荐记录到 UserPaperRecommendation 表，字段包括 userid, paperid, title, authors, abstract, url, content, blog, reason。
    """
    try:
        # 验证用户是否存在
        user_result = await db.execute(
            select(User).where(User.username == username)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")

        # 检查是否已存在该推荐记录（可选，防止重复）
        exist_result = await db.execute(
            select(UserPaperRecommendation).where(
                UserPaperRecommendation.username == username,
                UserPaperRecommendation.paper_id == rec.paper_id
            )
        )
        exist_rec = exist_result.scalars().first()
        if exist_rec:
            raise HTTPException(status_code=400, detail="该推荐记录已存在")

        # 创建推荐记录，保存所有字段
        new_rec = UserPaperRecommendation(
            username=username,
            paper_id=rec.paper_id,
            title=rec.title,
            authors=rec.authors,
            abstract=rec.abstract,
            url=rec.url,
            content=rec.content,
            blog=rec.blog,
            recommendation_reason=rec.recommendation_reason,
            relevance_score=rec.relevance_score
        )
        db.add(new_rec)
        await db.commit()
        await db.refresh(new_rec)
        return {"message": "推荐记录添加成功", "id": new_rec.id}
    except Exception as e:
        await db.rollback()
        print(f"添加推荐记录时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="添加推荐记录失败")