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

def search_papers_via_api(api_url, query, search_strategy='tf-idf', similarity_cutoff=0.1, filters=None):
    """Search papers using the /find_similar/ endpoint for a single query.
    Returns a list of DocSet objects corresponding to the results.
    """
    # 根据新的API结构构建payload
    payload = {
        "query": query,
        "top_k": 2,
        "similarity_cutoff": similarity_cutoff,
        "search_strategies": [(search_strategy, 0.0)],  # 新API使用元组格式 (strategy, threshold)
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
            
            # Create DocSet instance (handle missing fields gracefully)
            try:
                # 为缺失的必需字段提供默认值
                docset_data = {
                    'doc_id': r.get('doc_id'),
                    'title': title if title else 'Unknown Title',
                    'authors': r.get('authors', []),
                    'categories': r.get('categories', []),
                    'published_date': r.get('published_date', ''),
                    'abstract': r.get('abstract', ''),
                    'pdf_path': r.get('pdf_path', ''),
                    'HTML_path': r.get('HTML_path', ''),
                    'comments': r.get('comments', ''),
                    'score': score  # 保留相似度分数
                }
                
                docset = DocSet(**docset_data)
                print(f"[DocSet] Created with title: {docset.title}")
                docsets.append(docset)
            except Exception as e:
                print(f"Failed to create DocSet for {r.get('doc_id')}: {e}")
                continue
        return docsets
    except Exception as e:
        print(f"Failed to search for query '{query}':", e)
        return []

def save_recommendations(username, papers, api_url):
    for paper in papers:
        print(paper)
        data = {
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
    index_papers_via_api(papers, index_api_url)
    
    # 3. Return the papers for further processing
    return papers
