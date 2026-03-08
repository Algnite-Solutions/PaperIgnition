"""
Digests Router - User-specific recommendation endpoints

Handles user paper recommendations, blog content, feedback, and retrieve results.
Prefix: /digests
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone
from sqlalchemy.future import select
from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..models.users import User, UserPaperRecommendation, UserRetrieveResult
from ..models.papers import PaperBase, PaperRecommendation, FeedbackRequest, RetrieveResultSave
from ..db_utils import get_db
from ..auth.utils import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/digests", tags=["digests"])


# ==================== Recommendations ====================

@router.get("/recommendations/{username}", response_model=List[PaperBase])
async def get_recommended_papers_info(username: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """根据username查询UserPaperRecommendation表中对应的paper基础信息列表"""
    result = await db.execute(
        select(
            UserPaperRecommendation.paper_id,
            UserPaperRecommendation.title,
            UserPaperRecommendation.authors,
            UserPaperRecommendation.abstract,
            UserPaperRecommendation.url,
            UserPaperRecommendation.submitted,
            UserPaperRecommendation.recommendation_date,
            UserPaperRecommendation.viewed,
            UserPaperRecommendation.blog_liked
        )
        .where(
            (UserPaperRecommendation.username == username) &
            (UserPaperRecommendation.blog.isnot(None)) &
            (UserPaperRecommendation.blog != '')
        )
        .order_by(UserPaperRecommendation.recommendation_date.desc())
        .limit(limit)
    )
    recommendations = result.all()

    papers = []
    for rec in recommendations:
        paper_id = rec[0] or ""
        title = rec[1] or ""
        authors = rec[2] or ""
        abstract = rec[3] or ""
        url = "https://arxiv.org/pdf/" + paper_id
        submitted = rec[5]
        recommendation_date = rec[6]
        viewed = rec[7] or False
        blog_liked = rec[8]

        paper_data = {
            "id": paper_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "submitted": submitted,
            "recommendation_date": recommendation_date.isoformat() if recommendation_date else None,
            "viewed": viewed,
            "blog_liked": blog_liked
        }

        if url is not None:
            paper_data["url"] = url

        papers.append(PaperBase(**paper_data))

    return papers


# ==================== Feedback ====================

@router.put("/recommendations/{paper_id}/feedback", status_code=status.HTTP_200_OK)
async def update_paper_feedback(
    paper_id: str,
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update blog feedback (like/dislike) for a paper recommendation"""
    try:
        result = await db.execute(
            select(UserPaperRecommendation)
            .where(UserPaperRecommendation.username == feedback.username)
            .where(UserPaperRecommendation.paper_id == paper_id)
            .order_by(UserPaperRecommendation.recommendation_date.desc())
        )
        recommendations = result.scalars().all()

        if not recommendations:
            raise HTTPException(status_code=404, detail=f"Recommendation not found for paper {paper_id}")

        updated_count = 0
        for recommendation in recommendations:
            recommendation.blog_liked = feedback.blog_liked
            recommendation.blog_feedback_date = datetime.now(timezone.utc)
            updated_count += 1

        await db.commit()

        logger.info(f"Updated blog feedback for paper {paper_id}, username {feedback.username}: {feedback.blog_liked} ({updated_count} records)")
        return {"message": "Feedback updated successfully", "blog_liked": feedback.blog_liked, "updated_count": updated_count}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating paper feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update feedback")


# ==================== Mark Viewed ====================

@router.post("/{paper_id}/mark-viewed", status_code=status.HTTP_200_OK)
async def mark_paper_as_viewed(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a paper as viewed/read for the current user"""
    try:
        result = await db.execute(
            select(UserPaperRecommendation).where(
                UserPaperRecommendation.username == current_user.username,
                UserPaperRecommendation.paper_id == paper_id
            )
        )
        recommendation = result.scalar_one_or_none()

        if not recommendation:
            logger.info(f"No recommendation found for user {current_user.username} and paper {paper_id}")
            return {"message": "Paper not in recommendations", "viewed": False}

        recommendation.viewed = True
        await db.commit()

        logger.info(f"Marked paper {paper_id} as viewed for user {current_user.username}")
        return {"message": "Paper marked as viewed", "viewed": True}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error marking paper as viewed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark paper as viewed")


# ==================== Blog Content (User-specific) ====================

async def _process_markdown_images(markdown_content: str) -> str:
    """处理markdown中的图片路径，替换为预签名URL"""
    import re

    def replace_image_path(match):
        filename = match.group(1)
        new_url = f"http://oss.paperignition.com/imgs/{filename}"
        return f"({new_url})"

    # 处理四种格式的图片路径（使用非贪婪匹配来支持包含括号的文件名）
    pattern1 = r'\(\.\/imgs\/\/(.*?\.png)\)'  # ./imgs//xxx.png
    pattern2 = r'\(\.\.\/imgs\/\/(.*?\.png)\)'  # ../imgs//xxx.png
    pattern3 = r'\(\.\/imgs\/(.*?\.png)\)'  # ./imgs/xxx.png
    pattern4 = r'\(\.\.\/imgs\/(.*?\.png)\)'  # ../imgs/xxx.png

    result = re.sub(pattern1, replace_image_path, markdown_content)
    result = re.sub(pattern2, replace_image_path, result)
    result = re.sub(pattern3, replace_image_path, result)
    result = re.sub(pattern4, replace_image_path, result)

    return result


@router.get("/blog_content/{paper_id}/{username}")
async def get_blog_content(paper_id: str, username: str, db: AsyncSession = Depends(get_db)):
    """
    根据paper_id和username返回推荐博客的markdown内容，并处理其中的图片路径
    """
    logger.info(f"Fetching blog content for paper_id: {paper_id}, username: {username}")

    result = await db.execute(
        select(UserPaperRecommendation.blog).where(
            (UserPaperRecommendation.paper_id == paper_id) &
            (UserPaperRecommendation.username == username)
        )
    )
    paper = result.first()

    if not paper or not paper[0]:
        logger.warning(f"Blog content not found for paper_id: {paper_id}, username: {username}")
        raise HTTPException(status_code=404, detail="Blog content not found")

    markdown_content = paper[0]
    processed_content = await _process_markdown_images(markdown_content)

    logger.info(f"Successfully processed blog content for paper_id: {paper_id}, username: {username}")
    return processed_content


# ==================== Recommend ====================

@router.post("/recommend", status_code=status.HTTP_201_CREATED)
async def add_paper_recommendation(username: str, rec: PaperRecommendation, db: AsyncSession = Depends(get_db)):
    """根据username和paper详细信息插入推荐记录到UserPaperRecommendation表中"""
    try:
        user_result = await db.execute(
            select(User).where(User.username == username)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")
        if rec.blog is None or rec.blog == '':
            return {"message": "博客内容为空", "id": None}

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
            comment=rec.comment,
        )
        db.add(new_rec)
        await db.commit()
        await db.refresh(new_rec)
        return {"message": "推荐记录添加成功", "id": new_rec.id}
    except Exception as e:
        await db.rollback()
        print(f"添加推荐记录时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="添加推荐记录失败")


# ==================== Retrieve Results ====================

@router.post("/retrieve_results/save", status_code=status.HTTP_201_CREATED)
async def save_retrieve_result(
    data: RetrieveResultSave,
    db: AsyncSession = Depends(get_db)
):
    """保存用户检索结果用于 reranking 调试"""
    try:
        user_result = await db.execute(
            select(User).where(User.username == data.username)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {data.username} 不存在")

        if data.recommendation_date:
            try:
                rec_date = datetime.fromisoformat(data.recommendation_date.replace('Z', '+00:00'))
            except ValueError:
                rec_date = datetime.now(timezone.utc)
        else:
            rec_date = datetime.now(timezone.utc)

        new_retrieve_result = UserRetrieveResult(
            username=data.username,
            query=data.query,
            search_strategy=data.search_strategy,
            recommendation_date=rec_date,
            retrieve_ids=data.retrieve_ids,
            top_k_ids=data.top_k_ids
        )

        db.add(new_retrieve_result)
        await db.commit()
        await db.refresh(new_retrieve_result)

        logger.info(f"✅ Saved retrieve result for user {data.username}, query: {data.query[:50]}...")
        return {
            "success": True,
            "message": "检索结果保存成功",
            "id": new_retrieve_result.id
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"保存检索结果时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存检索结果失败: {str(e)}")
