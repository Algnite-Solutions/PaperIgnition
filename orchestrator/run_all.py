import paper_pull
#from generate_blog import run_dummy_blog_generation
#from backend.index_service import index_papers
import requests
import os
from backend.app.db_utils import load_config as load_backend_config
from AIgnite.data.docset import DocSetList, DocSet
import httpx
import sys

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
        response = httpx.post(f"{api_url}/index_papers/", json=data, timeout=30.0)
        response.raise_for_status()
        print("Indexing response:", response.json())
    except Exception as e:
        print("Failed to index papers:", e)

def search_papers_via_api(api_url, query, search_strategy='tf-idf', similarity_cutoff=0.1):
    """Search papers using the /find_similar/ endpoint for a single query.
    Returns a list of DocSet objects corresponding to the results.
    """
    payload = {
        "query": query,
        "top_k": 5,
        "similarity_cutoff": similarity_cutoff,
        "strategy_type": search_strategy
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
                docset = DocSet(**r)
            except TypeError:
                # If the API response has extra fields, filter them
                docset_fields = {k: v for k, v in r.items() if k in DocSet.__fields__}
                docset = DocSet(**docset_fields)
            print(f"[DocSet] Created with title: {docset.title}")  # Confirm DocSet creation
            docsets.append(docset)
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
            "relevance_score": paper.get("relevance_score", None)
        }
        try:
            resp = httpx.post(
                f"{api_url}/api/papers/recommend",
                params={"username": username},
                json=data,
                timeout=10.0
            )
            if resp.status_code == 201:
                print(f"✅ 推荐写入成功: {paper.get('paper_id')}")
            else:
                print(f"❌ 推荐写入失败: {paper.get('paper_id')}，原因: {resp.text}")
        except Exception as e:
            print(f"❌ 推荐写入异常: {paper.get('paper_id')}，错误: {e}")


def main():

    # TODO: use the real paper_pull.fetch_daily_papers
    # Given the directory of the json files, index the papers
    #json_dir = "./orchestrator/jsons"
    '''
    papers = paper_pull.fetch_daily_papers()
    print(f"Fetched {len(papers)} papers.")
    '''

    papers=paper_pull.dummy_paper_fetch("./orchestrator/jsons")
    print(f"Fetched {len(papers)} papers.")
    # Load config and get API URL
    config_path = os.path.join(os.path.dirname(__file__), "../backend/configs/app_config.yaml")
    config = load_backend_config(config_path)
    print(config)
    index_api_url = config['INDEX_SERVICE']["host"]
    backend_api_url = config['APP_SERVICE']["host"]
    print(backend_api_url)

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

    # 2. Index papers
    index_papers_via_api(papers, index_api_url)

    
    #3. Get user's interests
    #health = check_connection_health(backend_api_url) 
    #if health == "not_ready" or not health:
    #    print("Attempting to initialize user database...")
    #    if not initialize_database(backend_api_url, config):
    #        print("Exiting due to failed user database initialization.")
    #        sys.exit(1)
    #    if not check_connection_health(backend_api_url):
    #        print("Exiting due to failed health check after initialization.")
    #        sys.exit(1)
    def get_user_interest(username: str):
        """
            获取指定用户的研究兴趣（interests_description）,返回json，示例如下
            ['大型语言模型', '图神经网络']
        """
        # 实际上username和user_email保持一致
        response = requests.get(f"{backend_api_url}/api/users/by_email/{username}") 
        response.raise_for_status() # Raises an exception for bad status codes (e.g., 404)
        user_data = response.json()
        return user_data.get("interests_description", [])



    example_queries = get_user_interest("testuser1")
    
    
    # 3. Search papers for example queries
    for query in example_queries:
        papers=search_papers_via_api(index_api_url, query, 'tf-idf', 0.1)
    
    for query in example_queries:
        papers=search_papers_via_api(index_api_url, query, 'vector', 0.5)
    

    # TODO: use the real paper_pull.fetch_daily_papers

    # 4. Generate blog digests for users
    #print("Generating blog digests for users...")
    #run_dummy_blog_generation(papers)
    #print("Digest generation complete.")

    paper_infos = []
    for paper in papers:
        dummy_blog = "This is a dummy blog for paper " + paper.title
        paper_infos.append({
            "paper_id": paper.doc_id,
            "title": paper.title,
            "authors": ", ".join(paper.authors),
            "abstract": paper.abstract,
            "url": paper.HTML_path,
            "content": paper.abstract,  # 或其他内容
            "blog": dummy_blog,
            "recommendation_reason": "This is a dummy recommendation reason for paper " + paper.title,
            "relevance_score": 0.5
        })

    # 5. Write recommendations
    save_recommendations("testuser1", paper_infos, backend_api_url)


    
if __name__ == "__main__":
    main()