import paper_pull
#from backend.index_service import index_papers
from AIgnite.data.docset import DocSetList, DocSet
import httpx
import sys

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

def index_papers_via_api(papers, api_url, store_images=False, keep_temp_image=False):
    """
    Index papers using the /index_papers/ endpoint.
    
    Args:
        papers: List of DocSet objects
        api_url: API base URL
        store_images: Whether to store images to MinIO (default: False)
        keep_temp_image: If False, delete temporary image files after successful storage (default: False)
    """
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
        response = httpx.post(f"{api_url}/index_papers/", json=data, timeout=6000.0)
        response.raise_for_status()
        print("Indexing response:", response.json())
    except Exception as e:
        print("Failed to index papers:", e)

def search_papers_via_api(api_url, query, search_strategy='tf-idf', similarity_cutoff=0.1, filters=None):
    """Search papers using the /find_similar/ endpoint for a single query.
    Returns a list of DocSet objects corresponding to the results.
    """
    # 检查连接健康状态
    health = check_connection_health(api_url, timeout=5.0)
    if not health:
        print(f"❌ 搜索服务 {api_url} 不可用，跳过查询 '{query}'")
        return []
    
    # 根据新的API结构构建payload
    payload = {
        "query": query,
        "top_k": 1,
        "similarity_cutoff": similarity_cutoff,
        "search_strategies": [(search_strategy, 1.5)],  # 新API使用元组格式 (strategy, threshold)
        "filters": filters,
        "result_include_types": ["metadata", "text_chunks"]  # 使用正确的结果类型
    }
    try:
        response = httpx.post(f"{api_url}/find_similar/", json=payload, timeout=30.0)
        response.raise_for_status()
        results = response.json()
        print(f"\nResults for query '{query}' (strategy: {search_strategy}, cutoff: {similarity_cutoff}):")
        docsets = []
        for r in results:
            # Create DocSet instance (handle missing fields gracefully)
            try:
                # 提取metadata中的信息
                metadata = r.get('metadata', {})
                
                # 处理chunks数据，确保符合DocSet定义
                def process_text_chunks(chunks_data):
                    """处理text_chunks数据，转换为符合DocSet定义的格式"""
                    if not chunks_data:
                        return []
                    
                    processed_chunks = []
                    for chunk in chunks_data:
                        if isinstance(chunk, dict):
                            # 检查是否已经是正确的格式
                            if 'id' in chunk and 'type' in chunk and 'text' in chunk:
                                processed_chunks.append(chunk)
                            elif 'chunk_id' in chunk and 'text_content' in chunk:
                                # 转换API格式到DocSet格式
                                converted_chunk = {
                                    'id': chunk['chunk_id'],
                                    'type': 'text',
                                    'text': chunk['text_content']
                                }
                                processed_chunks.append(converted_chunk)
                            else:
                                # 跳过无效的chunk
                                print(f"Warning: Skipping invalid text chunk: {chunk}")
                        else:
                            print(f"Warning: Skipping non-dict text chunk: {chunk}")
                    return processed_chunks
                
                # 为缺失的必需字段提供默认值，确保符合DocSet定义
                docset_data = {
                    'doc_id': r.get('doc_id'),
                    'title': metadata.get('title', 'Unknown Title'),
                    'authors': metadata.get('authors', []),
                    'categories': metadata.get('categories', []),
                    'published_date': metadata.get('published_date', ''),
                    'abstract': metadata.get('abstract', ''),
                    'pdf_path': metadata.get('pdf_path', ''),
                    'HTML_path': metadata.get('HTML_path'),
                    'text_chunks': process_text_chunks(r.get('text_chunks', [])),
                    'figure_chunks': [],
                    'table_chunks': [],
                    'metadata': metadata,
                    'comments': metadata.get('comments', '')
                }
                
                docset = DocSet(**docset_data)
                print(f"[DocSet] Created with title: {docset.title}")
                docsets.append(docset)
            except Exception as e:
                print(f"Failed to create DocSet for {r.get('doc_id')}: {e}")
                continue
        return docsets
    except httpx.TimeoutException:
        print(f"❌ 搜索查询 '{query}' 超时（30秒），请检查网络连接或服务器状态")
        return []
    except httpx.ConnectError:
        print(f"❌ 无法连接到搜索服务 {api_url}，请检查服务是否运行")
        return []
    except httpx.HTTPStatusError as e:
        print(f"❌ 搜索查询 '{query}' 返回错误状态码: {e.response.status_code}")
        print(f"错误详情: {e.response.text}")
        return []
    except Exception as e:
        print(f"❌ 搜索查询 '{query}' 时发生未知错误: {e}")
        return []

def save_recommendations(username, papers, api_url):
    for paper in papers:
        print(paper)
        data = {
            "username": username,
            "paper_id": paper.get("paper_id"),
            "title": paper.get("title", ""),
            "authors": paper.get("authors", ""),
            "abstract": paper.get("abstract", ""),
            "url": paper.get("url", ""),
            "content": paper.get("content", ""),
            "blog": paper.get("blog", ""),
            "recommendation_reason": paper.get("recommendation_reason", ""),
            "relevance_score": paper.get("relevance_score", None),
            "blog_abs": paper.get("blog_abs", ""),
            "blog_title": paper.get("blog_title", ""),
            "submitted": paper.get("submitted", ""),
            "comment": paper.get("comment", ""),
        }
        try:
            resp = httpx.post(
                f"{api_url}/api/papers/recommend",
                params={"username": username},
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
    index_papers_via_api(papers, index_api_url, store_images=True, keep_temp_image=True)
    
    # 3. Return the papers for further processing
    return papers
