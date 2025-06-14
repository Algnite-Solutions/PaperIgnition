import paper_pull
#import generate_blog
#from backend.index_service import index_papers
import os
from backend.index_service.config import load_config
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

def main():
    # Given the directory of the json files, index the papers
    json_dir = "/data3/guofang/AIgnite-Solutions/PaperIgnition/orchestrator/jsons"
    papers = paper_pull.dummy_paper_fetch(json_dir)
    print(f"Fetched {len(papers)} papers.")

    # Load config and get API URL
    config_path = os.path.join(os.path.dirname(__file__), "../tests/config.yaml")
    config = load_config(config_path)
    api_url = config["index_api_url"]

    # 1. Check connection health before indexing
    health = check_connection_health(api_url)
    if health == "not_ready" or not health:
        print("Attempting to initialize index service...")
        if not initialize_database(api_url, config):
            print("Exiting due to failed indexer initialization.")
            sys.exit(1)
        # Re-check health after initialization
        if not check_connection_health(api_url):
            print("Exiting due to failed health check after initialization.")
            sys.exit(1)

    # 2. Index papers
    index_papers_via_api(papers, api_url)

    # 3. Search papers for example queries
    example_queries = [
        "transformer models",
        "deep kernel learning",
        "federated Learning",
    ]
    for query in example_queries:
        papers=search_papers_via_api(api_url, query, 'tf-idf', 0.1)
    for query in example_queries:
        papers=search_papers_via_api(api_url, query, 'vector', 0.5)

    
    #print("Generating blog digests for users...")
    #generate_blog.run_dummy_blog_generation(papers)
    #print("Digest generation complete.")

if __name__ == "__main__":
    main()