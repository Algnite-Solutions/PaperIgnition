from typing import List, Optional, Dict, Any
import os
import re
import logging
import json
from sqlalchemy.future import select
from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import asyncio
import socket
from pydantic import BaseModel
from datetime import datetime, timezone

from ..models.users import User, UserPaperRecommendation, UserRetrieveResult
from ..models.papers import PaperBase, PaperRecommendation, FeedbackRequest, RetrieveResultSave
from ..db_utils import get_db, get_paper_db, get_index_service_url
from ..auth.utils import get_current_user
# from minio import Minio  # Removed: MinIO dependency removed for Aliyun RDS migration
from minio.error import S3Error  # Required for MinIO error handling
from fastapi.responses import Response

# 设置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/digests", tags=["digests"])


# ==================== Find Similar Models ====================

class FindSimilarRequest(BaseModel):
    """Request model for find_similar endpoint"""
    query: str
    top_k: int = 10
    similarity_cutoff: float = 0.1
    filters: Optional[Dict[str, Any]] = None  # {"exclude": {"doc_ids": [...]}, "include": {"published_date": [...]}}
    result_types: Optional[List[str]] = None  # ["metadata", "text_chunks"]


class SimilarPaper(BaseModel):
    """Response model for a similar paper"""
    doc_id: str
    title: str
    abstract: str
    similarity: float
    authors: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    published_date: Optional[str] = None
    pdf_path: Optional[str] = None
    html_path: Optional[str] = None


class FindSimilarResponse(BaseModel):
    """Response model for find_similar endpoint"""
    results: List[SimilarPaper]
    query: str
    total: int


# ==================== Embedding Client for Backend ====================

class BackendEmbeddingClient:
    """
    Lightweight embedding client for backend service.
    Uses DashScope API for generating embeddings.
    """

    def __init__(self, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 model: str = "text-embedding-v4", dimension: int = 2048):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.dimension = dimension
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for a single text"""
        if not text or not text.strip():
            return None

        try:
            url = f"{self.base_url}/embeddings"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "input": text,
                "dimensions": self.dimension,
                "encoding_format": "float"
            }

            response = httpx.post(url, json=data, headers=headers, timeout=30.0)
            response.raise_for_status()

            result = response.json()
            return result.get("data", [{}])[0].get("embedding")

        except Exception as e:
            self.logger.error(f"Error getting embedding: {e}")
            return None


# Global embedding client (initialized lazily)
_embedding_client: Optional[BackendEmbeddingClient] = None
_embedding_client_config: Optional[Dict] = None


def get_embedding_client(request: Request) -> BackendEmbeddingClient:
    """Get or create the embedding client using app state config"""
    global _embedding_client, _embedding_client_config

    # Get config from app state
    config = getattr(request.app.state, 'config', {})
    dashscope_config = config.get('dashscope', {})

    # Check if config has changed
    current_config_hash = hash(str(dashscope_config))
    if _embedding_client is not None and _embedding_client_config == current_config_hash:
        return _embedding_client

    # Read from config first, fall back to environment variables
    api_key = dashscope_config.get("api_key") or os.environ.get("DASHSCOPE_API_KEY", "")
    base_url = dashscope_config.get("base_url") or os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = dashscope_config.get("embedding_model") or os.environ.get("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
    dimension = int(dashscope_config.get("embedding_dimension") or os.environ.get("DASHSCOPE_EMBEDDING_DIMENSION", "2048"))

    _embedding_client = BackendEmbeddingClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        dimension=dimension
    )
    _embedding_client_config = current_config_hash

    return _embedding_client


# ==================== Find Similar Endpoint ====================

@router.post("/find_similar", response_model=FindSimilarResponse)
async def find_similar_papers(
    request_body: FindSimilarRequest,
    request: Request,
    db: AsyncSession = Depends(get_paper_db)  # Use paper DB for pgvector
):
    """
    使用 pgvector 进行语义相似度搜索

    流程:
    1. 调用 DashScope API 获取 query embedding
    2. 构建 SQL 查询 (含 filters)
    3. 查询 paper_embeddings 表进行向量检索
    4. JOIN papers 表获取完整元数据
    5. 返回结果
    """
    try:
        # 1. 获取 query embedding
        embedding_client = get_embedding_client(request)
        query_embedding = embedding_client.get_embedding(request_body.query)

        if not query_embedding:
            logger.error(f"Failed to get embedding for query: {request_body.query[:50]}...")
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")

        # 2. 构建向量字符串 (PostgreSQL vector literal 格式)
        # 格式: '[0.1,0.2,0.3,...]'
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        # 3. 动态构建 SQL 查询
        # 使用字符串拼接将 vector literal 直接嵌入 SQL（因为 embedding_str 是安全的数值数组）
        # Note: HTML_path is uppercase in the papers table
        sql_str = f"""
            SELECT pe.doc_id, pe.title, pe.abstract,
                   p.authors, p.categories, p.published_date,
                   p.pdf_path, p."HTML_path",
                   1 - (pe.embedding <=> '{embedding_str}'::vector) as similarity
            FROM paper_embeddings pe
            LEFT JOIN papers p ON pe.doc_id = p.doc_id
            WHERE 1 - (pe.embedding <=> '{embedding_str}'::vector) >= :cutoff
        """

        params = {
            "cutoff": request_body.similarity_cutoff
        }

        # 4. 应用 filters
        if request_body.filters:
            if "exclude" in request_body.filters and "doc_ids" in request_body.filters["exclude"]:
                exclude_ids = request_body.filters["exclude"]["doc_ids"]
                if exclude_ids:
                    sql_str += " AND pe.doc_id != ALL(:exclude_ids)"
                    params["exclude_ids"] = exclude_ids

            if "include" in request_body.filters and "published_date" in request_body.filters["include"]:
                date_range = request_body.filters["include"]["published_date"]
                if len(date_range) == 2:
                    sql_str += " AND p.published_date >= :start_date AND p.published_date <= :end_date"
                    params["start_date"] = date_range[0]
                    params["end_date"] = date_range[1]

        # 5. 完成查询
        sql_str += f" ORDER BY pe.embedding <=> '{embedding_str}'::vector LIMIT :limit"
        params["limit"] = request_body.top_k

        # 6. 执行查询
        result = await db.execute(text(sql_str), params)
        rows = result.fetchall()

        # 7. 构建响应
        papers = []
        for row in rows:
            papers.append(SimilarPaper(
                doc_id=row[0],
                title=row[1] or "",
                abstract=row[2] or "",
                authors=row[3] or [],
                categories=row[4] or [],
                published_date=str(row[5]) if row[5] else None,
                pdf_path=row[6],
                html_path=row[7],
                similarity=float(row[8])
            ))

        logger.info(f"Found {len(papers)} similar papers for query: {request_body.query[:50]}...")

        return FindSimilarResponse(
            results=papers,
            query=request_body.query,
            total=len(papers)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in find_similar: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

def get_minio_client():
    """获取MinIO客户端 - 使用硬编码配置

    DISABLED: MinIO dependency removed for Aliyun RDS migration
    """
    raise HTTPException(status_code=501, detail="MinIO file serving disabled for Aliyun RDS migration")
    # try:
    #     # 硬编码的MinIO配置
    #     minio_config = {
    #         'endpoint': '10.0.1.226:9081',
    #         'access_key': 'XOrv2wfoWfPypp2zGIae',  # 移除多余的文本
    #         'secret_key': 'k9agaJuX2ZidOtaBxdc9Q2Hz5GnNKncNBnEZIoK3',
    #         'secure': False
    #     }
    #
    #     return Minio(
    #         minio_config['endpoint'],
    #         access_key=minio_config['access_key'],
    #         secret_key=minio_config['secret_key'],
    #         secure=minio_config['secure']
    #     )
    # except Exception as e:
    #     logger.error(f"Failed to create MinIO client: {e}")
    #     raise HTTPException(status_code=500, detail="MinIO client initialization error")


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
        new_url = f"http://oss.paperignition.com/imgs/{filename}"
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

    # 暂时注释掉图片验证逻辑
    # result = await validate_and_fix_image_urls(result)

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
# 接口为{backend_url}/api/digests/recommend
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
        
@router.post("/retrieve_results/save", status_code=status.HTTP_201_CREATED)
async def save_retrieve_result(
    data: RetrieveResultSave, 
    db: AsyncSession = Depends(get_db)
):
    """保存用户检索结果用于 reranking 调试
    
    Args:
        data: 包含用户名、查询、检索结果等信息
        db: 数据库会话
    
    Returns:
        保存成功的响应
    """
    try:
        # 验证用户是否存在
        user_result = await db.execute(
            select(User).where(User.username == data.username)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {data.username} 不存在")
        
        # 解析推荐日期
        if data.recommendation_date:
            try:
                rec_date = datetime.fromisoformat(data.recommendation_date.replace('Z', '+00:00'))
            except ValueError:
                rec_date = datetime.now(timezone.utc)
        else:
            rec_date = datetime.now(timezone.utc)
        
        # 创建检索结果记录
        new_retrieve_result = UserRetrieveResult(
            username=data.username,
            query=data.query,
            search_strategy=data.search_strategy,
            recommendation_date=rec_date,
            retrieve_ids=data.retrieve_ids,  # PostgreSQL JSON 类型
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

