from typing import List
import re
import logging
from datetime import timedelta
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from minio import Minio
from minio.error import S3Error
import yaml
import os
from pydantic import BaseModel
from datetime import datetime, timezone

from ..models.users import User, UserPaperRecommendation
from ..models.papers import PaperBase, PaperRecommendation
from ..db_utils import get_db
from ..auth.utils import get_current_user

# 设置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["papers"])

def get_minio_client():
    """获取MinIO客户端 - 使用硬编码配置"""
    try:
        # 硬编码的MinIO配置
        minio_config = {
            'endpoint': '10.0.1.226:9081',
            'access_key': 'XOrv2wfoWfPypp2zGIae',  # 移除多余的文本
            'secret_key': 'k9agaJuX2ZidOtaBxdc9Q2Hz5GnNKncNBnEZIoK3',
            'secure': False
        }
        
        return Minio(
            minio_config['endpoint'],
            access_key=minio_config['access_key'],
            secret_key=minio_config['secret_key'],
            secure=minio_config['secure']
        )
    except Exception as e:
        logger.error(f"Failed to create MinIO client: {e}")
        raise HTTPException(status_code=500, detail="MinIO client initialization error")


@router.get("/recommendations/{username}", response_model=List[PaperBase])
async def get_recommended_papers_info(username: str, db: AsyncSession = Depends(get_db)):
    """根据username查询UserPaperRecommendation表中对应的paper基础信息列表"""
    # 直接从UserPaperRecommendation表获取论文信息，按推荐日期降序排序（越晚的排越上面）
    result = await db.execute(
        select(
            UserPaperRecommendation.paper_id,
            UserPaperRecommendation.title,
            UserPaperRecommendation.authors,
            UserPaperRecommendation.abstract,
            UserPaperRecommendation.url
        ).where(UserPaperRecommendation.username == username)
        .order_by(UserPaperRecommendation.recommendation_date.desc())
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

def extract_image_filename(image_path: str) -> str:
    """从图片路径中提取文件名"""
    # 处理各种路径格式，提取最后一个文件名
    import os
    return os.path.basename(image_path.strip())

async def process_markdown_images(markdown_content: str) -> str:
    """处理markdown中的图片路径，替换为预签名URL"""
    import re
    
    # 匹配markdown图片格式: ![alt](path)
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    
    async def replace_image(match):
        alt_text = match.group(1)
        image_path = match.group(2)
        
        # 提取文件名
        filename = extract_image_filename(image_path)
        
        # 生成预签名URL
        try:
            filename = "test.png"
            await serve_file(bucket="aignite-papers", key=filename)
            presigned_url = f" http://10.0.1.226:8888/files/aignite-papers/{filename}"
            
            if presigned_url:
                return f'![{alt_text}]({presigned_url})'
            else:
                # 如果生成失败，保持原路径
                return match.group(0)
        except Exception as e:
            logger.error(f"Error processing image {filename}: {str(e)}")
            return match.group(0)
    
    # 找到所有匹配的图片
    matches = list(re.finditer(pattern, markdown_content))
    
    # 异步处理所有图片
    replacements = []
    for match in matches:
        replacement = await replace_image(match)
        replacements.append((match, replacement))
    
    # 从后往前替换，避免位置偏移
    result = markdown_content
    for match, replacement in reversed(replacements):
        result = result[:match.start()] + replacement + result[match.end():]
    
    return result

@router.get("/paper_content/{paper_id}")
async def get_paper_markdown_content(paper_id: str, db: AsyncSession = Depends(get_db)):
    """
    根据paper_id返回论文的markdown内容，并处理其中的图片路径
    为每个图片生成预签名URL并替换原始路径
    """
    logger.info(f"Fetching paper content for paper_id: {paper_id}")
    
    # 直接从UserPaperRecommendation表获取blog内容
    result = await db.execute(select(UserPaperRecommendation.blog).where(UserPaperRecommendation.paper_id == paper_id))
    paper = result.first()
    
    if not paper or not paper[0]:
        logger.warning(f"Paper content not found for paper_id: {paper_id}")
        raise HTTPException(status_code=404, detail="Paper content not found")
    
    # 获取原始markdown内容
    markdown_content = paper[0]
    
    # 处理图片路径，生成预签名URL
    processed_content = await process_markdown_images(markdown_content)
    
    logger.info(f"Successfully processed paper content for paper_id: {paper_id}")
    return processed_content

# 文件服务路由 - 需要在主应用中注册，不在papers前缀下
file_router = APIRouter(tags=["files"])

@file_router.get("/files/{bucket}/{key:path}")
async def serve_file(bucket: str, key: str):
    """
    处理文件请求，生成MinIO预签名URL并重定向
    步骤3.3: 后端现签名并302/307
    
    流程：
    1. 验证对象是否存在
    2. 生成预签名URL（15分钟有效期）
    3. 返回307重定向到MinIO
    """
    try:
        logger.info(f"Serving file request: {bucket}/{key}")
        
        # 获取MinIO客户端
        minio_client = get_minio_client()
        
        # 验证对象是否存在
        try:
            stat = minio_client.stat_object(bucket, key)
            logger.debug(f"File found: {bucket}/{key}, size: {stat.size}")
        except S3Error as e:
            if e.code == 'NoSuchKey':
                logger.warning(f"File not found: {bucket}/{key}")
                raise HTTPException(status_code=404, detail=f"File not found: {bucket}/{key}")
            else:
                logger.error(f"MinIO error for {bucket}/{key}: {e}")
                raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")
        
        # 生成预签名URL，有效期15分钟
        presigned_url = minio_client.presigned_get_object(
            bucket, 
            key, 
            expires=timedelta(minutes=15)
        )
        
        logger.info(f"Generated presigned URL for {bucket}/{key}")
        
        # 返回307重定向到预签名URL
        return RedirectResponse(url=presigned_url, status_code=307)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error serving file {bucket}/{key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating presigned URL: {str(e)}")


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