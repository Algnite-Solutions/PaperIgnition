import paper_pull
from generate_blog import run_batch_generation
#from backend.index_service import index_papers
import requests
import os
from backend.app.db_utils import load_config as load_backend_config
from AIgnite.data.docset import DocSetList, DocSet
import httpx
import sys
import asyncio
def initialize_database(api_url, config):
    try:
        payload = {"config": config}
        response = httpx.post(f"{api_url}/init_database", json=payload, params={"recreate_databases": True}, timeout=60.0)
        response.raise_for_status()
        print("✅ Database and indexer initialized:", response.json())
        return True
    except Exception as e:
        print("❌ Failed to initialize database/indexer:", e)
        return False

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
    data = docset_list.dict()
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
    payload = {
        "query": query,
        "top_k": 1,
        "similarity_cutoff": similarity_cutoff,
        "strategy_type": search_strategy,
        "filters": filters
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
            
            # Create DocSet instance with proper field handling
            try:
                # Prepare data with required fields and defaults
                docset_data = {
                    'doc_id': r.get('doc_id'),
                    'title': r.get('title', 'Unknown Title'),
                    'authors': r.get('authors', ['Unknown Author']),
                    'categories': r.get('categories', ['Unknown Category']),
                    'published_date': r.get('published_date', '2025-01-01'),
                    'abstract': r.get('abstract', 'No abstract available'),
                    'text_chunks': r.get('text_chunks', []),
                    'figure_chunks': r.get('figure_chunks', []),
                    'table_chunks': r.get('table_chunks', []),
                    'metadata': r.get('metadata', {}),
                    'pdf_path': r.get('pdf_path', ''),
                    'HTML_path': r.get('HTML_path')
                }
                
                # Create DocSet instance
                docset = DocSet(**docset_data)
                print(f"[DocSet] Created with title: {docset.title}")
                docsets.append(docset)
                
            except Exception as e:
                print(f"  Error: Failed to create DocSet: {e}")
                continue
                
        return docsets
    except Exception as e:
        print(f"Failed to search for query '{query}':", e)
        return []

def save_recommendations(username, papers, api_url):
    for paper in papers:
        #print(paper)
        data = {
            "paper_id": paper.get("paper_id"),
            "title": paper.get("title", ""),
            "authors": paper.get("authors", ""),
            "abstract": paper.get("abstract", ""),
            "url": paper.get("url", ""),
            "content": paper.get("content", ""),  # 必须补全
            "blog": paper.get("blog", ""),
            "recommendation_reason": paper.get("recommendation_reason", ""),
            "relevance_score": paper.get("relevance_score", None)
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

def get_all_users(backend_api_url):
    """
    获取所有用户信息，返回用户字典列表（含 username, interests_description 等）
    """
    resp = requests.get(f"{backend_api_url}/api/users/all", timeout=100.0)
    resp.raise_for_status()
    return resp.json()

def get_user_interest(username: str,backend_api_url):
        response = requests.get(f"{backend_api_url}/api/users/by_email/{username}")
        response.raise_for_status()
        user_data = response.json()
        return user_data.get("interests_description", [])

def fetch_daily_papers(index_api_url: str, config):
    """
    Fetch daily papers and return a list of DocSet objects.
    This function is a placeholder and should be replaced with the actual implementation.
    """
    # 1. Check connection health before indexing
    health = check_connection_health(index_api_url)
    if health == "not_ready" or not health:
        print("Attempting to initialize index service...")
        if not initialize_database(index_api_url, config):
            print("Exiting due to failed indexer initialization.")
            sys.exit(1)
        # Re-check health after initialization
        if not check_connection_health(index_api_url):
            print("Exiting due to failed health check after initialization.")
            sys.exit(1)

    #papers = paper_pull.fetch_daily_papers()
    papers=paper_pull.dummy_paper_fetch("./orchestrator/jsons")
    print(f"Fetched {len(papers)} papers.")

    # 2. Index papers
    index_papers_via_api(papers, index_api_url)
    return papers

async def blog_generation_for_existing_user(index_api_url: str, backend_api_url: str, all_papers):
    """
    Generate blog digests for existing users based on their interests.
    This function is a placeholder and should be replaced with the actual implementation.
    """
    username = "BlogBot@gmail.com"
    
    seen_paper_ids = set()
    unique_papers = []
    for paper in all_papers:
        if paper.doc_id not in seen_paper_ids:
            seen_paper_ids.add(paper.doc_id)
            unique_papers.append(paper)
    
    print(f"去重前论文数量: {len(all_papers)}")
    print(f"去重后论文数量: {len(unique_papers)}")
    
    # 使用去重后的论文列表
    all_papers = unique_papers

    # 4. Generate blog digests for users in batches
    print("Generating blog digests for users...")
    
    batch_size = 50
    total_papers = len(all_papers)
    processed_count = 0
    
    for batch_start in range(0, total_papers, batch_size):
        batch_end = min(batch_start + batch_size, total_papers)
        batch_papers = all_papers[batch_start:batch_end]
        
        print(f"🔄 Processing batch {batch_start//batch_size + 1}: papers {batch_start+1}-{batch_end} of {total_papers}")
        
        try:
            # 生成当前批次的博客
            await run_batch_generation(batch_papers)
            print(f"✅ Blog generation completed for batch {batch_start//batch_size + 1}")
            
            # 立即处理并保存当前批次的论文
            paper_infos = []
            for paper in batch_papers:
                try:
                    with open(f"./orchestrator/blogs/{paper.doc_id}.md", encoding="utf-8") as file:
                        blog = file.read()
                except FileNotFoundError:
                    blog = None
                
                paper_infos.append({
                    "paper_id": paper.doc_id,
                    "title": paper.title,
                    "authors": ", ".join(paper.authors),
                    "abstract": paper.abstract,
                    "url": paper.HTML_path,
                    "content": paper.abstract,
                    "blog": blog,
                    "recommendation_reason": f"This is a dummy recommendation reason for paper {paper.title}",
                    "relevance_score": 0.5
                })
            
            # 保存当前批次
            print(f"💾 Saving batch {batch_start//batch_size + 1} ({len(paper_infos)} papers)...")
            save_recommendations(username, paper_infos, backend_api_url)
            
            processed_count += len(batch_papers)
            print(f"📊 Progress: {processed_count}/{total_papers} papers processed")
            
        except Exception as e:
            print(f"❌ Blog generation failed for batch {batch_start//batch_size + 1}: {e}")
            continue
    
    print(f"🎉 All batches completed! Total processed: {processed_count}/{total_papers}")

def main():
    config_path = os.path.join(os.path.dirname(__file__), "../backend/configs/app_config.yaml")
    config = load_backend_config(config_path)
    index_api_url = config['INDEX_SERVICE']["host"]
    backend_api_url = config['APP_SERVICE']["host"]
    print("backend：",backend_api_url)
    print("index：",index_api_url)


    #print("Starting daily paper fetch...")
    papers = fetch_daily_papers(index_api_url, config)
    #print("Daily paper fetch complete.")

    print("Starting blog generation for existing users...")
    asyncio.run(blog_generation_for_existing_user(index_api_url, backend_api_url, papers))
    print("Blog generation for existing users complete.")
    
if __name__ == "__main__":
    main()