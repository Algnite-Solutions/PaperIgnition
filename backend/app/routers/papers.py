"""
Papers Router - Paper search, content, metadata, and image endpoints

Handles paper-level operations (not user-specific).
Prefix: /papers
"""
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

from ..db_utils import get_paper_db, get_index_service_url
from ..auth.utils import get_current_user

# 设置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["papers"])


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


# ==================== Image Helpers ====================

async def process_markdown_images(markdown_content: str) -> str:
    """处理markdown中的图片路径，替换为预签名URL"""

    def replace_image_path(match):
        filename = match.group(1)  # 提取文件名
        new_url = f"http://oss.paperignition.com/imgs/{filename}"
        return f"({new_url})"

    # 处理四种格式的图片路径（使用非贪婪匹配来支持包含括号的文件名）
    pattern1 = r'\(\.\/imgs\/\/(.*?\.png)\)'  # ./imgs//xxx.png
    pattern2 = r'\(\.\.\/imgs\/\/(.*?\.png)\)'  # ../imgs//xxx.png
    pattern3 = r'\(\.\/imgs\/(.*?\.png)\)'  # ./imgs/xxx.png
    pattern4 = r'\(\.\.\/imgs\/(.*?\.png)\)'  # ../imgs/xxx.png

    # 替换所有匹配的图片路径
    result = re.sub(pattern1, replace_image_path, markdown_content)
    result = re.sub(pattern2, replace_image_path, result)
    result = re.sub(pattern3, replace_image_path, result)
    result = re.sub(pattern4, replace_image_path, result)

    return result


# ==================== Paper Content (Global) ====================

@router.get("/content/{paper_id}")
async def get_paper_content(
    paper_id: str,
    db: AsyncSession = Depends(get_paper_db)
):
    """Get global blog content for a paper from the papers table.

    This replaces the index_service's /paper_content/{paper_id} endpoint.
    Queries the `papers` table in the paper database for the blog field,
    and processes markdown image paths.

    Args:
        paper_id: Document ID (doc_id) of the paper

    Returns:
        Processed blog content as a string with fixed image URLs

    Raises:
        HTTPException: If paper not found or blog content is empty
    """
    if not paper_id or not paper_id.strip():
        raise HTTPException(status_code=422, detail="Paper ID cannot be empty")

    paper_id = paper_id.strip()
    logger.info(f"Fetching paper content for paper_id: {paper_id}")

    try:
        # Query blog content from papers table
        query = text("SELECT blog FROM papers WHERE doc_id = :paper_id")
        result = await db.execute(query, {"paper_id": paper_id})
        row = result.fetchone()

        if not row or not row[0]:
            logger.warning(f"Blog content not found for paper_id: {paper_id}")
            raise HTTPException(status_code=404, detail="Blog content not found")

        # Process image paths
        markdown_content = row[0]
        processed_content = await process_markdown_images(markdown_content)

        logger.info(f"Successfully processed paper content for paper_id: {paper_id}")
        return processed_content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paper content for {paper_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get paper content: {str(e)}")


# ==================== Paper Metadata ====================

@router.get("/metadata/{doc_id}")
async def get_paper_metadata(
    doc_id: str,
    db: AsyncSession = Depends(get_paper_db)
):
    """Get metadata for a specific paper from the papers table.

    This replaces the index_service's /get_metadata/{doc_id} endpoint.

    Args:
        doc_id: The document ID of the paper

    Returns:
        Dictionary containing paper metadata including title, abstract, authors, etc.
    """
    if not doc_id or not doc_id.strip():
        raise HTTPException(status_code=422, detail="Document ID cannot be empty")

    doc_id = doc_id.strip()

    try:
        query = text("""
            SELECT doc_id, title, abstract, authors, categories, 
                   published_date, pdf_path, "HTML_path", comments, blog
            FROM papers WHERE doc_id = :doc_id
        """)
        result = await db.execute(query, {"doc_id": doc_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Metadata not found for doc_id: {doc_id}")

        metadata = {
            "doc_id": row[0],
            "title": row[1] or "",
            "abstract": row[2] or "",
            "authors": row[3] or [],
            "categories": row[4] or [],
            "published_date": str(row[5]) if row[5] else "",
            "pdf_path": row[6] or "",
            "html_path": row[7] or "",
            "comments": row[8] or "",
            "has_blog": bool(row[9]),
        }

        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata for {doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MinIO / Image Endpoints ====================
# Note: MinIO file serving disabled for Aliyun RDS migration
# Images are now served directly from Aliyun OSS via http://oss.paperignition.com/imgs/
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
