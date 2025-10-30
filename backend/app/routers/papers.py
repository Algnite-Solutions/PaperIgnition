from typing import List, Optional
import re
import logging
from sqlalchemy.future import select
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import asyncio
import socket
from pydantic import BaseModel
from datetime import datetime, timezone

from ..models.users import User, UserPaperRecommendation
from ..models.papers import PaperBase, PaperRecommendation, FeedbackRequest
from ..db_utils import get_db, get_index_service_url
from ..auth.utils import get_current_user
from minio import Minio
from minio.error import S3Error
from fastapi.responses import Response

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
async def get_recommended_papers_info(username: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """根据username查询UserPaperRecommendation表中对应的paper基础信息列表"""
    # 直接从UserPaperRecommendation表获取论文信息，按推荐日期降序排序（越晚的排越上面）
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
        # 确保所有字段都有值，避免None值导致验证错误
        paper_id = rec[0] or ""
        title = rec[1] or ""
        authors = rec[2] or ""
        abstract = rec[3] or ""
        url = "https://arxiv.org/pdf/"+ paper_id # url允许为None
        submitted = rec[5]  # submitted允许为None
        recommendation_date = rec[6]  # recommendation_date允许为None
        viewed = rec[7] or False  # viewed默认为False
        blog_liked = rec[8]  # blog_liked可以为None

        # 构建符合PaperBase模型的数据
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

        # 只有当url不为None时才添加到字典
        if url is not None:
            paper_data["url"] = url

        papers.append(PaperBase(**paper_data))
    
    return papers

@router.put("/recommendations/{paper_id}/feedback", status_code=status.HTTP_200_OK)
async def update_paper_feedback(
    paper_id: str,
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update blog feedback (like/dislike) for a paper recommendation"""
    try:
        # Find all recommendation records (there might be duplicates)
        result = await db.execute(
            select(UserPaperRecommendation)
            .where(UserPaperRecommendation.username == feedback.username)
            .where(UserPaperRecommendation.paper_id == paper_id)
            .order_by(UserPaperRecommendation.recommendation_date.desc())
        )
        recommendations = result.scalars().all()

        if not recommendations:
            raise HTTPException(status_code=404, detail=f"Recommendation not found for paper {paper_id}")

        # Update blog_liked field for all matching records
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

@router.post("/{paper_id}/mark-viewed", status_code=status.HTTP_200_OK)
async def mark_paper_as_viewed(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a paper as viewed/read for the current user"""
    try:
        # Find the recommendation record for this user and paper
        result = await db.execute(
            select(UserPaperRecommendation).where(
                UserPaperRecommendation.username == current_user.username,
                UserPaperRecommendation.paper_id == paper_id
            )
        )
        recommendation = result.scalar_one_or_none()

        if not recommendation:
            # If no recommendation exists, this is fine - just return success
            # The paper might not be in the user's recommendations
            logger.info(f"No recommendation found for user {current_user.username} and paper {paper_id}")
            return {"message": "Paper not in recommendations", "viewed": False}

        # Update the viewed status
        recommendation.viewed = True
        await db.commit()

        logger.info(f"Marked paper {paper_id} as viewed for user {current_user.username}")
        return {"message": "Paper marked as viewed", "viewed": True}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error marking paper as viewed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark paper as viewed")

def extract_image_urls(markdown_content: str) -> list[str]:
    """从已处理的markdown内容中提取所有图片URL"""
    import re
    
    # 匹配已替换的图片URL
    url_pattern = r'\(http://www\.paperignition\.com/files/aignite-papers-new/([^)]+\.png)\)'
    matches = re.findall(url_pattern, markdown_content)
    
    # 构建完整的URL列表
    urls = []
    for filename in matches:
        full_url = f"http://www.paperignition.com/files/aignite-papers-new/{filename}"
        urls.append(full_url)
    
    return urls

async def validate_and_fix_image_urls(markdown_content: str, timeout: int = 10) -> str:
    """
    验证图片URL的连通性，并替换失败的URL为备用路径
    
    Args:
        markdown_content: 已处理的markdown内容
        timeout: 超时时间（秒）
    
    Returns:
        str: 修复后的markdown内容
    """
    import re
    import httpx
    
    # 提取所有图片URL
    urls = extract_image_urls(markdown_content)
    
    if not urls:
        return markdown_content
    
    logger.info(f"Found {len(urls)} image URLs to validate")
    
    # 测试每个URL的连通性
    failed_urls = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        for url in urls:
            try:
                response = await client.head(url)
                is_accessible = 200 <= response.status_code < 300
                logger.info(f"URL {url} - Status: {response.status_code}, Accessible: {is_accessible}")
                
                if not is_accessible:
                    failed_urls.append(url)
                    
            except Exception as e:
                logger.warning(f"Ping failed for {url}: {str(e)}")
                failed_urls.append(url)
    
    # 如果有失败的URL，直接删除这些图片
    if failed_urls:
        logger.warning(f"Found {len(failed_urls)} inaccessible URLs, removing them")
        
        result = markdown_content
        for failed_url in failed_urls:
            # 删除整个markdown图片语法，包括![alt text](url)部分
            # 使用正则表达式匹配并删除整个图片语法
            pattern = r'!\[[^\]]*\]\(' + re.escape(failed_url) + r'\)'
            result = re.sub(pattern, '', result)
            logger.info(f"Removed inaccessible URL: {failed_url}")
        
        return result
    
    logger.info("All image URLs are accessible")
    return markdown_content

async def process_markdown_images(markdown_content: str) -> str:
    """处理markdown中的图片路径，替换为预签名URL"""
    import re
    
    def replace_image_path(match):
        filename = match.group(1)  # 提取文件名
        new_url = f"http://www.paperignition.com/files/aignite-papers-new/{filename}"
        return f"({new_url})"
    
    # 处理四种格式的图片路径（使用非贪婪匹配来支持包含括号的文件名）
    pattern1 = r'\(\./imgs//(.*?\.png)\)'  # ./imgs//xxx.png
    pattern2 = r'\(\.\./imgs//(.*?\.png)\)'  # ../imgs//xxx.png
    pattern3 = r'\(\./imgs/(.*?\.png)\)'  # ./imgs/xxx.png
    pattern4 = r'\(\.\./imgs/(.*?\.png)\)'  # ../imgs/xxx.png
    
    # 替换所有匹配的图片路径
    result = re.sub(pattern1, replace_image_path, markdown_content)
    result = re.sub(pattern2, replace_image_path, result)
    result = re.sub(pattern3, replace_image_path, result)
    result = re.sub(pattern4, replace_image_path, result)

    result = await validate_and_fix_image_urls(result)
    
    return result

@router.get("/blog_content/{paper_id}/{username}")
async def get_blog_content(paper_id: str, username: str, db: AsyncSession = Depends(get_db)):
    """
    根据paper_id和username返回推荐博客的markdown内容，并处理其中的图片路径
    为每个图片生成预签名URL并替换原始路径
    """
    logger.info(f"Fetching blog content for paper_id: {paper_id}, username: {username}")
    
    # 从UserPaperRecommendation表获取blog内容，同时匹配paper_id和username
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
    
    # 获取原始markdown内容
    markdown_content = paper[0]
    
    # 处理图片路径，生成预签名URL
    processed_content = await process_markdown_images(markdown_content)
    
    logger.info(f"Successfully processed blog content for paper_id: {paper_id}, username: {username}")
    return processed_content

# 文件服务路由 - 需要在主应用中注册，不在papers前缀下
file_router = APIRouter(tags=["files"])

@file_router.get("/files/{bucket}/{key:path}")
async def serve_file(bucket: str, key: str):
    """
    处理文件请求，直接代理文件内容并设置正确的响应头
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
        
        # 获取文件内容
        try:
            response = minio_client.get_object(bucket, key)
            file_data = response.read()
            response.close()
            response.release_conn()
        except Exception as e:
            logger.error(f"Error reading file {bucket}/{key}: {e}")
            raise HTTPException(status_code=500, detail="Error reading file")
        
        # 根据文件类型设置响应头
        if key.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            # 图片文件，设置为预览模式
            media_type = "image/png"
            if key.lower().endswith('.jpg') or key.lower().endswith('.jpeg'):
                media_type = "image/jpeg"
            elif key.lower().endswith('.gif'):
                media_type = "image/gif"
            elif key.lower().endswith('.webp'):
                media_type = "image/webp"
            
            return Response(
                content=file_data,
                media_type=media_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # 缓存1小时
                    "Content-Length": str(len(file_data))
                }
            )
        else:
            # 其他文件，设置为下载模式
            return Response(
                content=file_data,
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{key}\"",
                    "Content-Length": str(len(file_data))
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error serving file {bucket}/{key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")


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
        if rec.blog is None or rec.blog == '':
            return {"message": "博客内容为空", "id": None}
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
        
@router.get("/image/{image_id}")
async def get_paper_image(
    image_id: str,
    index_service_url: str = Depends(get_index_service_url)
):
    """Get an image from MinIO storage via index_service.

    Args:
        image_id: Image ID to retrieve

    Returns:
        Image data and metadata from index_service
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{index_service_url}/get_image/",
                json={"image_id": image_id}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Failed to get image: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/image_storage_status/{doc_id}")
async def get_paper_image_storage_status(
    doc_id: str,
    index_service_url: str = Depends(get_index_service_url)
):
    """Get image storage status for a document via index_service.

    Args:
        doc_id: Document ID to get storage status for

    Returns:
        Storage status information from index_service
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{index_service_url}/get_image_storage_status/",
                json={"doc_id": doc_id}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Failed to get image storage status: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

