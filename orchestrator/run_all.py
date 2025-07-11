import paper_pull
import generate_blog
#from backend.index_service import index_papers
import os
from backend.index_service.config import load_config
from AIgnite.data.docset import DocSetList, DocSet
import httpx
import sys
import requests

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
        "top_k": 2,
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

def write_recommendations(username, papers, api_url):
    for paper in papers:
        data = {
            "paper_id": paper.doc_id,
            "recommendation_reason": getattr(paper, "digest", "自动推荐"),
            "relevance_score": getattr(paper, "score", None)
        }
        try:
            resp = httpx.post(
                f"{api_url}/api/papers/recommend",
                params={"username": username},
                json=data,
                timeout=10.0
            )
            if resp.status_code == 201:
                print(f"✅ 推荐写入成功: {paper.doc_id}")
            else:
                print(f"❌ 推荐写入失败: {paper.doc_id}，原因: {resp.text}")
        except Exception as e:
            print(f"❌ 推荐写入异常: {paper.doc_id}，错误: {e}")


def main():

    # Given the directory of the json files, index the papers
    json_dir = "./orchestrator/jsons"
    papers = paper_pull.dummy_paper_fetch(json_dir)

    # real fetch function, but dummy is used for the convenience of development
    # papers = paper_pull.fetch_daily_papers()

    print(f"Fetched {len(papers)} papers.")

    # Load config and get API URL
    config_path = os.path.join(os.path.dirname(__file__), "../backend/configs/app_config.yaml")
    config = load_config(config_path)
    
    index_api_url = config["INDEX_SERVICE"]["host"]
    backend_api_url = config["BACKEND_SERVICE"]["host"]

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

    # 3. Get user's interests
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
    
    example_queries = get_user_interest("111@tongji.edu.cn")

    example_queries = [
       # "transformer models",
        "deep kernel learning",
       # "federated Learning",
    ]

    print("hhhhhhhhhhhh\n",example_queries)

     # 4. Search papers for example queries

    #for query in example_queries:
    #    papers=search_papers_via_api(index_api_url, query, 'tf-idf', 0.1)
    #for query in example_queries:
    #    papers=search_papers_via_api(index_api_url, query, 'vector', 0.5)
    
    #没有遍历所有的用户，也没有考虑用户所有的兴趣
    for query in example_queries:
        papers=search_papers_via_api(index_api_url, query)

    write_recommendations("111@tongji.edu.cn", papers,  backend_api_url)

    import json
    with open("C:\\Users\\lenovo\\Desktop\\paperignite\\PaperIgnition\\orchestrator\\tem.json", 'w', encoding='utf-8') as f:
        json.dump([paper.dict() for paper in papers], f, ensure_ascii=False, indent=2)
    
    !
    generate()
    !

    # 批量保存blogs下所有博客到index server
    save_all_blogs_to_index_server(
        blogs_dir=r"C:\\Users\\lenovo\\Desktop\\paperignite\\PaperIgnition\\orchestrator\\blogs",
        index_server_url="http://localhost:8002"
    )

######################################################下面是开发需要建立的临时的函数################################################
def generate():
    import json
    import os
    with open("C:\\Users\\lenovo\\Desktop\\paperignite\\PaperIgnition\\orchestrator\\tem.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    papers = [DocSet(**item) for item in data]
    
    print("Generating blog digests for users...")
    generate_blog.run_dummy_blog_generation(papers)
    print("Digest generation complete.")
    

def save_all_blogs_to_index_server(blogs_dir, index_server_url):
    """
    读取blogs_dir下所有博客文件内容，并通过index服务器的/save_blog接口保存到数据库。
    :param blogs_dir: 博客文件夹路径
    :param index_server_url: index服务器API地址（如 http://localhost:8002 ）
    """
    for filename in os.listdir(blogs_dir):
        file_path = os.path.join(blogs_dir, filename)
        if os.path.isfile(file_path):
            doc_id = os.path.splitext(filename)[0]
            with open(file_path, 'r', encoding='utf-8') as f:
                blog_content = f.read()
            payload = {
                "doc_id": doc_id,
                "blog": blog_content
            }
            try:
                resp = requests.post(f"{index_server_url}/save_blog/", json=payload, timeout=10)
                if resp.status_code == 200:
                    print(f"✅ 博客 {filename} 已保存到 index server")
                else:
                    print(f"❌ 博客 {filename} 保存失败: {resp.text}")
            except Exception as e:
                print(f"❌ 博客 {filename} 保存异常: {e}")
###########################################################################################################################################

if __name__ == "__main__":
    main()