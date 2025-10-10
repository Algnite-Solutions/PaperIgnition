import paper_pull
#from backend.index_service import index_papers
from AIgnite.data.docset import DocSetList, DocSet
from AIgnite.generation.generator import LLMReranker
import httpx
import sys
import asyncio
import os
from typing import List, Optional

def check_connection_health(api_url, timeout=5.0):
    try:
        response = httpx.get(f"{api_url}/health", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy" and data.get("indexer_ready"):
                print("✅ Connection health check passed")
                return True
            elif data.get("status") == "healthy" and not data.get("indexer_ready"):
                print("❌ API server is not ready: ", data)
                return "not_ready"
            else:
                print("❌ API server unhealthy: ", data)
        else:
            print(f"❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: API server not accessible at {api_url}")
        print(f"Error details: {str(e)}")
    return False

def index_papers_via_api(papers, api_url):
    docset_list = DocSetList(docsets=papers)

    # Wrap in the expected format: {"docsets": DocSetList, "store_images": bool}
    data = {
        "docsets": docset_list.model_dump(),  # This creates {"docsets": [...]}
        "store_images": False
    }

    print(f"📤 Sending {len(papers)} papers to index...")
    if papers:
        print(f"📋 First paper: {papers[0].doc_id} - {papers[0].title[:50]}...")

    try:
        response = httpx.post(f"{api_url}/index_papers/", json=data, timeout=3000.0)
        response.raise_for_status()
        print("Indexing response:", response.json())
    except Exception as e:
        print("Failed to index papers:", e)

def search_papers_via_api(api_url, query, top_k=5, search_strategy='tf-idf', similarity_cutoff=0.1, filters=None):
    """Search papers using the /find_similar/ endpoint for a single query.
    Returns a list of DocSet objects corresponding to the results.
    """
    # 根据新的API结构构建payload
    payload = {
        "query": query,
        "top_k": top_k,
        "similarity_cutoff": similarity_cutoff,
        "search_strategies": [(search_strategy, 0)],  # Threshold must be between 0.0 and 1.0
        "filters": filters,
        "result_include_types": ["metadata", "text_chunks"]  # 使用正确的结果类型
    }
    try:
        response = httpx.post(f"{api_url}/find_similar/", json=payload, timeout=10.0)
        response.raise_for_status()
        results = response.json()
        print(f"\nResults for query '{query}' (strategy: {search_strategy}, cutoff: {similarity_cutoff}):")
        docsets = []
        for r in results:
            # Print for debug
            score = r.get('score', r.get('similarity_score'))
            title = r.get('title', r.get('metadata', {}).get('title'))
            print(f"  doc_id: {r.get('doc_id')}, score: {score}, title: {title}")
            metadata = r.get('metadata', {})
            print(f"    metadata: {metadata}")
            # Create DocSet instance (handle missing fields gracefully)
            try:
                # Extract metadata - most fields are nested inside 'metadata'
                metadata = r.get('metadata', {})

                # 为缺失的必需字段提供默认值
                docset_data = {
                    'doc_id': r.get('doc_id'),
                    'title': title if title else metadata.get('authors', []),
                    'authors': metadata.get('authors', []),
                    'categories': metadata.get('categories', []),
                    'published_date': metadata.get('published_date', ''),
                    'abstract': metadata.get('abstract', ''),
                    'pdf_path': metadata.get('pdf_path', ''),
                    'HTML_path': metadata.get('HTML_path', ''),
                    'comments': metadata.get('comments', ''),
                    'score': score  # 保留相似度分数
                }

                docset = DocSet(**docset_data)
                print(f"[DocSet] Created: {docset.doc_id} - {docset.title}, PDF: {docset.pdf_path}, HTML: {docset.HTML_path}")
                docsets.append(docset)
            except Exception as e:
                print(f"Failed to create DocSet for {r.get('doc_id')}: {e}")
                continue
        return docsets
    except Exception as e:
        print(f"Failed to search for query '{query}':", e)
        return []

def save_recommendations(username, papers, api_url):
    print(f"\n💾 Saving {len(papers)} recommendations for user {username}...")
    for paper in papers:
        print(paper)
        data = {
            "username": username,  # Include username in body
            "paper_id": paper.get("paper_id"),
            "title": paper.get("title", ""),
            "authors": paper.get("authors", ""),
            "abstract": paper.get("abstract", ""),
            "url": paper.get("url", ""),
            "content": paper.get("content", ""),  # 必须补全
            "blog": paper.get("blog", ""),
            "recommendation_reason": paper.get("recommendation_reason", ""),
            "relevance_score": paper.get("relevance_score", None),
            "blog_abs": paper.get("blog_abs", ""),
            "blog_title": paper.get("blog_title", ""),
        }
        try:
            resp = httpx.post(
                f"{api_url}/api/papers/recommend?username={username}",
                json=data,
                timeout=100.0
            )
            if resp.status_code == 201:
                print(f"✅ 推荐写入成功: {paper.get('paper_id')}")
            else:
                print(f"❌ 推荐写入失败: {paper.get('paper_id')}，原因: {resp.text}")
        except Exception as e:
            print(f"❌ 推荐写入异常: {paper.get('paper_id')}，错误: {e}")

def fetch_daily_papers(index_api_url: str, config, job_logger):
    """
    Fetch daily papers and return a list of DocSet objects.
    This function is a placeholder and should be replaced with the actual implementation.
    """
    # 1. Check connection health before indexing
    health = check_connection_health(index_api_url)
    if health == "not_ready" or not health:
        print("Attempting to initialize index service...")
        # Re-check health after initialization
        if not check_connection_health(index_api_url):
            print("Exiting due to failed health check after initialization.")
            sys.exit(1)

    papers = paper_pull.fetch_daily_papers()
    #papers=paper_pull.dummy_paper_fetch("./orchestrator/jsons")
    print(f"Fetched {len(papers)} papers.")

    # 2. Index papers
    index_papers_via_api(papers, index_api_url)

    # 3. Return the papers for further processing
    return papers


async def rerank_papers_with_llm(
    query: str,
    papers: List[DocSet],
    top_k: int = 10,
    api_key: Optional[str] = None,
    customized_prompt: Optional[str] = None
) -> List[DocSet]:
    """
    Rerank papers using LLM for better relevance scoring.

    This function takes a user's research interest query and a list of candidate papers,
    then uses an LLM to evaluate and rerank them based on relevance. The LLM provides
    more nuanced relevance scoring than traditional similarity metrics.

    Args:
        query: User's research interest or search query
        papers: List of candidate DocSet papers from search results
        top_k: Number of top papers to return after reranking (default: 10)
        api_key: OpenAI/DeepSeek API key (uses env var if not provided)
        customized_prompt: Custom prompt template for reranking (optional)

    Returns:
        List[DocSet]: Reranked papers with LLM scores added as attributes

    Example:
        >>> papers = search_papers_via_api(...)
        >>> reranked = await rerank_papers_with_llm(
        ...     query="I'm interested in transformer architectures",
        ...     papers=papers,
        ...     top_k=5
        ... )
    """
    if not papers:
        print("⚠️ No papers to rerank")
        return []

    print(f"🤖 Starting LLM reranking for {len(papers)} papers...")

    try:
        # Convert DocSet objects to dict format for reranker
        candidates = []
        for paper in papers:
            candidates.append({
                'doc_id': paper.doc_id,
                'metadata': {
                    'title': paper.title or 'Unknown Title',
                    'abstract': paper.abstract or '',
                    'authors': ', '.join(paper.authors) if isinstance(paper.authors, list) else paper.authors
                },
                'similarity_score': getattr(paper, 'score', 0.0)
            })

        # Initialize LLM rerancker
        reranker = LLMReranker(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            model_name="deepseek-chat",
            api_base="https://api.deepseek.com/v1",
            customized_prompt=customized_prompt
        )

        # Perform reranking
        print(f"📊 Calling LLM API for reranking...")
        reranked_results = await reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k
        )

        # Convert back to DocSet objects with LLM scores
        # Create a mapping for fast lookup
        paper_map = {p.doc_id: p for p in papers}

        result = []
        for reranked_item in reranked_results:
            doc_id = reranked_item.get('doc_id')
            if doc_id in paper_map:
                original_paper = paper_map[doc_id]
                result.append(original_paper)

        print(f"✅ LLM reranking complete: {len(result)} papers reranked and sorted")
        return result

    except Exception as e:
        print(f"⚠️ LLM reranking failed: {e}")
        print(f"   Returning original {len(papers)} papers without reranking")
        import traceback
        traceback.print_exc()
        return papers[:top_k] if len(papers) > top_k else papers
