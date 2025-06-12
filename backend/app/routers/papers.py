from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from ..db.database import get_db
from ..models.user import PaperRecommendation

router = APIRouter(prefix="/papers", tags=["papers"])

# 论文模型
class PaperBase(BaseModel):
    id: str
    title: str
    authors: str
    abstract: str
    url: Optional[str] = None

class PaperDetail(PaperBase):
    markdownContent: str

class PaperRecommendationIn(BaseModel):
    username: str
    paper_id: str
    recommendation_reason: Optional[str] = None
    relevance_score: Optional[float] = None

# 模拟论文数据
MOCK_PAPERS = [
    {
        "id": "2023.12345",
        "title": "深度学习在自然语言处理中的应用",
        "authors": "张三, 李四, 王五",
        "abstract": "本文探讨了深度学习技术在自然语言处理领域的最新进展...",
        "url": "https://example.com/papers/2023.12345",
        "content": """Okay, here is a blog post summarizing the TigerVector paper, incorporating only the specified figures and adhering to your formatting requirements.

---

## TigerVector: Bringing High-Performance Vector Search to Graph Databases for Advanced RAG

Retrieval-Augmented Generation (RAG) has become a cornerstone for grounding Large Language Models (LLMs) with external data. While traditional RAG often relies on vector databases storing semantic embeddings, this approach can struggle with complex queries that require understanding relationships between data points – a strength of graph databases.

Enter VectorGraphRAG, a promising hybrid approach that combines the power of vector search for semantic similarity with graph traversal for structural context. The paper "TigerVector: Supporting Vector Search in Graph Databases for Advanced RAGs" introduces TigerVector, a novel system that integrates vector search directly into TigerGraph, a distributed graph database. This unified approach aims to overcome the limitations of using separate systems, offering benefits like data consistency, reduced silos, and streamlined hybrid queries.

Integrating high-performance vector search into a graph database is challenging. TigerVector tackles this through several key innovations:

**A Unified Data Model:** TigerVector introduces a new \`embedding\` attribute type for vertices. This isn't just a list of floats; it explicitly manages crucial metadata like dimensionality, the model used, index type, and similarity metric. This dedicated type facilitates managing different types of embeddings and ensures compatibility during queries.

**Decoupled Storage:** Recognizing that vector embeddings are often much larger than other attributes, TigerVector stores vectors separately in "embedding segments." These segments mirror the vertex partitioning of the graph, ensuring related vector and graph data reside together for efficient processing. This decoupling also optimizes updates and index management.

![Figure 3](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Decoupled Storage. Vectors within a vertex segment (left) are stored separately in another embedding segment (right), while keeping the same ids.

**Leveraging MPP Architecture:** Built within TigerGraph's Massively Parallel Processing (MPP) architecture, TigerVector distributes vector data and processing across multiple machines. Vector indexes (currently supporting HNSW) are built per segment, and queries are parallelized, with results merged by a coordinator.
![Figure 5](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Distributed Query Processing. The coordinator prepares top-k vector search requests in the send queue and dispatches requests to worker servers. Each worker conducts top-k search locally and sends IDs and distances as results back to the response pool in the coordinator.

**GSQL Integration:** TigerVector integrates vector search into TigerGraph's GSQL query language. This includes adding \`VECTOR_DIST\` to \`ORDER BY...LIMIT\` syntax for declarative search and introducing a flexible \`VectorSearch()\` function. This function allows vector search results to be easily composed with graph query blocks, enabling complex hybrid queries.

**Advanced Hybrid Search:** TigerVector supports powerful query patterns beyond simple vector similarity, including filtered vector search and vector search on graph patterns. The \`VectorSearch()\` function can accept a vertex set from a graph query as a filter, allowing users to find similar items *within* a specific graph context (e.g., find similar posts written by people Alice knows).
![Figure 6](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Demonstration of Combing Community Detection and Vector Search. The Person vertices are partitioned into three communities, colored green, blue, and yellow. The top-k Posts from each community are colored red.

**Efficient Updates:** TigerVector supports transactional updates to vector data, leveraging TigerGraph's MVCC scheme and employing background vacuum processes to incrementally merge delta records into vector indexes. This ensures updates are atomic and efficient.

**Performance:** The paper presents extensive experiments comparing TigerVector with other graph databases supporting vector search (Neo4j, Amazon Neptune) and a specialized vector database (Milvus).
![Figure 7](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Throughput Evaluation on SIFT100M and Deep100M. TigerVector significantly outperforms Neo4j and Amazon Neptune in throughput and recall for vector search.
![Figure 8](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Latency Evaluation on SIFT100M and Deep100M. TigerVector shows significantly lower latency compared to Neo4j and Amazon Neptune.
TigerVector demonstrates performance comparable to, and sometimes even higher than, Milvus, a specialized vector database, particularly in throughput.

**Scalability:** Experiments show TigerVector scales effectively with both the number of nodes and dataset size, leveraging its distributed architecture.
![Figure 9](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Node Scalability. TigerVector exhibits near-linear throughput gain when scaling the number of machines.
![Figure 10](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Data Size Scalability. Throughput decreases roughly proportionally as the dataset size scales by 10x, demonstrating good scalability.

In conclusion, TigerVector represents a significant step towards a unified platform for graph and vector data, enabling powerful hybrid searches essential for advanced RAG applications. Its performance is competitive with specialized vector databases and significantly surpasses other graph databases with vector capabilities. TigerVector was integrated into TigerGraph v4.2, released in December 2024.
"""
    },
]


@router.get("/recommendations/{username}", response_model=List[PaperBase])
async def get_recommended_papers_info(username: str, db: AsyncSession = Depends(get_db)):
    """根据username查询PaperRecommendation表中对应的paper基础信息列表"""
    result = await db.execute(select(PaperRecommendation.paper_id).where(PaperRecommendation.username == username))
    paper_ids = [row[0] for row in result.all()]
    papers=get_papers_by_ids(paper_ids)
    print("========================")
    print(papers)
    print("========================")
    return papers

# TODO(@Fang Guo): 输入为paper_id列表，返回为以下json格式的内容,实际上我觉得可以在其他地方实现，import进来就行
"""
    {
        "id": "2023.24680",
        "title": "多模态大语言模型研究进展",
        "authors": "孙八, 周九, 吴十",
        "abstract": "多模态大语言模型将文本、图像等多种模态信息融合处理...",
        "url": "https://example.com/papers/2023.24680"
    }
"""
def get_papers_by_ids(paper_ids: List[str]):
    """根据paper_id列表返回论文详情（mock数据）"""
    # 用mock数据模拟数据库查询
    papers = []
    for pid in paper_ids:
        paper = next((p for p in MOCK_PAPERS if p["id"] == pid), None)
        if paper:
            papers.append(PaperBase(**paper))
    return papers

@router.get("/paper_content/{paper_id}")
async def get_paper_markdown_content(paper_id: str):
    """根据paper_id返回论文的markdown内容（mock数据）"""
    paper = get_content_by_ids(paper_id)
    print("========================")
    print(paper)
    print("========================")
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper content not found")
    return paper

# TODO(@Fang Guo): 输入为paper_id，返回为str格式的markdown内容,暂时不考虑图片
def get_content_by_ids(paper_id: str):
    """根据paper_id返回论文详情（mock数据）"""
    content = next((p["content"] for p in MOCK_PAPERS if p["id"] == paper_id), None)
    return content

# 这个接口应该为后端使用，插入对任意用户的推荐，应当受到保护
# 接口为{backend_url}/api/papers/recommend
# TODO(@Hui Chen): 需要添加安全验证
@router.post("/recommend", status_code=status.HTTP_201_CREATED)
async def add_paper_recommendation(rec: PaperRecommendationIn, db: AsyncSession = Depends(get_db)):
    """根据username和paper_id插入推荐记录"""
    new_rec = PaperRecommendation(
        username=rec.username,
        paper_id=rec.paper_id,
        recommendation_reason=rec.recommendation_reason,
        relevance_score=rec.relevance_score
    )
    db.add(new_rec)
    try:
        await db.commit()
        await db.refresh(new_rec)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="该推荐记录已存在或数据不合法")
    return {"message": "推荐记录添加成功", "id": new_rec.id}


